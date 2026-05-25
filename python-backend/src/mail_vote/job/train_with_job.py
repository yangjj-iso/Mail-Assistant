"""合并 job 数据到 Stage 2 训练集并重新训练。"""

import os
import sys
import pandas as pd
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))


def merge_job_data():
    """将 job_classification.csv 合并到 train.csv 和 test.csv。"""
    data_dir = _REPO_ROOT / "data"
    hf_dir = data_dir / "hugging_face_jason"

    def read_csv_safe(path):
        try:
            return pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="latin-1", on_bad_lines="skip")

    # 读取原始数据
    train_df = read_csv_safe(hf_dir / "train.csv")
    test_df = read_csv_safe(hf_dir / "test.csv")
    job_df = read_csv_safe(data_dir / "job_classification.csv")

    print(f"Original train: {len(train_df)} samples")
    print(f"Original test: {len(test_df)} samples")
    print(f"Job data: {len(job_df)} samples")

    # 分割 job 数据为 train/test (80/20)
    from sklearn.model_selection import train_test_split
    job_train, job_test = train_test_split(job_df, test_size=0.2, random_state=42)

    # 合并
    train_merged = pd.concat([train_df, job_train], ignore_index=True)
    test_merged = pd.concat([test_df, job_test], ignore_index=True)

    # 保存到新文件
    train_merged.to_csv(hf_dir / "train_with_job.csv", index=False)
    test_merged.to_csv(hf_dir / "test_with_job.csv", index=False)

    print(f"Merged train: {len(train_merged)} samples")
    print(f"Merged test: {len(test_merged)} samples")
    print(f"Categories in train: {train_merged['category'].unique()}")

    return str(hf_dir / "train_with_job.csv"), str(hf_dir / "test_with_job.csv")


def train_stage2_with_job(train_csv: str, test_csv: str):
    """使用合并后的数据重新训练 Stage 2。"""
    from src.mail_vote import data_io
    from src.mail_vote.stages import train_stage, evaluate_stage_simple
    from src.mail_vote.textcnn import TextCNNConfig

    artifact_root = _REPO_ROOT / "artifacts"

    # 加载数据
    X_tr, y_tr, X_te, y_te, le = data_io.load_stage2_from_split(
        train_csv, test_csv, exclude_spam=True
    )

    names = list(le.classes_)
    print(f"Classes: {names}")
    print(f"Train samples: {len(X_tr)}, Test samples: {len(X_te)}")

    out_dir = str(artifact_root / "stage2")

    cfg = TextCNNConfig(
        epochs=6,
        batch_size=64,
        max_len=400,
        show_progress=True,
    )

    print("\n=== Training Stage 2 with job category ===")
    train_stage(
        X_tr, y_tr, names, out_dir,
        test_size=0.15,
        fusion_weight_sklearn=0.5,
        textcnn_cfg=cfg,
        max_features=50000,
        show_progress=True,
    )

    print("\n=== Evaluating ===")
    ev = evaluate_stage_simple(
        X_te, y_te, out_dir,
        fusion_weight_sklearn=0.5,
        plot_cm_path=os.path.join(out_dir, "confusion_matrix.png"),
    )
    print(f"Accuracy: {ev['accuracy']:.4f}")
    print(f"F1 Macro: {ev['f1_macro']:.4f}")
    print(ev["report"])


def main():
    print("Step 1: Merging job data...")
    train_csv, test_csv = merge_job_data()

    print("\nStep 2: Training Stage 2...")
    train_stage2_with_job(train_csv, test_csv)

    print("\nDone! Restart the ML service to use the new model.")


if __name__ == "__main__":
    main()
