from __future__ import annotations

from app.ai.providers.openai_compatible import OpenAICompatibleProvider as _Base
from app.config import settings


class QwenProvider(_Base):
    def __init__(self):
        super().__init__(
            name="qwen",
            base_url=settings.qwen_base_url,
            api_key=settings.qwen_api_key,
            model=settings.qwen_model,
            timeout=settings.ai_timeout_seconds,
        )
