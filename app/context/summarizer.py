from __future__ import annotations

import logging
from typing import Callable, List, Optional

from app.context.memory import estimate_tokens

logger = logging.getLogger(__name__)

SYSTEM_SUMMARY_PROMPT = (
    "Anda adalah perangkum percakapan. Ringkaslah percakapan berikut dalam Bahasa "
    "Indonesia dengan menyimpan: tujuan pengguna, status proyek, keputusan, konfigurasi "
    "penting, preferensi, kendala, masalah yang belum selesai, fakta penting, dan tugas "
    "saat ini. Jangan menghapus informasi penting. Jangan mengarang informasi baru."
)


class Summarizer:
    def __init__(
        self,
        summarize_fn: Optional[Callable[[str], str]] = None,
        max_chars: int = 4000,
    ):
        self._summarize_fn = summarize_fn
        self.max_chars = max_chars

    def should_summarize(self, transcript: str, trigger_tokens: int) -> bool:
        return estimate_tokens(transcript) >= trigger_tokens

    def summarize(self, transcript: str) -> str:
        if self._summarize_fn is None:
            # Deterministic fallback: tail-trim the transcript to a bounded length.
            return transcript[-self.max_chars :] if transcript else ""
        try:
            result = self._summarize_fn(transcript)
            if not result:
                return transcript[-self.max_chars :] if transcript else ""
            return result[: self.max_chars]
        except Exception:
            logger.exception("Summarizer failed; using bounded tail.")
            return transcript[-self.max_chars :] if transcript else ""
