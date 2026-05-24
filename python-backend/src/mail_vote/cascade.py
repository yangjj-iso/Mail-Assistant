"""级联加载与推理。"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from . import fusion
from .sklearn_ensemble import SklearnTriEnsemble
from .textcnn import TextCNNConfig, load_textcnn_bundle, predict_proba_textcnn


class CascadedPredictor:
    """级联预测；soft 模式下每阶段融合权重见 meta.json 的 fusion_weight_sklearn，可被 predict_one 入参覆盖。"""

    def __init__(self, artifact_root: str):
        self.root = artifact_root
        self.stage1_dir = os.path.join(artifact_root, "stage1")
        self.stage2_dir = os.path.join(artifact_root, "stage2")
        self._load()

    def _load(self) -> None:
        with open(os.path.join(self.stage1_dir, "meta.json"), "r", encoding="utf-8") as f:
            self.meta1 = json.load(f)
        with open(os.path.join(self.stage2_dir, "meta.json"), "r", encoding="utf-8") as f:
            self.meta2 = json.load(f)
        self.sk1 = SklearnTriEnsemble.load(os.path.join(self.stage1_dir, "sklearn"))
        self.sk2 = SklearnTriEnsemble.load(os.path.join(self.stage2_dir, "sklearn"))
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.cnn1, self.vocab1, self.cfg1, _ = load_textcnn_bundle(
            os.path.join(self.stage1_dir, "textcnn"), self.device
        )
        self.cnn2, self.vocab2, self.cfg2, _ = load_textcnn_bundle(
            os.path.join(self.stage2_dir, "textcnn"), self.device
        )
        self.names1: List[str] = self.meta1["class_names"]
        self.names2: List[str] = self.meta2["class_names"]
        self.w1 = float(self.meta1.get("fusion_weight_sklearn", 0.5))
        self.w2 = float(self.meta2.get("fusion_weight_sklearn", 0.5))
        self.spam_index = None
        for i, n in enumerate(self.names1):
            if str(n).lower() == "spam":
                self.spam_index = i
                break

    @staticmethod
    def clip_fusion_weight(override: Optional[float], fallback: float) -> float:
        """将融合权重限制在 [0,1]；override 为 None 时使用训练落盘的 fallback。"""
        fb = float(np.clip(fallback, 0.0, 1.0))
        if override is None:
            return fb
        return float(np.clip(override, 0.0, 1.0))

    def _predict_stage(
        self,
        texts: List[str],
        sk: SklearnTriEnsemble,
        model,
        vocab,
        cfg: TextCNNConfig,
        weight_sk: float,
        mode: str,
    ) -> tuple:
        p_sk = sk.predict_proba_mean(texts)
        p_cnn = predict_proba_textcnn(model, vocab, texts, cfg, self.device)
        if mode == "hard":
            a_nb, a_svc, a_xgb = sk.argmax_components(texts)
            a_cnn = np.argmax(p_cnn, axis=1)
            classes = np.arange(p_sk.shape[1])
            y_idx = fusion.hard_vote_four(a_nb, a_svc, a_xgb, a_cnn, classes)
            return y_idx, p_sk, p_cnn
        p_fused = fusion.soft_fusion(p_sk, p_cnn, weight_sklearn=weight_sk)
        y_idx = np.argmax(p_fused, axis=1)
        return y_idx, p_sk, p_cnn

    def predict_one(
        self,
        text: str,
        mode: str = "soft",
        fusion_w_stage1: Optional[float] = None,
        fusion_w_stage2: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        fusion_w_stage1/2：仅 soft 模式参与 sklearn 与 TextCNN 概率融合；为 None 时用 meta.json 中的 fusion_weight_sklearn。
        hard 模式为四路硬投票，不传融合概率，但返回体仍会带上本次若走 soft 会使用的有效权重便于前端展示。
        """
        w1_use = self.clip_fusion_weight(fusion_w_stage1, self.w1)
        w2_use = self.clip_fusion_weight(fusion_w_stage2, self.w2)
        texts = [text]
        y1, _, _ = self._predict_stage(texts, self.sk1, self.cnn1, self.vocab1, self.cfg1, w1_use, mode)
        idx1 = int(y1[0])
        label1 = self.names1[idx1]
        out: Dict[str, Any] = {
            "stage1_label": label1,
            "stage1_index": idx1,
            "effective_fusion_weight_stage1": w1_use,
            "effective_fusion_weight_stage2": w2_use,
        }
        is_spam = str(label1).lower() == "spam"
        if self.spam_index is not None:
            is_spam = idx1 == self.spam_index
        if is_spam:
            out["final"] = "bad"
            out["stage2_label"] = None
            return out
        y2, _, _ = self._predict_stage(texts, self.sk2, self.cnn2, self.vocab2, self.cfg2, w2_use, mode)
        idx2 = int(y2[0])
        out["final"] = "good"
        out["stage2_label"] = self.names2[idx2]
        out["stage2_index"] = idx2
        return out
