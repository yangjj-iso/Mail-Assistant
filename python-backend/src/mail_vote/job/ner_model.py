"""BiLSTM-CRF model for Named Entity Recognition."""

from __future__ import annotations

import torch
import torch.nn as nn
from typing import List, Optional, Tuple


TAG_SET = [
    "O",
    "B-COMPANY", "I-COMPANY",
    "B-POSITION", "I-POSITION",
    "B-TIME", "I-TIME",
    "B-ROUND", "I-ROUND",
    "B-LOCATION", "I-LOCATION",
]
TAG2IDX = {t: i for i, t in enumerate(TAG_SET)}
IDX2TAG = {i: t for t, i in TAG2IDX.items()}
NUM_TAGS = len(TAG_SET)

PAD_IDX = 0
UNK_IDX = 1
PAD_CHAR = 0


class CharCNN(nn.Module):
    def __init__(self, char_vocab_size: int, char_embed_dim: int = 30,
                 out_channels: int = 50, kernel_size: int = 3):
        super().__init__()
        self.embed = nn.Embedding(char_vocab_size, char_embed_dim, padding_idx=PAD_CHAR)
        self.conv = nn.Conv1d(char_embed_dim, out_channels, kernel_size, padding=kernel_size // 2)
        self.out_dim = out_channels

    def forward(self, chars: torch.Tensor) -> torch.Tensor:
        # chars: (batch, seq_len, max_word_len)
        batch, seq_len, max_wl = chars.shape
        chars = chars.view(batch * seq_len, max_wl)
        x = self.embed(chars)  # (B*S, W, E)
        x = x.transpose(1, 2)  # (B*S, E, W)
        x = self.conv(x)  # (B*S, C, W)
        x = torch.max(x, dim=2).values  # (B*S, C)
        return x.view(batch, seq_len, -1)


class CRF(nn.Module):
    def __init__(self, num_tags: int):
        super().__init__()
        self.num_tags = num_tags
        self.transitions = nn.Parameter(torch.randn(num_tags, num_tags))
        self.start_transitions = nn.Parameter(torch.randn(num_tags))
        self.end_transitions = nn.Parameter(torch.randn(num_tags))

    def _compute_score(self, emissions: torch.Tensor, tags: torch.Tensor,
                       mask: torch.Tensor) -> torch.Tensor:
        batch, seq_len, _ = emissions.shape
        score = self.start_transitions[tags[:, 0]] + emissions[:, 0].gather(1, tags[:, 0:1]).squeeze(1)

        for i in range(1, seq_len):
            cur_tag = tags[:, i]
            prev_tag = tags[:, i - 1]
            emit = emissions[:, i].gather(1, cur_tag.unsqueeze(1)).squeeze(1)
            trans = self.transitions[cur_tag, prev_tag]
            step_score = (emit + trans) * mask[:, i]
            score = score + step_score

        last_idx = mask.long().sum(dim=1) - 1
        last_tag = tags.gather(1, last_idx.unsqueeze(1)).squeeze(1)
        score = score + self.end_transitions[last_tag]
        return score

    def _compute_normalizer(self, emissions: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        batch, seq_len, num_tags = emissions.shape
        score = self.start_transitions + emissions[:, 0]  # (B, T)

        for i in range(1, seq_len):
            broadcast_score = score.unsqueeze(2)  # (B, T, 1)
            broadcast_emit = emissions[:, i].unsqueeze(1)  # (B, 1, T)
            next_score = broadcast_score + self.transitions.unsqueeze(0) + broadcast_emit  # (B, T, T)
            next_score = torch.logsumexp(next_score, dim=1)  # (B, T)
            score = torch.where(mask[:, i].unsqueeze(1).bool(), next_score, score)

        score = score + self.end_transitions
        return torch.logsumexp(score, dim=1)

    def forward(self, emissions: torch.Tensor, tags: torch.Tensor,
                mask: torch.Tensor) -> torch.Tensor:
        nll = self._compute_normalizer(emissions, mask) - self._compute_score(emissions, tags, mask)
        return nll.mean()

    def decode(self, emissions: torch.Tensor, mask: torch.Tensor) -> List[List[int]]:
        batch, seq_len, num_tags = emissions.shape
        score = self.start_transitions + emissions[:, 0]
        history: List[torch.Tensor] = []

        for i in range(1, seq_len):
            broadcast_score = score.unsqueeze(2)
            broadcast_emit = emissions[:, i].unsqueeze(1)
            next_score = broadcast_score + self.transitions.unsqueeze(0) + broadcast_emit
            next_score, indices = next_score.max(dim=1)
            score = torch.where(mask[:, i].unsqueeze(1).bool(), next_score, score)
            history.append(indices)

        score = score + self.end_transitions
        best_tags_list: List[List[int]] = []

        for b in range(batch):
            seq_length = int(mask[b].sum().item())
            best_last = score[b].argmax().item()
            best_tags = [best_last]
            for i in range(seq_length - 2, -1, -1):
                best_last = history[i][b][best_last].item()
                best_tags.append(best_last)
            best_tags.reverse()
            best_tags_list.append(best_tags)

        return best_tags_list


class BiLSTMCRF(nn.Module):
    def __init__(self, vocab_size: int, char_vocab_size: int,
                 word_embed_dim: int = 128, char_embed_dim: int = 30,
                 char_out_dim: int = 50, hidden_dim: int = 200,
                 num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.word_embed = nn.Embedding(vocab_size, word_embed_dim, padding_idx=PAD_IDX)
        self.char_cnn = CharCNN(char_vocab_size, char_embed_dim, char_out_dim)
        self.dropout = nn.Dropout(dropout)

        lstm_input = word_embed_dim + char_out_dim
        self.lstm = nn.LSTM(
            lstm_input, hidden_dim // 2,
            num_layers=num_layers, batch_first=True,
            bidirectional=True, dropout=dropout if num_layers > 1 else 0,
        )
        self.hidden2tag = nn.Linear(hidden_dim, NUM_TAGS)
        self.crf = CRF(NUM_TAGS)

    def _get_emissions(self, words: torch.Tensor, chars: torch.Tensor,
                       mask: torch.Tensor) -> torch.Tensor:
        word_emb = self.word_embed(words)
        char_emb = self.char_cnn(chars)
        x = torch.cat([word_emb, char_emb], dim=-1)
        x = self.dropout(x)

        lengths = mask.sum(dim=1).cpu()
        packed = nn.utils.rnn.pack_padded_sequence(
            x, lengths, batch_first=True, enforce_sorted=False
        )
        lstm_out, _ = self.lstm(packed)
        lstm_out, _ = nn.utils.rnn.pad_packed_sequence(lstm_out, batch_first=True)
        emissions = self.hidden2tag(self.dropout(lstm_out))
        return emissions

    def loss(self, words: torch.Tensor, chars: torch.Tensor,
             tags: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        emissions = self._get_emissions(words, chars, mask)
        return self.crf(emissions, tags, mask)

    def predict(self, words: torch.Tensor, chars: torch.Tensor,
                mask: torch.Tensor) -> List[List[int]]:
        emissions = self._get_emissions(words, chars, mask)
        return self.crf.decode(emissions, mask)
