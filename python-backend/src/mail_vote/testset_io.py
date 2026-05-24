"""labeled_email_testset：读取 dataset.json，将纯正文文件解析为模型输入文本。"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List


def clean_join(subject: str, body: str) -> str:
    s = f"{(subject or '').strip()} {(body or '').strip()}".strip()
    return " ".join(s.split())


def parse_email_file_to_text(raw: str) -> str:
    """
    支持两种无标签泄露格式：
    1) Subject: ... 后空行 Body: 后接正文
    2) [Subject] / [Body] 分段（不含类别名元数据）
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    if low.startswith("subject:"):
        subject = ""
        body = ""
        lines = raw.splitlines()
        i = 0
        if lines and lines[0].lower().startswith("subject:"):
            subject = lines[0].split(":", 1)[1].strip()
            i = 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i < len(lines) and lines[i].strip().lower().startswith("body:"):
            rest = lines[i].split(":", 1)[1].strip()
            body_lines = ([rest] if rest else []) + lines[i + 1 :]
            body = "\n".join(body_lines).strip()
        else:
            body = "\n".join(lines[i:]).strip()
        return clean_join(subject, body)
    if "[subject]" in low:
        parts = raw.split("[Subject]", 1)[1] if "[Subject]" in raw else raw.split("[subject]", 1)[1]
        if "[Body]" in parts or "[body]" in parts:
            sp = parts.replace("[body]", "[Body]")
            subj_part, body_part = sp.split("[Body]", 1)
            subject = subj_part.strip()
            body = body_part.strip()
            return clean_join(subject, body)
    return clean_join("", raw)


def load_dataset_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_email_path(dataset_dir: str, email_file: str) -> str:
    return os.path.normpath(os.path.join(dataset_dir, email_file))


def load_item_text(dataset_dir: str, email_file: str) -> str:
    p = resolve_email_path(dataset_dir, email_file)
    with open(p, "r", encoding="utf-8") as f:
        return parse_email_file_to_text(f.read())


def iter_items(dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(dataset.get("items") or [])
