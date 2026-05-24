"""NER 推理接口：加载训练好的模型，对文本进行实体提取。"""

from __future__ import annotations

import json
import torch
from pathlib import Path
from typing import Dict, List, Optional

from .ner_model import BiLSTMCRF, IDX2TAG, NUM_TAGS
from .ner_trainer import Vocabulary, MAX_WORD_LEN, PAD_CHAR, PAD_IDX


class NERPredictor:
    def __init__(self, model_dir: Path, device: str = "cpu"):
        self.device = device
        self.model_dir = model_dir

        with open(model_dir / "meta.json", "r") as f:
            meta = json.load(f)

        self.vocab = Vocabulary.load(model_dir / "vocab.json")

        self.model = BiLSTMCRF(
            vocab_size=meta["vocab_size"],
            char_vocab_size=meta["char_vocab_size"],
        ).to(device)
        self.model.load_state_dict(
            torch.load(model_dir / "model.pt", map_location=device, weights_only=True)
        )
        self.model.eval()

    def _tokenize(self, text: str) -> List[str]:
        tokens: List[str] = []
        buf = ""
        for ch in text:
            if ch.isascii() and ch.isalpha():
                buf += ch
            else:
                if buf:
                    tokens.append(buf)
                    buf = ""
                if ch.strip():
                    tokens.append(ch)
        if buf:
            tokens.append(buf)
        return tokens

    def _decode_entities(self, tokens: List[str], tag_ids: List[int]) -> Dict[str, List[str]]:
        entities: Dict[str, List[str]] = {}
        current_type: Optional[str] = None
        current_tokens: List[str] = []

        for i, tag_id in enumerate(tag_ids):
            if i >= len(tokens):
                break
            tag = IDX2TAG.get(tag_id, "O")

            if tag.startswith("B-"):
                if current_type and current_tokens:
                    ent_text = "".join(current_tokens)
                    entities.setdefault(current_type, []).append(ent_text)
                current_type = tag[2:]
                current_tokens = [tokens[i]]
            elif tag.startswith("I-") and current_type == tag[2:]:
                current_tokens.append(tokens[i])
            else:
                if current_type and current_tokens:
                    ent_text = "".join(current_tokens)
                    entities.setdefault(current_type, []).append(ent_text)
                current_type = None
                current_tokens = []

        if current_type and current_tokens:
            ent_text = "".join(current_tokens)
            entities.setdefault(current_type, []).append(ent_text)

        return entities

    def predict(self, text: str) -> Dict[str, List[str]]:
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        word_ids = self.vocab.encode_words(tokens)
        char_ids = self.vocab.encode_chars(tokens)
        mask = [1.0] * len(tokens)

        words = torch.tensor([word_ids], dtype=torch.long, device=self.device)
        chars = torch.tensor([char_ids], dtype=torch.long, device=self.device)
        mask_t = torch.tensor([mask], dtype=torch.float, device=self.device)

        with torch.no_grad():
            pred_tags = self.model.predict(words, chars, mask_t)

        return self._decode_entities(tokens, pred_tags[0])

    def predict_batch(self, texts: List[str]) -> List[Dict[str, List[str]]]:
        results = []
        for text in texts:
            results.append(self.predict(text))
        return results
