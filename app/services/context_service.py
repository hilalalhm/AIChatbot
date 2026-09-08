from __future__ import annotations

from typing import List, Optional

from app.config import settings
from app.context.manager import ContextMessage, ContextSnapshot
from app.context.memory import estimate_tokens
from app.context.summarizer import Summarizer
from app.database.models import Message

SYSTEM_INSTRUCTIONS = (
    "Anda adalah asisten AI yang membantu pengguna melalui Telegram. "
    "Gunakan bahasa yang jelas dan ringkas. Jawablah dalam bahasa yang sama "
    "dengan pertanyaan pengguna (umumnya Bahasa Indonesia)."
)


class ContextManager:
    def __init__(
        self,
        max_tokens: int = None,
        recent_limit: int = None,
        summarizer: Optional[Summarizer] = None,
    ):
        self.max_tokens = max_tokens or settings.context_max_tokens
        self.recent_limit = recent_limit or settings.recent_message_limit
        self.summarizer = summarizer or Summarizer()

    def build_context(
        self,
        messages: List[Message],
        current_message: str,
        summary: Optional[str] = None,
        memory: str = "",
    ) -> ContextSnapshot:
        snapshot = ContextSnapshot(
            system=SYSTEM_INSTRUCTIONS,
            summary=summary or "",
            memory=memory,
            current_message=current_message,
        )

        # Current message token requirement
        current_tokens = estimate_tokens(current_message)
        # Reserve a little for system
        system_tokens = estimate_tokens(snapshot.system)
        budget = max(0, self.max_tokens - system_tokens - current_tokens)

        # Summary and memory first (priority 2 & 3)
        summary_tokens = estimate_tokens(snapshot.summary)
        memory_tokens = estimate_tokens(snapshot.memory)
        used = summary_tokens + memory_tokens
        remaining_for_messages = max(0, budget - used)

        recent_inputs = messages[-self.recent_limit :]
        selected: List[ContextMessage] = []
        # Walk from most recent backwards to favor the latest context
        for msg in reversed(recent_inputs):
            m = ContextMessage(role=msg.role, content=msg.content)
            tok = estimate_tokens(m.content)
            if remaining_for_messages - tok < 0:
                break
            selected.append(m)
            remaining_for_messages -= tok

        snapshot.recent_messages = list(reversed(selected))
        return snapshot
