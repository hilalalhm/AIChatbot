from functools import lru_cache
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    debug: bool = True

    database_url: str = "sqlite:///./data/app.db"

    telegram_bot_token: Optional[str] = None
    telegram_webhook_url: Optional[str] = None
    telegram_webhook_secret: Optional[str] = None

    ai_provider_order: str = "gemini,qwen,kimi,opencode"

    ai_timeout_seconds: float = 60.0
    ai_max_retries: int = 1

    context_max_tokens: int = 12000
    recent_message_limit: int = 30
    summary_trigger_tokens: int = 8000

    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60

    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_cooldown_seconds: int = 60

    log_level: str = "INFO"

    # Provider configs (OpenAI-compatible endpoints)
    kimi_api_key: Optional[str] = None
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-8k"

    qwen_api_key: Optional[str] = None
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-turbo"

    opencode_api_key: Optional[str] = None
    opencode_base_url: Optional[str] = None
    opencode_model: Optional[str] = None

    gemini_api_key: Optional[str] = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_model: str = "gemini-2.5-flash"

    @property
    def provider_order(self) -> List[str]:
        return [p.strip() for p in self.ai_provider_order.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
