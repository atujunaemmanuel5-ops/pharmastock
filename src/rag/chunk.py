"""Small, citation-preserving text chunk helpers."""

from __future__ import annotations

import re


def chunk_text(text: str, max_words: int = 350, overlap: int = 40) -> list[str]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(len(words), start + max_words)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(start + 1, end - overlap)
    return chunks
