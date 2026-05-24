"""sklearn 三模型平均概率与 TextCNN softmax 融合；硬投票。"""

from __future__ import annotations

from typing import List, Optional

import numpy as np


def soft_fusion(
    p_sklearn: np.ndarray,
    p_cnn: np.ndarray,
    weight_sklearn: float = 0.5,
) -> np.ndarray:
    """逐样本融合两类概率矩阵 (n, C)，权重和为 1。"""
    w = float(np.clip(weight_sklearn, 0.0, 1.0))
    return w * p_sklearn + (1.0 - w) * p_cnn


def hard_vote_four(
    pred_nb: np.ndarray,
    pred_svc: np.ndarray,
    pred_xgb: np.ndarray,
    pred_cnn: np.ndarray,
    _classes: np.ndarray,
) -> np.ndarray:
    """四类整数预测 (n,) 多数票，返回与 classes 对齐的类别索引。"""
    stack = np.stack([pred_nb, pred_svc, pred_xgb, pred_cnn], axis=1)
    out = np.empty(stack.shape[0], dtype=np.int64)
    for i in range(stack.shape[0]):
        row = stack[i]
        vals, counts = np.unique(row, return_counts=True)
        out[i] = vals[np.argmax(counts)]
    return out


def predict_from_probs(proba: np.ndarray, classes: np.ndarray) -> np.ndarray:
    idx = np.argmax(proba, axis=1)
    return classes.take(idx)


def decode_labels(indices: np.ndarray, class_names: List[str]) -> List[str]:
    return [class_names[int(i)] for i in indices]
