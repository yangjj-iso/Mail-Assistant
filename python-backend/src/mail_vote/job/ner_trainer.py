"""NER 训练脚本：加载 JSONL 数据，构建词表，训练 BiLSTM-CRF。"""

from __future__ import annotations

import json
import torch
import torch.optim as optim
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter

from .ner_model import BiLSTMCRF, TAG2IDX, NUM_TAGS, PAD_IDX, UNK_IDX, PAD_CHAR


MAX_WORD_LEN = 10


class Vocabulary:
    def __init__(self, min_freq: int = 1):
        self.word2idx: Dict[str, int] = {"<PAD>": PAD_IDX, "<UNK>": UNK_IDX}
        self.char2idx: Dict[str, int] = {"<PAD>": PAD_CHAR, "<UNK>": 1}
        self.min_freq = min_freq

    def build(self, sentences: List[List[str]]) -> None:
        word_freq: Counter = Counter()
        char_freq: Counter = Counter()
        for tokens in sentences:
            word_freq.update(tokens)
            for t in tokens:
                char_freq.update(t)

        for w, freq in word_freq.items():
            if freq >= self.min_freq and w not in self.word2idx:
                self.word2idx[w] = len(self.word2idx)

        for c, freq in char_freq.items():
            if freq >= self.min_freq and c not in self.char2idx:
                self.char2idx[c] = len(self.char2idx)

    @property
    def vocab_size(self) -> int:
        return len(self.word2idx)

    @property
    def char_vocab_size(self) -> int:
        return len(self.char2idx)

    def encode_words(self, tokens: List[str]) -> List[int]:
        return [self.word2idx.get(t, UNK_IDX) for t in tokens]

    def encode_chars(self, tokens: List[str]) -> List[List[int]]:
        result = []
        for t in tokens:
            chars = [self.char2idx.get(c, 1) for c in t[:MAX_WORD_LEN]]
            chars += [PAD_CHAR] * (MAX_WORD_LEN - len(chars))
            result.append(chars)
        return result

    def save(self, path: Path) -> None:
        data = {"word2idx": self.word2idx, "char2idx": self.char2idx}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> "Vocabulary":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        vocab = cls()
        vocab.word2idx = data["word2idx"]
        vocab.char2idx = data["char2idx"]
        return vocab


def load_jsonl(path: Path) -> List[Dict]:
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def collate_batch(
    batch: List[Dict], vocab: Vocabulary
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    max_len = max(len(s["tokens"]) for s in batch)

    words_batch = []
    chars_batch = []
    tags_batch = []
    mask_batch = []

    for sample in batch:
        tokens = sample["tokens"]
        labels = sample["labels"]
        seq_len = len(tokens)

        word_ids = vocab.encode_words(tokens) + [PAD_IDX] * (max_len - seq_len)
        char_ids = vocab.encode_chars(tokens) + [[PAD_CHAR] * MAX_WORD_LEN] * (max_len - seq_len)
        tag_ids = [TAG2IDX.get(l, 0) for l in labels] + [0] * (max_len - seq_len)
        mask = [1.0] * seq_len + [0.0] * (max_len - seq_len)

        words_batch.append(word_ids)
        chars_batch.append(char_ids)
        tags_batch.append(tag_ids)
        mask_batch.append(mask)

    return (
        torch.tensor(words_batch, dtype=torch.long),
        torch.tensor(chars_batch, dtype=torch.long),
        torch.tensor(tags_batch, dtype=torch.long),
        torch.tensor(mask_batch, dtype=torch.float),
    )


def evaluate(model: BiLSTMCRF, data: List[Dict], vocab: Vocabulary,
             batch_size: int = 64, device: str = "cpu") -> Dict[str, float]:
    model.eval()
    correct = 0
    total = 0

    with torch.no_grad():
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            words, chars, tags, mask = collate_batch(batch, vocab)
            words, chars, mask = words.to(device), chars.to(device), mask.to(device)

            preds = model.predict(words, chars, mask)
            for j, pred_seq in enumerate(preds):
                gold = [TAG2IDX.get(l, 0) for l in batch[j]["labels"]]
                seq_len = len(gold)
                for k in range(seq_len):
                    if k < len(pred_seq):
                        total += 1
                        if pred_seq[k] == gold[k]:
                            correct += 1

    accuracy = correct / total if total > 0 else 0.0
    return {"accuracy": accuracy, "correct": correct, "total": total}


def train(
    train_path: Path,
    test_path: Path,
    output_dir: Path,
    epochs: int = 30,
    batch_size: int = 32,
    lr: float = 0.001,
    device: str = "cpu",
    patience: int = 5,
    hidden_dim: int = 200,
    num_layers: int = 2,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    train_data = load_jsonl(train_path)
    test_data = load_jsonl(test_path)
    print(f"Train: {len(train_data)}, Test: {len(test_data)}")

    vocab = Vocabulary(min_freq=1)
    vocab.build([s["tokens"] for s in train_data])
    vocab.save(output_dir / "vocab.json")
    print(f"Vocab: {vocab.vocab_size} words, {vocab.char_vocab_size} chars")

    model = BiLSTMCRF(
        vocab_size=vocab.vocab_size,
        char_vocab_size=vocab.char_vocab_size,
        hidden_dim=hidden_dim,
        num_layers=num_layers,
    ).to(device)

    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=2, factor=0.5)

    best_acc = 0.0
    no_improve = 0

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        indices = list(range(len(train_data)))
        import random
        random.shuffle(indices)
        shuffled = [train_data[i] for i in indices]

        for i in range(0, len(shuffled), batch_size):
            batch = shuffled[i:i + batch_size]
            words, chars, tags, mask = collate_batch(batch, vocab)
            words = words.to(device)
            chars = chars.to(device)
            tags = tags.to(device)
            mask = mask.to(device)

            optimizer.zero_grad()
            loss = model.loss(words, chars, tags, mask)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            total_loss += loss.item()

        avg_loss = total_loss / (len(shuffled) // batch_size + 1)
        metrics = evaluate(model, test_data, vocab, batch_size, device)
        scheduler.step(avg_loss)

        print(f"Epoch {epoch}: loss={avg_loss:.4f}, acc={metrics['accuracy']:.4f}")

        if metrics["accuracy"] > best_acc:
            best_acc = metrics["accuracy"]
            no_improve = 0
            torch.save(model.state_dict(), output_dir / "model.pt")
            meta = {
                "vocab_size": vocab.vocab_size,
                "char_vocab_size": vocab.char_vocab_size,
                "hidden_dim": hidden_dim,
                "num_layers": num_layers,
                "best_accuracy": best_acc,
                "epoch": epoch,
            }
            with open(output_dir / "meta.json", "w") as f:
                json.dump(meta, f)
            print(f"  -> Saved best model (acc={best_acc:.4f})")
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"Early stopping at epoch {epoch}")
                break

    print(f"Training complete. Best accuracy: {best_acc:.4f}")
