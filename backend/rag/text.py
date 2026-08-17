"""Text normalization and lightweight token estimation."""

from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str, *, preserve_code: bool = False) -> str:
    text = text.replace("\x00", "")
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if preserve_code:
        return "\n".join(line.rstrip() for line in text.split("\n")).strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def stable_excerpt(text: str, limit: int = 240) -> str:
    candidate = " ".join(text.split())
    if len(candidate) <= limit:
        return candidate
    return f"{candidate[: max(0, limit - 3)].rstrip()}..."
