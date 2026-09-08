from __future__ import annotations

from app.ai.providers.openai_compatible import OpenAICompatibleProvider as _Base
from app.config import settings


class KimiProvider(_Base):
    def __init__(self):
        super().__init__(
            name="kimi",
            base_url=settings.kimi_base_url,
            api_key=settings.kimi_api_key,
            model=settings.kimi_model,
            timeout=settings.ai_timeout_seconds,
        )
