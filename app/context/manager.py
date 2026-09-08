from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.context.memory import estimate_tokens


@dataclass
class ContextMessage:
    role: str
    content: str


@dataclass
class ContextSnapshot:
    system: str = ""
    summary: str = ""
    memory: str = ""
    recent_messages: List[ContextMessage] = field(default_factory=list)
    current_message: str = ""

    def to_provider_messages(self) -> List[dict]:
        messages: List[dict] = []
        if self.summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"Ringkasan percakapan:\n{self.summary}",
                }
            )
        if self.memory:
            messages.append(
                {
                    "role": "system",
                    "content": f"Informasi penting:\n{self.memory}",
                }
            )
        for m in self.recent_messages:
            messages.append({"role": m.role, "content": m.content})
        if self.current_message:
            messages.append({"role": "user", "content": self.current_message})
        return messages

    def estimated_tokens(self) -> int:
        total = estimate_tokens(self.current_message)
        total += estimate_tokens(self.summary) + estimate_tokens(self.memory)
        for m in self.recent_messages:
            total += estimate_tokens(m.content)
        return total
