from __future__ import annotations

from app.ai.providers.openai_compatible import OpenAICompatibleProvider as _Base
from app.config import settings


class GeminiProvider(_Base):
    def __init__(self):
        super().__init__(
            name="gemini",
            base_url=settings.gemini_base_url,
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout=settings.ai_timeout_seconds,
        )