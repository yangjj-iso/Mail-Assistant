"""英文 TextCNN：词表、训练、predict_proba。"""

from __future__ import annotations

import json
import os
import pickle
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm


def tokenize(text: str) -> List[str]:
    return [w for w in text.lower().replace("\n", " ").split() if w]


class Vocab:
    def __init__(self, token_freq: List[Tuple[str, int]], max_size: int = 50000):
        self.token2idx = {"<pad>": 0, "<unk>": 1}
        for tok, _ in token_freq[: max_size - 2]:
            if tok not in self.token2idx:
                self.token2idx[tok] = len(self.token2idx)
        self.idx2token = {v: k for k, v in self.token2idx.items()}

    def __len__(self) -> int:
        return len(self.token2idx)

    def encode(self, tokens: List[str]) -> List[int]:
        unk = self.token2idx["<unk>"]
        return [self.token2idx.get(t, unk) for t in tokens]


@dataclass
class TextCNNConfig:
    embed_dim: int = 128
    kernel_num: int = 100
    kernel_sizes: Tuple[int, ...] = (3, 4, 5)
    dropout: float = 0.5
    batch_size: int = 64
    epochs: int = 8
    lr: float = 0.001
    max_len: int = 400
    vocab_max: int = 50000
    show_progress: bool = True


class TextCNN(nn.Module):
    def __init__(self, vocab_size: int, class_num: int, cfg: TextCNNConfig):
        super().__init__()
        self.cfg = cfg
        D = cfg.embed_dim
        Co = cfg.kernel_num
        Ks = cfg.kernel_sizes
        self.embed = nn.Embedding(vocab_size, D, padding_idx=0)
        self.convs = nn.ModuleList([nn.Conv2d(1, Co, (K, D)) for K in Ks])
        self.dropout = nn.Dropout(cfg.dropout)
        self.fc = nn.Linear(len(Ks) * Co, class_num)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.embed(x)
        x = x.unsqueeze(1)
        feats = []
        for conv in self.convs:
            h = F.relu(conv(x)).squeeze(3)
            h = F.max_pool1d(h, h.size(2)).squeeze(2)
            feats.append(h)
        h = torch.cat(feats, dim=1)
        h = self.dropout(h)
        return self.fc(h)


class TextDataset(Dataset):
    def __init__(self, texts: List[str], labels: np.ndarray, vocab: Vocab, max_len: int):
        self.texts = texts
        self.labels = labels.astype(np.int64)
        self.vocab = vocab
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, i: int):
        ids = self.vocab.encode(tokenize(self.texts[i]))[: self.max_len]
        if len(ids) < self.max_len:
            ids = ids + [0] * (self.max_len - len(ids))
        return torch.tensor(ids, dtype=torch.long), torch.tensor(self.labels[i], dtype=torch.long)


def build_vocab(texts: List[str], max_tokens: int) -> Vocab:
    cnt = Counter()
    for t in texts:
        cnt.update(tokenize(t))
    return Vocab(cnt.most_common(max_tokens), max_size=max_tokens)


def train_textcnn(
    train_texts: List[str],
    y_train: np.ndarray,
    val_texts: Optional[List[str]] = None,
    y_val: Optional[np.ndarray] = None,
    cfg: Optional[TextCNNConfig] = None,
    device: Optional[torch.device] = None,
) -> Tuple[TextCNN, Vocab, float]:
    cfg = cfg or TextCNNConfig()
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    vocab = build_vocab(train_texts, cfg.vocab_max)
    n_classes = int(y_train.max()) + 1
    model = TextCNN(len(vocab), n_classes, cfg).to(device)
    ds = TextDataset(train_texts, y_train, vocab, cfg.max_len)
    dl = DataLoader(ds, batch_size=cfg.batch_size, shuffle=True, drop_last=False)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr, weight_decay=1e-4)
    best_val = -1.0
    best_state = None
    epoch_iter = range(cfg.epochs)
    if cfg.show_progress:
        epoch_iter = tqdm(
            epoch_iter,
            desc="TextCNN 训练轮次",
            unit="epoch",
            leave=True,
            ncols=100,
        )
    for epoch in epoch_iter:
        model.train()
        total, correct, n = 0.0, 0.0, 0
        batch_iter = dl
        if cfg.show_progress:
            batch_iter = tqdm(
                dl,
                desc=f"TextCNN epoch {epoch + 1}/{cfg.epochs} 批次",
                leave=False,
                ncols=100,
            )
        for xb, yb in batch_iter:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = F.cross_entropy(logits, yb)
            loss.backward()
            opt.step()
            pred = logits.argmax(dim=1)
            correct += (pred == yb).sum().item()
            total += loss.item() * xb.size(0)
            n += xb.size(0)
            if cfg.show_progress and hasattr(batch_iter, "set_postfix"):
                batch_iter.set_postfix(loss=f"{total / max(n, 1):.4f}", acc=f"{100.0 * correct / max(n, 1):.1f}%")
        if val_texts is not None and y_val is not None:
            acc = _accuracy(model, val_texts, y_val, vocab, cfg, device)
            if acc > best_val:
                best_val = acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            if cfg.show_progress and isinstance(epoch_iter, tqdm):
                epoch_iter.set_postfix(val_acc=f"{100.0 * acc:.1f}%", best_val_acc=f"{100.0 * best_val:.1f}%")
        else:
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_val = 0.0
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, vocab, best_val


def _accuracy(model, texts, y, vocab, cfg, device):
    model.eval()
    ds = TextDataset(texts, y, vocab, cfg.max_len)
    dl = DataLoader(ds, batch_size=cfg.batch_size, shuffle=False)
    correct, n = 0, 0
    with torch.no_grad():
        for xb, yb in dl:
            xb, yb = xb.to(device), yb.to(device)
            pred = model(xb).argmax(dim=1)
            correct += (pred == yb).sum().item()
            n += xb.size(0)
    return correct / max(n, 1)


@torch.no_grad()
def predict_proba_textcnn(
    model: TextCNN,
    vocab: Vocab,
    texts: List[str],
    cfg: TextCNNConfig,
    device: torch.device,
    batch_size: int = 64,
) -> np.ndarray:
    model.eval()
    ds = TextDataset(texts, np.zeros(len(texts), dtype=np.int64), vocab, cfg.max_len)
    dl = DataLoader(ds, batch_size=batch_size, shuffle=False)
    outs = []
    batch_iter = dl
    if cfg.show_progress and len(texts) >= 32:
        batch_iter = tqdm(dl, desc="TextCNN 推理批次", leave=False, ncols=100)
    for xb, _ in batch_iter:
        xb = xb.to(device)
        logits = model(xb)
        prob = F.softmax(logits, dim=1).cpu().numpy()
        outs.append(prob)
    return np.vstack(outs)


def save_textcnn_bundle(path_dir: str, model: TextCNN, vocab: Vocab, cfg: TextCNNConfig, class_names: List[str]) -> None:
    os.makedirs(path_dir, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(path_dir, "textcnn.pt"))
    with open(os.path.join(path_dir, "vocab.pkl"), "wb") as f:
        pickle.dump(vocab, f)
    meta = {
        "class_names": class_names,
        "embed_dim": cfg.embed_dim,
        "kernel_num": cfg.kernel_num,
        "kernel_sizes": list(cfg.kernel_sizes),
        "dropout": cfg.dropout,
        "max_len": cfg.max_len,
        "vocab_max": cfg.vocab_max,
    }
    with open(os.path.join(path_dir, "textcnn_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def load_textcnn_bundle(path_dir: str, device: torch.device) -> Tuple[TextCNN, Vocab, TextCNNConfig, List[str]]:
    with open(os.path.join(path_dir, "textcnn_meta.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)
    cfg = TextCNNConfig(
        embed_dim=meta["embed_dim"],
        kernel_num=meta["kernel_num"],
        kernel_sizes=tuple(meta["kernel_sizes"]),
        dropout=meta["dropout"],
        max_len=meta["max_len"],
        vocab_max=meta["vocab_max"],
    )
    with open(os.path.join(path_dir, "vocab.pkl"), "rb") as f:
        vocab = pickle.load(f)
    class_names = meta["class_names"]
    model = TextCNN(len(vocab), len(class_names), cfg).to(device)
    state = torch.load(os.path.join(path_dir, "textcnn.pt"), map_location=device)
    model.load_state_dict(state)
    model.eval()
    return model, vocab, cfg, class_names
