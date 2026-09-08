from __future__ import annotations

import os
from typing import List, Optional

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.ai.base import AIProvider, AIResponse, ChatMessage
from app.ai.exceptions import (
    ProviderAuthenticationError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.ai.health import ProviderHistory
from app.ai.registry import ProviderRegistry
from app.ai.router import AIRouter
from app.context.manager import ContextSnapshot
from app.database.database import Base
from app.reliability.circuit_breaker import CircuitBreakerRegistry

# Ensure fresh DB location for tests
_TEST_DB = "sqlite+aiosqlite:///./data/test.db"

_session_factory: Optional[async_sessionmaker] = None


def get_test_session_factory() -> async_sessionmaker:
    """Standalone test session factory bound to a fresh in-memory DB.

    Returns an async_sessionmaker; use session_scope_factory() with it for
    commit/rollback behaviour.
    """
    global _session_factory
    if _session_factory is None:
        engine = create_async_engine(_TEST_DB)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        _session_factory = factory
    return _session_factory


def session_scope_factory(factory: async_sessionmaker):
    import contextlib

    @contextlib.asynccontextmanager
    async def _scope():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _scope


@pytest_asyncio.fixture
async def db_engine():
    import os

    os.makedirs("data", exist_ok=True)
    engine = create_async_engine(_TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    factory = sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    yield factory


# ---------- Fake providers ----------

class FailingProvider(AIProvider):
    name = "fail"

    def __init__(self, error: Exception, name: Optional[str] = None):
        self.error = error
        if name is not None:
            self.name = name

    async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
        raise self.error


class SuccessfulProvider(AIProvider):
    name = "success"

    def __init__(self, content: str = "OK from provider", seen: Optional[list] = None):
        self.content = content
        self.seen = seen if seen is not None else []

    async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
        if self.seen is not None:
            self.seen.append(list(messages))
        return AIResponse(
            content=self.content,
            provider=self.name,
            model="test-model",
            request_id=request_id,
            attempt_id=attempt_id,
            latency_ms=10,
        )


class TimeoutProvider(AIProvider):
    name = "timeout"

    async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
        raise ProviderTimeoutError("timeout")


class RateLimitedProvider(AIProvider):
    name = "rate"

    async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
        raise ProviderRateLimitError("rate limit")


class AuthenticationErrorProvider(AIProvider):
    name = "auth"

    async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
        raise ProviderAuthenticationError("auth failed")


class UnavailableProvider(AIProvider):
    name = "down"

    async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
        raise ProviderUnavailableError("down")


def register_provider(registry: ProviderRegistry, provider: AIProvider, order: Optional[List[str]] = None):
    registry.register(provider)
    return registry


def make_context() -> ContextSnapshot:
    return ContextSnapshot(
        system="You are a test assistant.",
        summary="User is building a Telegram AI app. Backend uses FastAPI.",
        memory="Deployment target is Jagoan Hosting.",
        recent_messages=[
            type("M", (), {"role": "assistant", "content": "Use FastAPI as backend."})(),
        ],
        current_message="Now build the database structure.",
    )


def make_router(providers: List[AIProvider], order: Optional[List[str]] = None) -> AIRouter:
    reg = ProviderRegistry(order=[], register_defaults=False)
    for p in providers:
        reg.register(p)
    if order:
        reg._order = [n for n in order if n in reg.by_name()]
    cb = CircuitBreakerRegistry()
    hist = ProviderHistory()
    return AIRouter(registry=reg, circuit_breakers=cb, history=hist, max_retries=1)
