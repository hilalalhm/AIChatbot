from __future__ import annotations

from typing import List


def split_message(text: str, max_len: int = 4096) -> List[str]:
    """Split a Telegram message into chunks, preferring paragraph > newline > space."""
    if len(text) <= max_len:
        return [text]

    chunks: List[str] = []
    remaining = text
    while len(remaining) > max_len:
        chunk, remaining = _take_chunk(remaining, max_len)
        chunks.append(chunk)
    if remaining:
        chunks.append(remaining)
    return chunks


def _take_chunk(text: str, max_len: int) -> tuple:
    if len(text) <= max_len:
        return text, ""

    segment = text[:max_len]

    # 1. Paragraph break
    idx = segment.rfind("\n\n")
    if idx > max_len // 2:
        return segment[: idx + 2], text[idx + 2 :]

    # 2. Newline
    idx = segment.rfind("\n")
    if idx > max_len // 2:
        return segment[: idx + 1], text[idx + 1 :]

    # 3. Whitespace
    idx = segment.rfind(" ")
    if idx > max_len // 2:
        return segment[: idx + 1], text[idx + 1 :]

    # 4. Hard split
    return segment, text[max_len:]
