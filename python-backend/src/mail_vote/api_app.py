"""FastAPI：级联邮件分类预测与带金标批量评估。"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .cascade import CascadedPredictor
from .eval_testset import evaluate_batch
from .schemas import EvaluateBatchRequest, HealthResponse, PredictRequest, PredictResponse
from .job.schemas import JobPredictRequest, JobPredictResponse, EntityResult, JobFeedbackRequest, JobFeedbackResponse


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _default_artifact_root() -> str:
    return os.path.join(_repo_root(), "artifacts")


def _cors_origins() -> List[str]:
    raw = os.environ.get("MAIL_VOTE_CORS_ORIGINS", "").strip()
    if not raw:
        return []
    return [o.strip() for o in raw.split(",") if o.strip()]


def _api_key_expected() -> str:
    return os.environ.get("MAIL_VOTE_API_KEY", "").strip()


def _max_eval_items() -> int:
    try:
        return max(1, min(10000, int(os.environ.get("MAIL_VOTE_MAX_EVAL_ITEMS", "2000"))))
    except ValueError:
        return 2000


async def verify_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    expected = _api_key_expected()
    if not expected:
        return
    if (x_api_key or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    root = os.environ.get("MAIL_VOTE_ARTIFACT_ROOT", "").strip() or _default_artifact_root()
    root = os.path.abspath(root)
    try:
        app.state.predictor = CascadedPredictor(root)
        app.state.artifact_root = root
    except Exception as e:
        app.state.predictor = None
        app.state.artifact_root = root
        app.state.load_error = str(e)

    # Load job models if available
    job_dir = os.path.join(root, "job")
    app.state.job_detector = None
    app.state.job_stage_clf = None
    app.state.job_ner = None
    if os.path.isdir(os.path.join(job_dir, "detector")):
        try:
            from .job.detector import JobDetector, JobStageClassifier
            app.state.job_detector = JobDetector(os.path.join(job_dir, "detector"))
            if os.path.isdir(os.path.join(job_dir, "stage")):
                app.state.job_stage_clf = JobStageClassifier(os.path.join(job_dir, "stage"))
        except Exception:
            pass
    if os.path.isdir(os.path.join(job_dir, "ner")):
        try:
            from .job.ner_predictor import NERPredictor
            from pathlib import Path
            app.state.job_ner = NERPredictor(Path(os.path.join(job_dir, "ner")))
        except Exception:
            pass
    yield


app = FastAPI(
    title="Mail vote cascade API",
    version="1.0.0",
    lifespan=lifespan,
)

_origins = _cors_origins()
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    pred = getattr(app.state, "predictor", None)
    if pred is None:
        raise HTTPException(
            status_code=503,
            detail=getattr(app.state, "load_error", "Model not loaded"),
        )
    return HealthResponse(
        status="ok",
        artifact_root=str(app.state.artifact_root),
        stage1_class_names=list(pred.names1),
        stage2_class_names=list(pred.names2),
        fusion_weight_sklearn_stage1=float(pred.meta1.get("fusion_weight_sklearn", 0.5)),
        fusion_weight_sklearn_stage2=float(pred.meta2.get("fusion_weight_sklearn", 0.5)),
    )


@app.post("/v1/predict", response_model=PredictResponse, dependencies=[Depends(verify_api_key)])
def predict(req: PredictRequest) -> PredictResponse:
    pred = getattr(app.state, "predictor", None)
    if pred is None:
        raise HTTPException(status_code=503, detail=getattr(app.state, "load_error", "Model not loaded"))
    out = pred.predict_one(
        req.text,
        mode=req.mode,
        fusion_w_stage1=req.fusion_weight_sklearn_stage1,
        fusion_w_stage2=req.fusion_weight_sklearn_stage2,
    )
    return PredictResponse(
        stage1_label=str(out["stage1_label"]),
        stage1_index=int(out["stage1_index"]),
        final=str(out["final"]),
        stage2_label=out.get("stage2_label"),
        stage2_index=int(out["stage2_index"]) if out.get("stage2_index") is not None else None,
        effective_fusion_weight_stage1=float(out["effective_fusion_weight_stage1"]),
        effective_fusion_weight_stage2=float(out["effective_fusion_weight_stage2"]),
    )


def _strip_eval_for_response(raw: Dict[str, Any], include_reports: bool) -> Dict[str, Any]:
    out = dict(raw)
    if not include_reports:
        out.pop("stage1_classification_report", None)
        out.pop("stage2_classification_report", None)
    return out


@app.post("/v1/evaluate/batch", dependencies=[Depends(verify_api_key)])
def evaluate_batch_route(req: EvaluateBatchRequest) -> Dict[str, Any]:
    pred = getattr(app.state, "predictor", None)
    if pred is None:
        raise HTTPException(status_code=503, detail=getattr(app.state, "load_error", "Model not loaded"))
    cap = _max_eval_items()
    if len(req.items) > cap:
        raise HTTPException(status_code=400, detail=f"Too many items, max {cap}")
    samples: List[Dict[str, Any]] = []
    for it in req.items:
        samples.append(
            {
                "id": it.id or "",
                "text": it.text,
                "gold_stage1": it.gold_stage1,
                "gold_stage2": it.gold_stage2,
                "note_zh": it.note_zh or "",
            }
        )
    raw = evaluate_batch(
        pred,
        samples,
        mode=req.mode,
        verbose_print=False,
        fusion_w_stage1=req.fusion_weight_sklearn_stage1,
        fusion_w_stage2=req.fusion_weight_sklearn_stage2,
    )
    return _strip_eval_for_response(raw, req.include_reports)


@app.post("/v1/job/predict", response_model=JobPredictResponse, dependencies=[Depends(verify_api_key)])
def job_predict(req: JobPredictRequest) -> JobPredictResponse:
    detector = getattr(app.state, "job_detector", None)
    if detector is None:
        raise HTTPException(status_code=503, detail="Job models not loaded")

    combined_text = f"{req.subject} {req.text}".strip()
    det_result = detector.predict_one(combined_text)

    response = JobPredictResponse(
        is_job=det_result["is_job"],
        confidence=det_result["confidence"],
    )

    if not det_result["is_job"]:
        return response

    stage_clf = getattr(app.state, "job_stage_clf", None)
    if stage_clf:
        stage_result = stage_clf.predict_one(combined_text)
        response.stage = stage_result["stage"]
        response.stage_confidence = stage_result["confidence"]

    ner = getattr(app.state, "job_ner", None)
    if ner:
        entities = ner.predict(combined_text)
        response.entities = EntityResult(
            company=entities.get("COMPANY", []),
            position=entities.get("POSITION", []),
            time=entities.get("TIME", []),
            round=entities.get("ROUND", []),
            location=entities.get("LOCATION", []),
        )

    return response


@app.post("/v1/job/feedback", response_model=JobFeedbackResponse, dependencies=[Depends(verify_api_key)])
def job_feedback(req: JobFeedbackRequest) -> JobFeedbackResponse:
    # Store feedback for future active learning iterations
    import json
    from pathlib import Path
    feedback_dir = Path(app.state.artifact_root) / "job" / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    feedback_file = feedback_dir / "feedback.jsonl"
    with open(feedback_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(req.model_dump(), ensure_ascii=False) + "\n")
    return JobFeedbackResponse(email_id=req.email_id)
