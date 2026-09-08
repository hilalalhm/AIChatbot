from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class Usage:
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


@dataclass
class AIResponse:
    content: str
    provider: str
    model: Optional[str] = None
    request_id: Optional[str] = None
    attempt_id: Optional[str] = None
    usage: Optional[Usage] = None
    latency_ms: Optional[int] = None
    status: str = "success"


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        request_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> AIResponse:
        """Call the provider with a list of messages and return a unified response."""
        ...
