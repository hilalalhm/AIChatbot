from __future__ import annotations

from app.ai.providers.openai_compatible import OpenAICompatibleProvider as _Base
from app.config import settings


class OpenCodeProvider(_Base):
    def __init__(self):
        super().__init__(
            name="opencode",
            base_url=settings.opencode_base_url or "",
            api_key=settings.opencode_api_key,
            model=settings.opencode_model,
            timeout=settings.ai_timeout_seconds,
        )
