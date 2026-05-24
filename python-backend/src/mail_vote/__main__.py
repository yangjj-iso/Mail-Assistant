"""CLI: python -m src.mail_vote train|predict ..."""

from __future__ import annotations

import argparse
import json
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def cmd_train(args: argparse.Namespace) -> int:
    from . import data_io
    from .stages import evaluate_stage_simple, train_stage
    from .textcnn import TextCNNConfig

    show_prog = not args.no_progress
    artifact_root = os.path.abspath(args.artifact_root)
    stages = []
    if args.stage in ("1", "all"):
        stages.append(1)
    if args.stage in ("2", "all"):
        stages.append(2)

    if 1 in stages:
        max_samples = args.max_samples_coarse if args.max_samples_coarse > 0 else None
        texts, y, le = data_io.load_stage1(args.coarse_csv, max_samples=max_samples, random_state=args.seed)
        names = list(le.classes_)
        out = os.path.join(artifact_root, "stage1")
        cfg = TextCNNConfig(
            epochs=args.textcnn_epochs,
            batch_size=args.batch_size,
            max_len=args.max_len,
            show_progress=show_prog,
        )
        train_stage(
            texts,
            y,
            names,
            out,
            test_size=args.val_size,
            fusion_weight_sklearn=args.fusion_w,
            textcnn_cfg=cfg,
            max_features=args.max_features,
            show_progress=show_prog,
        )
        if args.eval_split > 0 and len(texts) > 50:
            import numpy as np
            from sklearn.model_selection import train_test_split

            idx = np.arange(len(texts))
            strat = y if len(np.unique(y)) > 1 else None
            _, te_idx = train_test_split(idx, test_size=args.eval_split, random_state=args.seed, stratify=strat)
            X_te = [texts[i] for i in te_idx]
            y_te = y[te_idx]
            ev = evaluate_stage_simple(
                X_te,
                y_te,
                out,
                fusion_weight_sklearn=args.fusion_w,
                plot_cm_path=os.path.join(out, "confusion_matrix.png") if args.save_cm else None,
            )
            print("=== Stage1 eval (hold-out) ===")
            print(json.dumps({k: ev[k] for k in ("accuracy", "f1_macro")}, indent=2, ensure_ascii=False))
            print(ev["report"])

    if 2 in stages:
        if args.fine_train_csv and args.fine_test_csv:
            X_tr, y_tr, X_te, y_te, le2 = data_io.load_stage2_from_split(
                args.fine_train_csv,
                args.fine_test_csv,
                exclude_spam=True,
            )
        else:
            paths = data_io.default_paths(_REPO_ROOT)
            X_tr, y_tr, X_te, y_te, le2 = data_io.load_stage2_from_split(
                paths["fine_train"],
                paths["fine_test"],
                exclude_spam=True,
            )
        names2 = list(le2.classes_)
        out2 = os.path.join(artifact_root, "stage2")
        cfg = TextCNNConfig(
            epochs=args.textcnn_epochs,
            batch_size=args.batch_size,
            max_len=args.max_len,
            show_progress=show_prog,
        )
        train_stage(
            X_tr,
            y_tr,
            names2,
            out2,
            test_size=args.val_size,
            fusion_weight_sklearn=args.fusion_w,
            textcnn_cfg=cfg,
            max_features=args.max_features,
            show_progress=show_prog,
        )
        ev2 = evaluate_stage_simple(
            X_te,
            y_te,
            out2,
            fusion_weight_sklearn=args.fusion_w,
            plot_cm_path=os.path.join(out2, "confusion_matrix.png") if args.save_cm else None,
        )
        print("=== Stage2 eval (provided test, non-spam) ===")
        print(json.dumps({k: ev2[k] for k in ("accuracy", "f1_macro")}, indent=2, ensure_ascii=False))
        print(ev2["report"])

    return 0


def cmd_eval_testset(args: argparse.Namespace) -> int:
    from .eval_testset import run_eval

    dataset = os.path.abspath(args.dataset)
    run_eval(
        os.path.abspath(args.artifact_root),
        dataset,
        mode=args.mode,
        json_out=args.json_out or None,
    )
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    if args.artifact_root:
        os.environ["MAIL_VOTE_ARTIFACT_ROOT"] = os.path.abspath(args.artifact_root)
    if args.cors_origins:
        os.environ["MAIL_VOTE_CORS_ORIGINS"] = args.cors_origins
    if args.api_key:
        os.environ["MAIL_VOTE_API_KEY"] = args.api_key
    if args.reload:
        uvicorn.run(
            "src.mail_vote.api_app:app",
            host=args.host,
            port=args.port,
            reload=True,
        )
    else:
        from src.mail_vote.api_app import app as fastapi_app

        uvicorn.run(fastapi_app, host=args.host, port=args.port, reload=False)
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    from .cascade import CascadedPredictor

    pred = CascadedPredictor(os.path.abspath(args.artifact_root))
    text = args.text
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    if not text.strip():
        print("请提供 --text 或 --file", file=sys.stderr)
        return 2
    r = pred.predict_one(text, mode=args.mode)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


def cmd_job_gen(args: argparse.Namespace) -> int:
    from pathlib import Path
    from .job.data_gen import save_ner_data, save_classifier_data

    out = Path(os.path.abspath(args.output_dir))
    print(f"Generating synthetic data to {out}")
    save_ner_data(out, n_samples=args.ner_samples, seed=args.seed)
    save_classifier_data(out, n_per_class=args.cls_per_class, seed=args.seed)
    print("Done. Files: ner_train.jsonl, ner_test.jsonl, job_cls_train.csv, job_cls_test.csv")
    return 0


def cmd_job_train(args: argparse.Namespace) -> int:
    from pathlib import Path

    data_dir = Path(os.path.abspath(args.data_dir))
    artifact_dir = Path(os.path.abspath(args.artifact_root)) / "job"

    components = []
    if args.component in ("detector", "all"):
        components.append("detector")
    if args.component in ("stage", "all"):
        components.append("stage")
    if args.component in ("ner", "all"):
        components.append("ner")

    if "detector" in components:
        print("=== Training Job Detector ===")
        from .job.detector import JobDetector, load_classifier_data
        texts, det_labels, _ = load_classifier_data(data_dir / "job_cls_train.csv")
        detector = JobDetector()
        result = detector.train(texts, det_labels, str(artifact_dir / "detector"))
        print(f"Detector accuracy: {result['accuracy']:.4f}")

    if "stage" in components:
        print("=== Training Stage Classifier ===")
        from .job.detector import JobStageClassifier, load_classifier_data
        texts, det_labels, stage_labels = load_classifier_data(data_dir / "job_cls_train.csv")
        job_texts = [t for t, d in zip(texts, det_labels) if d == "job"]
        job_stages = [s for s, d in zip(stage_labels, det_labels) if d == "job"]
        clf = JobStageClassifier()
        result = clf.train(job_texts, job_stages, str(artifact_dir / "stage"))
        print(f"Stage classifier accuracy: {result['accuracy']:.4f}")

    if "ner" in components:
        print("=== Training NER Model ===")
        from .job.ner_trainer import train as train_ner
        train_ner(
            train_path=data_dir / "ner_train.jsonl",
            test_path=data_dir / "ner_test.jsonl",
            output_dir=artifact_dir / "ner",
            epochs=args.ner_epochs,
            batch_size=args.batch_size,
            device="cuda" if not args.cpu else "cpu",
        )

    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="级联邮件分类训练与推理")
    sub = p.add_subparsers(dest="command", required=True)

    pt = sub.add_parser("train", help="训练阶段一/二")
    pt.add_argument("--stage", choices=["1", "2", "all"], default="all")
    pt.add_argument("--artifact-root", default=os.path.join(_REPO_ROOT, "artifacts"))
    pt.add_argument("--coarse-csv", default=os.path.join(_REPO_ROOT, "data", "粗.csv"))
    pt.add_argument("--max-samples-coarse", type=int, default=25000, help="粗数据分层子采样上限；0 表示全量")
    pt.add_argument("--fine-train-csv", default="", help="默认可空，使用 data/hugging_face_jason/train.csv")
    pt.add_argument("--fine-test-csv", default="", help="默认可空，使用 test.csv")
    pt.add_argument("--val-size", type=float, default=0.15, help="TextCNN 验证集比例")
    pt.add_argument("--eval-split", type=float, default=0.15, help="阶段一训练后 hold-out 评估比例；0 跳过")
    pt.add_argument("--fusion-w", type=float, default=0.5, help="融合时 sklearn 平均概率权重")
    pt.add_argument("--textcnn-epochs", type=int, default=6)
    pt.add_argument("--batch-size", type=int, default=64)
    pt.add_argument("--max-len", type=int, default=400)
    pt.add_argument("--max-features", type=int, default=50000)
    pt.add_argument("--seed", type=int, default=42)
    pt.add_argument("--save-cm", action="store_true", help="保存混淆矩阵 PNG")
    pt.add_argument("--no-progress", action="store_true", help="关闭 tqdm 进度条")
    pt.set_defaults(func=cmd_train)

    pp = sub.add_parser("predict", help="级联推理单条文本")
    pp.add_argument("--artifact-root", default=os.path.join(_REPO_ROOT, "artifacts"))
    pp.add_argument("--text", default="", help="邮件文本")
    pp.add_argument("--file", default="", help="从文件读入全文")
    pp.add_argument("--mode", choices=["soft", "hard"], default="soft")
    pp.set_defaults(func=cmd_predict)

    pe = sub.add_parser("eval-testset", help="在 data/labeled_email_testset 上评估级联模型")
    pe.add_argument("--artifact-root", default=os.path.join(_REPO_ROOT, "artifacts"))
    pe.add_argument("--dataset", default=os.path.join(_REPO_ROOT, "data", "labeled_email_testset", "dataset.json"))
    pe.add_argument("--mode", choices=["soft", "hard"], default="soft")
    pe.add_argument("--json-out", default="", help="可选，写出评估结果 JSON")
    pe.set_defaults(func=cmd_eval_testset)

    ps = sub.add_parser("serve", help="启动 FastAPI (uvicorn)")
    ps.add_argument("--host", default="0.0.0.0")
    ps.add_argument("--port", type=int, default=8081)
    ps.add_argument("--reload", action="store_true", help="开发热重载")
    ps.add_argument("--artifact-root", default="", help="写入环境变量 MAIL_VOTE_ARTIFACT_ROOT")
    ps.add_argument("--cors-origins", default="", help="逗号分隔，写入 MAIL_VOTE_CORS_ORIGINS")
    ps.add_argument("--api-key", default="", help="写入 MAIL_VOTE_API_KEY，非空则要求请求头 X-API-Key")
    ps.set_defaults(func=cmd_serve)

    pjg = sub.add_parser("job-gen", help="生成求职模块合成训练数据")
    pjg.add_argument("--output-dir", default=os.path.join(_REPO_ROOT, "data", "job"))
    pjg.add_argument("--ner-samples", type=int, default=4000)
    pjg.add_argument("--cls-per-class", type=int, default=600)
    pjg.add_argument("--seed", type=int, default=42)
    pjg.set_defaults(func=cmd_job_gen)

    pjt = sub.add_parser("job-train", help="训练求职模块模型（detector/stage/ner）")
    pjt.add_argument("--component", choices=["detector", "stage", "ner", "all"], default="all")
    pjt.add_argument("--data-dir", default=os.path.join(_REPO_ROOT, "data", "job"))
    pjt.add_argument("--artifact-root", default=os.path.join(_REPO_ROOT, "artifacts"))
    pjt.add_argument("--ner-epochs", type=int, default=30)
    pjt.add_argument("--batch-size", type=int, default=32)
    pjt.add_argument("--cpu", action="store_true", help="强制使用 CPU 训练")
    pjt.set_defaults(func=cmd_job_train)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
