"""粗/细语料加载与子采样。"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


def _clean_text(s: str) -> str:
    s = (s or "").strip()
    return " ".join(s.split())


def load_stage1(
    path: str,
    max_samples: Optional[int] = None,
    random_state: int = 42,
) -> Tuple[List[str], np.ndarray, LabelEncoder]:
    """
    加载粗 CSV：Subject + Message -> 文本；Spam/Ham -> 标签。
    max_samples 非空时按标签分层子采样。
    """
    try:
        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip", low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip", low_memory=False)
    except TypeError:
        try:
            df = pd.read_csv(path, encoding="utf-8", error_bad_lines=False, warn_bad_lines=False, low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="latin-1", error_bad_lines=False, warn_bad_lines=False, low_memory=False)
    subj = df.get("Subject", pd.Series([""] * len(df))).fillna("").astype(str)
    msg = df.get("Message", pd.Series([""] * len(df))).fillna("").astype(str)
    texts = [_clean_text(a + " " + b) for a, b in zip(subj, msg)]
    raw_y = df["Spam/Ham"].astype(str).str.lower().str.strip()
    le = LabelEncoder()
    y = le.fit_transform(raw_y)
    if max_samples is not None and int(max_samples) > 0 and len(texts) > int(max_samples):
        idx = np.arange(len(texts))
        strat = y if len(np.unique(y)) > 1 else None
        idx, _ = train_test_split(
            idx,
            train_size=max_samples,
            random_state=random_state,
            stratify=strat,
        )
        texts = [texts[i] for i in idx]
        y = y[idx]
    return texts, y, le


def load_stage2_from_split(
    train_path: str,
    test_path: str,
    exclude_spam: bool = True,
    text_column: str = "text",
    label_column: str = "category",
) -> Tuple[List[str], np.ndarray, List[str], np.ndarray, LabelEncoder]:
    """
    从已划分的 train/test CSV 加载阶段二数据；可选排除 category == spam。
    返回 train 文本/标签、test 文本/标签、LabelEncoder（在 train 上 fit）。
    """
    def _read_csv(p: str) -> pd.DataFrame:
        try:
            return pd.read_csv(p, encoding="utf-8", on_bad_lines="skip")
        except UnicodeDecodeError:
            return pd.read_csv(p, encoding="latin-1", on_bad_lines="skip")
        except TypeError:
            try:
                return pd.read_csv(p, encoding="utf-8", error_bad_lines=False)
            except UnicodeDecodeError:
                return pd.read_csv(p, encoding="latin-1", error_bad_lines=False)

    train_df = _read_csv(train_path)
    test_df = _read_csv(test_path)
    if exclude_spam:
        train_df = train_df[train_df[label_column].astype(str).str.lower() != "spam"]
        test_df = test_df[test_df[label_column].astype(str).str.lower() != "spam"]
    X_train = [_clean_text(t) for t in train_df[text_column].fillna("").astype(str)]
    X_test = [_clean_text(t) for t in test_df[text_column].fillna("").astype(str)]
    le = LabelEncoder()
    y_train = le.fit_transform(train_df[label_column].astype(str))
    # test 中若出现 train 未见的类，先统一为已知类集合
    train_classes = set(le.classes_)
    test_labels = test_df[label_column].astype(str)
    mask = test_labels.isin(train_classes)
    if not mask.all():
        dropped = int((~mask).sum())
        test_df = test_df.loc[mask].reset_index(drop=True)
        X_test = [_clean_text(t) for t in test_df[text_column].fillna("").astype(str)]
        test_labels = test_df[label_column].astype(str)
    y_test = le.transform(test_labels)
    return X_train, y_train, X_test, y_test, le


def load_stage2_single_csv(
    path: str,
    test_size: float = 0.2,
    exclude_spam: bool = True,
    random_state: int = 42,
    text_column: str = "text",
    label_column: str = "category",
) -> Tuple[List[str], np.ndarray, List[str], np.ndarray, LabelEncoder]:
    """从单一细 CSV 随机划分 train/test。"""
    try:
        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip")
    except TypeError:
        try:
            df = pd.read_csv(path, encoding="utf-8", error_bad_lines=False)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="latin-1", error_bad_lines=False)
    if exclude_spam:
        df = df[df[label_column].astype(str).str.lower() != "spam"].reset_index(drop=True)
    texts = [_clean_text(t) for t in df[text_column].fillna("").astype(str)]
    y_raw = df[label_column].astype(str)
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    return X_train, y_train, X_test, y_test, le


def default_paths(repo_root: Optional[str] = None) -> dict:
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return {
        "coarse": os.path.join(root, "data", "粗.csv"),
        "fine_train": os.path.join(root, "data", "hugging_face_jason", "train.csv"),
        "fine_test": os.path.join(root, "data", "hugging_face_jason", "test.csv"),
        "fine_full": os.path.join(root, "data", "细.csv"),
    }
