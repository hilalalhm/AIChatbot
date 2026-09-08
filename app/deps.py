from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.ai.health import ProviderHistory
from app.ai.registry import ProviderRegistry, build_registry
from app.ai.router import AIRouter
from app.config import settings
from app.reliability.circuit_breaker import CircuitBreakerRegistry
from app.reliability.lock import ConversationLock
from app.reliability.rate_limiter import SlidingWindowRateLimiter
from app.services.chat_service import ChatService
from app.services.context_service import ContextManager
from app.telegram.bot import TelegramBot
from app.telegram.handlers import TelegramHandlers

logger = logging.getLogger(__name__)


@dataclass
class Container:
    registry: ProviderRegistry = None
    circuit_breakers: CircuitBreakerRegistry = None
    history: ProviderHistory = None
    lock: ConversationLock = None
    rate_limiter: SlidingWindowRateLimiter = None
    context_manager: ContextManager = None
    ai_router: AIRouter = None
    chat_service: ChatService = None
    bot: TelegramBot = None
    handlers: TelegramHandlers = None

    def __post_init__(self):
        self.registry = build_registry(settings.provider_order)
        self.circuit_breakers = CircuitBreakerRegistry()
        self.history = ProviderHistory()
        self.lock = ConversationLock()
        self.rate_limiter = SlidingWindowRateLimiter(
            settings.rate_limit_requests, settings.rate_limit_window_seconds
        )
        self.context_manager = ContextManager()
        self.ai_router = AIRouter(
            registry=self.registry,
            circuit_breakers=self.circuit_breakers,
            history=self.history,
            max_retries=settings.ai_max_retries,
            timeout=settings.ai_timeout_seconds,
        )
        self.chat_service = ChatService(
            ai_router=self.ai_router,
            registry=self.registry,
            lock=self.lock,
            rate_limiter=self.rate_limiter,
            context_manager=self.context_manager,
        )
        self.bot = TelegramBot()
        self.handlers = TelegramHandlers(
            chat_service=self.chat_service,
            registry=self.registry,
            circuit_breakers=self.circuit_breakers,
            history=self.history,
            bot=self.bot,
        )


_container: Optional[Container] = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    global _container
    _container = None
