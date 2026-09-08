from __future__ import annotations

import re

_WORD_RE = re.compile(r"\S+")


def estimate_tokens(text: str) -> int:
    """Rough token estimator: ~4 chars per token, min 1 token."""
    if not text:
        return 0
    return max(1, len(text) // 4)
