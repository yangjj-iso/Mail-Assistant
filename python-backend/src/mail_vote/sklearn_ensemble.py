"""TF-IDF + NB / Calibrated LinearSVC / XGBoost 与三模型软平均。"""

from __future__ import annotations

import json
import os
from typing import List, Optional

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from tqdm import tqdm
from xgboost import XGBClassifier


class SklearnTriEnsemble:
    """共享同一向量化后的三分类器及软平均概率。"""

    def __init__(
        self,
        max_features: int = 50000,
        ngram_range: tuple = (1, 2),
        xgb_n_estimators: int = 200,
        xgb_max_depth: int = 6,
        random_state: int = 42,
    ):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            lowercase=True,
            strip_accents="unicode",
            min_df=2,
            sublinear_tf=True,
        )
        self.nb = MultinomialNB(alpha=0.1)
        self.svc = CalibratedClassifierCV(
            LinearSVC(max_iter=8000, dual=False, class_weight="balanced", random_state=random_state),
            method="sigmoid",
            cv=3,
        )
        self.xgb = XGBClassifier(
            n_estimators=xgb_n_estimators,
            max_depth=xgb_max_depth,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=random_state,
            tree_method="hist",
            n_jobs=-1,
        )
        self._classes: Optional[np.ndarray] = None
        self._n_classes: int = 0

    def fit(self, texts: List[str], y: np.ndarray, show_progress: bool = True) -> "SklearnTriEnsemble":
        y = np.asarray(y).astype(np.int32).ravel()
        self._classes = np.unique(y)
        self._n_classes = len(self._classes)
        if self._n_classes < 2:
            raise ValueError("y 至少需要 2 个类别，当前 unique=%s" % (self._classes,))
        pbar = None
        if show_progress:
            pbar = tqdm(total=4, desc="Sklearn 三模型", unit="step", ncols=100)

        def _step(msg: str) -> None:
            if pbar is not None:
                pbar.set_postfix_str(msg)
                pbar.update(1)

        X = self.vectorizer.fit_transform(texts)
        _step("TF-IDF 完成")
        if X.shape[1] == 0:
            if pbar is not None:
                pbar.close()
            raise ValueError("TF-IDF 无特征列，请降低 min_df 或增大语料。")
        if self._n_classes == 2:
            self.xgb.set_params(objective="binary:logistic", eval_metric="logloss")
        else:
            self.xgb.set_params(objective="multi:softprob", eval_metric="mlogloss")
        self.nb.fit(X, y)
        _step("朴素贝叶斯")
        self.svc.fit(X, y)
        _step("校准 LinearSVC")
        self.xgb.fit(X, y)
        _step("XGBoost")
        if pbar is not None:
            pbar.close()
        return self

    def _transform(self, texts: List[str]):
        return self.vectorizer.transform(texts)

    def predict_proba_triple(self, texts: List[str]) -> tuple:
        X = self._transform(texts)
        p_nb = self.nb.predict_proba(X)
        p_svc = self.svc.predict_proba(X)
        p_xgb = self.xgb.predict_proba(X)
        return p_nb, p_svc, p_xgb

    def predict_proba_mean(self, texts: List[str]) -> np.ndarray:
        p_nb, p_svc, p_xgb = self.predict_proba_triple(texts)
        return (p_nb + p_svc + p_xgb) / 3.0

    def predict(self, texts: List[str]) -> np.ndarray:
        proba = self.predict_proba_mean(texts)
        return self._classes.take(np.argmax(proba, axis=1))

    def argmax_components(self, texts: List[str]) -> tuple:
        """三基学习器各自 argmax 类别索引，与 predict_proba 列顺序一致。"""
        p_nb, p_svc, p_xgb = self.predict_proba_triple(texts)
        return (
            np.argmax(p_nb, axis=1),
            np.argmax(p_svc, axis=1),
            np.argmax(p_xgb, axis=1),
        )

    @property
    def classes_(self) -> np.ndarray:
        if self._classes is None:
            raise RuntimeError("Model not fitted")
        return self._classes

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        joblib.dump(self.vectorizer, os.path.join(directory, "vectorizer.joblib"))
        joblib.dump(self.nb, os.path.join(directory, "nb.joblib"))
        joblib.dump(self.svc, os.path.join(directory, "svc_calibrated.joblib"))
        joblib.dump(self.xgb, os.path.join(directory, "xgb.joblib"))
        meta = {"classes": [str(c) for c in self._classes.tolist()], "n_classes": int(self._n_classes)}
        with open(os.path.join(directory, "sklearn_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, directory: str) -> "SklearnTriEnsemble":
        obj = cls()
        obj.vectorizer = joblib.load(os.path.join(directory, "vectorizer.joblib"))
        obj.nb = joblib.load(os.path.join(directory, "nb.joblib"))
        obj.svc = joblib.load(os.path.join(directory, "svc_calibrated.joblib"))
        obj.xgb = joblib.load(os.path.join(directory, "xgb.joblib"))
        with open(os.path.join(directory, "sklearn_meta.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)
        obj._classes = np.array(meta["classes"])
        obj._n_classes = int(meta["n_classes"])
        return obj
