"""在 labeled_email_testset 或任意带金标样本上评估级联模型。"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_recall_fscore_support,
)

from .cascade import CascadedPredictor
from .testset_io import iter_items, load_dataset_json, load_item_text


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def match_one(pred: Dict[str, Any], gold_s1: str, gold_s2: Optional[str]) -> Tuple[bool, str]:
    g1 = _norm(gold_s1)
    p1 = _norm(pred.get("stage1_label"))
    if g1 != p1:
        return False, "stage1"
    if g1 == "spam":
        ok = pred.get("final") == "bad"
        return ok, "spam_flow"
    if pred.get("final") != "good":
        return False, "ham_flow"
    ps2 = _norm(pred.get("stage2_label"))
    gs2 = _norm(gold_s2)
    return ps2 == gs2, "stage2"


def _classification_metrics_block(
    y_true: List[str],
    y_pred: List[str],
    labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if not y_true:
        return {
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "weighted_precision": 0.0,
            "weighted_recall": 0.0,
            "weighted_f1": 0.0,
            "per_class": {},
        }
    lab = labels if labels is not None else sorted(set(y_true) | set(y_pred))
    p, r, f, sup = precision_recall_fscore_support(y_true, y_pred, labels=lab, average=None, zero_division=0)
    per: Dict[str, Any] = {}
    for i, L in enumerate(lab):
        per[str(L)] = {
            "precision": float(p[i]),
            "recall": float(r[i]),
            "f1_score": float(f[i]),
            "support": int(sup[i]),
        }
    mp, mr, mf, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    wp, wr, wf, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(mp),
        "macro_recall": float(mr),
        "macro_f1": float(mf),
        "weighted_precision": float(wp),
        "weighted_recall": float(wr),
        "weighted_f1": float(wf),
        "per_class": per,
    }


def evaluate_batch(
    predictor: CascadedPredictor,
    samples: List[Dict[str, Any]],
    mode: str = "soft",
    verbose_print: bool = False,
    artifact_root: str = "",
    fusion_w_stage1: Optional[float] = None,
    fusion_w_stage2: Optional[float] = None,
) -> Dict[str, Any]:
    """
    samples 每项: id?, text, gold_stage1, gold_stage2?, note_zh?
    fusion_w_stage1/2：与 CascadedPredictor.predict_one 一致，覆盖 meta 中的 sklearn 融合权重。
    返回: n, stage1_*, stage2_*, strict_match_*, items, effective_fusion_weights?, ...
    """
    w1_eff = CascadedPredictor.clip_fusion_weight(fusion_w_stage1, predictor.w1)
    w2_eff = CascadedPredictor.clip_fusion_weight(fusion_w_stage2, predictor.w2)
    rows: List[Dict[str, Any]] = []
    y1_gold: List[str] = []
    y1_pred: List[str] = []
    y2_gold_h: List[str] = []
    y2_pred_h: List[str] = []

    for it in samples:
        eid = it.get("id") or ""
        text = it["text"]
        g1 = it["gold_stage1"]
        g2 = it.get("gold_stage2")
        note = it.get("note_zh", "")
        pred = predictor.predict_one(
            text,
            mode=mode,
            fusion_w_stage1=fusion_w_stage1,
            fusion_w_stage2=fusion_w_stage2,
        )
        ok, where = match_one(pred, g1, g2)
        rows.append(
            {
                "id": eid,
                "ok": ok,
                "fail_reason": where if not ok else "",
                "gold_stage1": g1,
                "pred_stage1": pred.get("stage1_label"),
                "gold_stage2": g2,
                "pred_stage2": pred.get("stage2_label"),
                "final": pred.get("final"),
                "note_zh": note,
            }
        )
        y1_gold.append(_norm(g1))
        y1_pred.append(_norm(pred.get("stage1_label")))
        if _norm(g1) == "ham":
            y2_gold_h.append(_norm(g2) or "")
            y2_pred_h.append(_norm(pred.get("stage2_label")) or "")

    lab1 = sorted(set(y1_gold) | set(y1_pred))
    stage1_metrics = _classification_metrics_block(y1_gold, y1_pred, labels=lab1)

    lab2 = sorted(x for x in set(y2_gold_h) | set(y2_pred_h) if x)
    stage2_metrics = _classification_metrics_block(y2_gold_h, y2_pred_h, labels=lab2 if lab2 else None)

    if y2_gold_h:
        s2_macro_f1_only = f1_score(y2_gold_h, y2_pred_h, labels=lab2 or None, average="macro", zero_division=0)
    else:
        s2_macro_f1_only = 0.0

    strict_ok = sum(1 for r in rows if r["ok"])
    n = len(rows)
    result: Dict[str, Any] = {
        "n": n,
        "mode": mode,
        "effective_fusion_weights": {"stage1": w1_eff, "stage2": w2_eff},
        "stage1": stage1_metrics,
        "stage2_on_ham_gold": {
            "n_ham_gold": len(y2_gold_h),
            "accuracy": stage2_metrics["accuracy"],
            "macro_precision": stage2_metrics["macro_precision"],
            "macro_recall": stage2_metrics["macro_recall"],
            "macro_f1": stage2_metrics["macro_f1"],
            "weighted_f1": stage2_metrics["weighted_f1"],
            "per_class": stage2_metrics["per_class"],
            "macro_f1_sklearn_only": float(s2_macro_f1_only),
        },
        "strict_match_count": int(strict_ok),
        "strict_match_rate": float(strict_ok / n) if n else 0.0,
        "items": rows,
        "rows": rows,
    }

    try:
        result["stage1_classification_report"] = classification_report(y1_gold, y1_pred, zero_division=0)
    except Exception:
        result["stage1_classification_report"] = ""
    try:
        if y2_gold_h:
            result["stage2_classification_report"] = classification_report(
                y2_gold_h, y2_pred_h, labels=lab2 or None, zero_division=0
            )
        else:
            result["stage2_classification_report"] = ""
    except Exception:
        result["stage2_classification_report"] = ""

    if verbose_print:
        _print_eval_report(result, artifact_root=artifact_root)

    return result


def _print_eval_report(result: Dict[str, Any], artifact_root: str = "") -> None:
    s1 = result["stage1"]
    s2 = result["stage2_on_ham_gold"]
    n = result["n"]
    mode = result.get("mode", "soft")
    rows = result["items"]
    strict_ok = result["strict_match_count"]
    print("=== 级联评估 ===")
    print(f"样本数: {n} | 模式: {mode} | artifacts: {artifact_root}")
    print(f"阶段一 accuracy: {s1['accuracy']:.4f}")
    print(f"阶段一 macro P/R/F1: {s1['macro_precision']:.4f} / {s1['macro_recall']:.4f} / {s1['macro_f1']:.4f}")
    print(f"金标 ham 子集阶段二 accuracy: {s2['accuracy']:.4f}")
    print(f"阶段二 macro P/R/F1: {s2['macro_precision']:.4f} / {s2['macro_recall']:.4f} / {s2['macro_f1']:.4f}")
    print(f"严格全对比例: {result['strict_match_rate']:.4f} ({strict_ok}/{n})")
    if result.get("stage1_classification_report"):
        print("\n阶段一 classification_report:\n" + result["stage1_classification_report"])
    if result.get("stage2_classification_report"):
        print("\n阶段二 classification_report (金标 ham):\n" + result["stage2_classification_report"])
    print("\n逐条结果:")
    hdr = f"{'id':<8} {'OK':<5} {'g1':<6} {'p1':<6} {'g2':<14} {'p2':<14} note"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        g2s = (str(r.get("gold_stage2")) if r.get("gold_stage2") is not None else "-")[:14]
        p2s = (str(r.get("pred_stage2")) if r.get("pred_stage2") is not None else "-")[:14]
        note = (r.get("note_zh") or "")[:40]
        rid = (r.get("id") or "")[:8]
        print(f"{rid:<8} {'OK' if r['ok'] else 'FAIL':<5} {r['gold_stage1']:<6} {r['pred_stage1']:<6} {g2s:<14} {p2s:<14} {note}")


def run_eval(
    artifact_root: str,
    dataset_path: str,
    mode: str = "soft",
    json_out: Optional[str] = None,
) -> Dict[str, Any]:
    dataset_dir = os.path.dirname(os.path.abspath(dataset_path))
    ds = load_dataset_json(dataset_path)
    items = iter_items(ds)
    predictor = CascadedPredictor(os.path.abspath(artifact_root))

    samples: List[Dict[str, Any]] = []
    for it in items:
        samples.append(
            {
                "id": it["id"],
                "text": load_item_text(dataset_dir, it["email_file"]),
                "gold_stage1": it["gold_stage1"],
                "gold_stage2": it.get("gold_stage2"),
                "note_zh": it.get("note_zh", ""),
            }
        )

    result = evaluate_batch(
        predictor,
        samples,
        mode=mode,
        verbose_print=True,
        artifact_root=os.path.abspath(artifact_root),
    )
    result["artifact_root"] = os.path.abspath(artifact_root)
    result["dataset_path"] = os.path.abspath(dataset_path)

    if json_out:
        out_payload = {k: v for k, v in result.items() if k not in ("stage1_classification_report", "stage2_classification_report")}
        out_payload["stage1_classification_report"] = result.get("stage1_classification_report", "")
        out_payload["stage2_classification_report"] = result.get("stage2_classification_report", "")
        os.makedirs(os.path.dirname(os.path.abspath(json_out)) or ".", exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(out_payload, f, ensure_ascii=False, indent=2)
        print(f"\n已写入 JSON: {json_out}")

    return result
