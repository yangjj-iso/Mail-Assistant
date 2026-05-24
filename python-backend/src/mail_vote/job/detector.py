"""求职邮件检测器 + 阶段分类器：复用现有融合架构。"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from ..sklearn_ensemble import SklearnTriEnsemble
from ..textcnn import (
    TextCNN, TextCNNConfig, Vocab,
    train_textcnn, predict_proba_textcnn,
    save_textcnn_bundle, load_textcnn_bundle,
)


JOB_LABELS = ["job", "not_job"]
STAGE_LABELS = ["applied", "written_test", "interview", "offer", "rejected"]


class JobDetector:
    """二分类：判断邮件是否为求职相关。"""

    def __init__(self, artifact_dir: Optional[str] = None):
        self.sklearn_model: Optional[SklearnTriEnsemble] = None
        self._cnn_model: Optional[TextCNN] = None
        self._cnn_vocab: Optional[Vocab] = None
        self._cnn_cfg: Optional[TextCNNConfig] = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.sklearn_weight: float = 0.5
        self._labels = JOB_LABELS

        if artifact_dir:
            self.load(artifact_dir)

    def train(self, texts: List[str], labels: List[str], output_dir: str) -> Dict:
        os.makedirs(output_dir, exist_ok=True)

        label2idx = {l: i for i, l in enumerate(self._labels)}
        y = np.array([label2idx[l] for l in labels])

        sklearn_dir = os.path.join(output_dir, "sklearn")
        self.sklearn_model = SklearnTriEnsemble()
        self.sklearn_model.fit(texts, y)
        self.sklearn_model.save(sklearn_dir)

        cnn_dir = os.path.join(output_dir, "textcnn")
        self._cnn_cfg = TextCNNConfig(epochs=10)
        model, vocab, _ = train_textcnn(texts, y, cfg=self._cnn_cfg, device=self._device)
        self._cnn_model = model
        self._cnn_vocab = vocab
        save_textcnn_bundle(cnn_dir, model, vocab, self._cnn_cfg, self._labels)

        meta = {"labels": self._labels, "sklearn_weight": self.sklearn_weight}
        with open(os.path.join(output_dir, "meta.json"), "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        preds = self.predict_batch(texts)
        correct = sum(1 for p, g in zip(preds, labels) if p["label"] == g)
        return {"accuracy": correct / len(labels), "total": len(labels)}

    def load(self, artifact_dir: str) -> None:
        with open(os.path.join(artifact_dir, "meta.json"), "r") as f:
            meta = json.load(f)
        self._labels = meta["labels"]
        self.sklearn_weight = meta.get("sklearn_weight", 0.5)
        self.sklearn_model = SklearnTriEnsemble.load(os.path.join(artifact_dir, "sklearn"))
        self._cnn_model, self._cnn_vocab, self._cnn_cfg, _ = load_textcnn_bundle(
            os.path.join(artifact_dir, "textcnn"), self._device
        )

    def predict_one(self, text: str) -> Dict:
        return self.predict_batch([text])[0]

    def predict_batch(self, texts: List[str]) -> List[Dict]:
        p_sklearn = self.sklearn_model.predict_proba_mean(texts)
        p_cnn = predict_proba_textcnn(
            self._cnn_model, self._cnn_vocab, texts, self._cnn_cfg, self._device
        )

        w = self.sklearn_weight
        p_fused = w * p_sklearn + (1 - w) * p_cnn

        results = []
        for probs in p_fused:
            idx = int(np.argmax(probs))
            results.append({
                "label": self._labels[idx],
                "confidence": float(probs[idx]),
                "is_job": self._labels[idx] == "job",
            })
        return results


class JobStageClassifier:
    """5分类：求职邮件阶段。"""

    def __init__(self, artifact_dir: Optional[str] = None):
        self.sklearn_model: Optional[SklearnTriEnsemble] = None
        self._cnn_model: Optional[TextCNN] = None
        self._cnn_vocab: Optional[Vocab] = None
        self._cnn_cfg: Optional[TextCNNConfig] = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.sklearn_weight: float = 0.5
        self._labels = STAGE_LABELS

        if artifact_dir:
            self.load(artifact_dir)

    def train(self, texts: List[str], labels: List[str], output_dir: str) -> Dict:
        os.makedirs(output_dir, exist_ok=True)

        label2idx = {l: i for i, l in enumerate(self._labels)}
        y = np.array([label2idx[l] for l in labels])

        sklearn_dir = os.path.join(output_dir, "sklearn")
        self.sklearn_model = SklearnTriEnsemble()
        self.sklearn_model.fit(texts, y)
        self.sklearn_model.save(sklearn_dir)

        cnn_dir = os.path.join(output_dir, "textcnn")
        self._cnn_cfg = TextCNNConfig(epochs=10)
        model, vocab, _ = train_textcnn(texts, y, cfg=self._cnn_cfg, device=self._device)
        self._cnn_model = model
        self._cnn_vocab = vocab
        save_textcnn_bundle(cnn_dir, model, vocab, self._cnn_cfg, self._labels)

        meta = {"labels": self._labels, "sklearn_weight": self.sklearn_weight}
        with open(os.path.join(output_dir, "meta.json"), "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        preds = self.predict_batch(texts)
        correct = sum(1 for p, g in zip(preds, labels) if p["stage"] == g)
        return {"accuracy": correct / len(labels), "total": len(labels)}

    def load(self, artifact_dir: str) -> None:
        with open(os.path.join(artifact_dir, "meta.json"), "r") as f:
            meta = json.load(f)
        self._labels = meta["labels"]
        self.sklearn_weight = meta.get("sklearn_weight", 0.5)
        self.sklearn_model = SklearnTriEnsemble.load(os.path.join(artifact_dir, "sklearn"))
        self._cnn_model, self._cnn_vocab, self._cnn_cfg, _ = load_textcnn_bundle(
            os.path.join(artifact_dir, "textcnn"), self._device
        )

    def predict_one(self, text: str) -> Dict:
        return self.predict_batch([text])[0]

    def predict_batch(self, texts: List[str]) -> List[Dict]:
        p_sklearn = self.sklearn_model.predict_proba_mean(texts)
        p_cnn = predict_proba_textcnn(
            self._cnn_model, self._cnn_vocab, texts, self._cnn_cfg, self._device
        )

        w = self.sklearn_weight
        p_fused = w * p_sklearn + (1 - w) * p_cnn

        results = []
        for probs in p_fused:
            idx = int(np.argmax(probs))
            results.append({
                "stage": self._labels[idx],
                "confidence": float(probs[idx]),
            })
        return results


def load_classifier_data(data_path: Path) -> Tuple[List[str], List[str], List[str]]:
    texts, det_labels, stage_labels = [], [], []
    with open(data_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            texts.append(row["text"])
            is_job = row["is_job"].lower() == "true"
            det_labels.append("job" if is_job else "not_job")
            stage_labels.append(row["label"] if is_job else "")
    return texts, det_labels, stage_labels
