"""单阶段训练、评估与落盘。"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from typing import List, Optional

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

from . import fusion
from .sklearn_ensemble import SklearnTriEnsemble
from .textcnn import TextCNNConfig, predict_proba_textcnn, save_textcnn_bundle, train_textcnn


def _safe_calibrated_cv(n_samples: int, n_classes: int) -> int:
    per = max(1, n_samples // max(n_classes, 1))
    return max(2, min(3, per))


def fit_sklearn_with_cv(
    texts: List[str],
    y: np.ndarray,
    max_features: int = 50000,
    random_state: int = 42,
    show_progress: bool = True,
) -> SklearnTriEnsemble:
    n = len(texts)
    cv = _safe_calibrated_cv(n, len(np.unique(y)))
    ens = SklearnTriEnsemble(max_features=max_features, random_state=random_state)
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.svm import LinearSVC

    ens.svc = CalibratedClassifierCV(
        LinearSVC(max_iter=8000, dual=False, class_weight="balanced", random_state=random_state),
        method="sigmoid",
        cv=cv,
    )
    ens.fit(texts, y, show_progress=show_progress)
    return ens


def train_stage(
    texts: List[str],
    y: np.ndarray,
    class_names: List[str],
    artifact_dir: str,
    test_size: float = 0.15,
    random_state: int = 42,
    fusion_weight_sklearn: float = 0.5,
    textcnn_cfg: Optional[TextCNNConfig] = None,
    max_features: int = 50000,
    show_progress: bool = True,
) -> dict:
    os.makedirs(artifact_dir, exist_ok=True)
    sk = fit_sklearn_with_cv(
        texts,
        y,
        max_features=max_features,
        random_state=random_state,
        show_progress=show_progress,
    )
    sk.save(os.path.join(artifact_dir, "sklearn"))

    idx = np.arange(len(texts))
    strat = y if len(np.unique(y)) > 1 else None
    tr_idx, va_idx = train_test_split(idx, test_size=test_size, random_state=random_state, stratify=strat)
    X_tr = [texts[i] for i in tr_idx]
    y_tr = y[tr_idx]
    X_va = [texts[i] for i in va_idx]
    y_va = y[va_idx]

    cfg = textcnn_cfg or TextCNNConfig()
    if not show_progress:
        cfg = replace(cfg, show_progress=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, vocab, _ = train_textcnn(X_tr, y_tr, X_va, y_va, cfg=cfg, device=device)
    cnn_dir = os.path.join(artifact_dir, "textcnn")
    save_textcnn_bundle(cnn_dir, model, vocab, cfg, class_names=list(class_names))

    meta = {
        "stage": os.path.basename(artifact_dir.rstrip(os.sep)),
        "class_names": list(class_names),
        "fusion_weight_sklearn": float(fusion_weight_sklearn),
        "n_classes": len(class_names),
    }
    with open(os.path.join(artifact_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def evaluate_stage_simple(
    texts: List[str],
    y: np.ndarray,
    artifact_dir: str,
    fusion_weight_sklearn: Optional[float] = None,
    plot_cm_path: Optional[str] = None,
) -> dict:
    """y 为整数标签 0..C-1。"""
    with open(os.path.join(artifact_dir, "meta.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)
    class_names: List[str] = meta["class_names"]
    w = float(
        fusion_weight_sklearn if fusion_weight_sklearn is not None else meta.get("fusion_weight_sklearn", 0.5)
    )

    sk = SklearnTriEnsemble.load(os.path.join(artifact_dir, "sklearn"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from .textcnn import load_textcnn_bundle

    model, vocab, cfg, _ = load_textcnn_bundle(os.path.join(artifact_dir, "textcnn"), device)
    cfg = replace(cfg, show_progress=len(texts) >= 32)

    p_sk = sk.predict_proba_mean(texts)
    p_cnn = predict_proba_textcnn(model, vocab, texts, cfg, device)
    p_fused = fusion.soft_fusion(p_sk, p_cnn, weight_sklearn=w)
    y_pred = np.argmax(p_fused, axis=1)

    acc = accuracy_score(y, y_pred)
    f1_macro = f1_score(y, y_pred, average="macro", zero_division=0)
    report = classification_report(y, y_pred, target_names=class_names, zero_division=0)
    cm = confusion_matrix(y, y_pred)

    if plot_cm_path:
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            plt.figure(figsize=(8, 6))
            sns.heatmap(cm, annot=True, fmt="d", xticklabels=class_names, yticklabels=class_names, cmap="Blues")
            plt.ylabel("True")
            plt.xlabel("Pred")
            plt.tight_layout()
            d = os.path.dirname(plot_cm_path)
            if d:
                os.makedirs(d, exist_ok=True)
            plt.savefig(plot_cm_path, dpi=120)
            plt.close()
        except Exception:
            pass

    return {
        "accuracy": float(acc),
        "f1_macro": float(f1_macro),
        "report": report,
        "confusion_matrix": cm.tolist(),
    }
