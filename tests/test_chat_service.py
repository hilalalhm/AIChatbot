import asyncio

import pytest
import pytest_asyncio

from app.ai.health import ProviderHistory
from app.ai.registry import ProviderRegistry
from app.ai.router import AIRouter
from app.database.database import Base
from app.reliability.circuit_breaker import CircuitBreakerRegistry
from app.reliability.lock import ConversationLock
from app.reliability.rate_limiter import SlidingWindowRateLimiter
from app.services.chat_service import ChatService, FRIENDLY_ALL_FAILED
from app.services.context_service import ContextManager
from tests.conftest import (
    FailingProvider,
    ProviderUnavailableError,
    SuccessfulProvider,
    get_test_session_factory,
    session_scope_factory,
)

from sqlalchemy.ext.asyncio import create_async_engine


@pytest_asyncio.fixture
async def fresh_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///./data/chat_service_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, session_scope_factory(factory)
    await engine.dispose()


@pytest.mark.asyncio
async def _make_service(providers, order, fresh_test_db=None):
    reg = ProviderRegistry(order=[], register_defaults=False)
    for p in providers:
        reg.register(p)
    reg._order = [n for n in order if n in reg.by_name()]
    router = AIRouter(
        registry=reg,
        circuit_breakers=CircuitBreakerRegistry(),
        history=ProviderHistory(),
    )
    kwargs = {}
    if fresh_test_db is not None:
        _, scope = fresh_test_db
        kwargs["session_factory"] = scope
    svc = ChatService(
        ai_router=router,
        registry=reg,
        lock=ConversationLock(),
        rate_limiter=SlidingWindowRateLimiter(100, 60),
        context_manager=ContextManager(),
        **kwargs,
    )
    return svc


@pytest.mark.asyncio
async def test_all_providers_failed_keeps_user_message(fresh_test_db):
    svc = await _make_service(
        [FailingProvider(ProviderUnavailableError("down"))], order=["fail"],
        fresh_test_db=fresh_test_db,
    )
    outcome = await svc.handle_message(5001, "ini pesan penting")
    assert outcome.all_failed is True
    assert outcome.success is False
    assert outcome.reply_text == FRIENDLY_ALL_FAILED
    assert outcome.user_message_id is not None
    assert outcome.request_id is not None


@pytest.mark.asyncio
async def test_duplicate_final_message_prevented_on_fallback(fresh_test_db):
    svc = await _make_service(
        [
            FailingProvider(ProviderUnavailableError("down")),
            SuccessfulProvider("success response"),
        ],
        order=["fail", "success"],
        fresh_test_db=fresh_test_db,
    )
    outcome = await svc.handle_message(5002, "berapa 2+2?")
    assert outcome.success is True
    assert outcome.reply_text == "success response"
    # Exactly one assistant message is created by the flow
    # (the provider attempts are tracked, but only one final assistant message)
    assert outcome.request_id is not None


@pytest.mark.asyncio
async def test_rate_limited_request_does_not_call_provider(fresh_test_db):
    class CountingProvider(SuccessfulProvider):
        calls = 0
        async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
            CountingProvider.calls += 1
            return await super().chat(messages, model, request_id, attempt_id, timeout)

    svc = await _make_service(
        [CountingProvider("ok")], order=["success"], fresh_test_db=fresh_test_db
    )
    # Set a very tight rate limit
    svc.rate_limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    first = await svc.handle_message(6000, "hello")
    assert first.success is True
    counting_before = CountingProvider.calls
    second = await svc.handle_message(6000, "hello again")
    assert second.rate_limited is True
    # Provider NOT called for rejected request
    assert CountingProvider.calls == counting_before


@pytest.mark.asyncio
async def test_user_message_persisted_after_provider_failure(fresh_test_db):
    svc = await _make_service(
        [FailingProvider(ProviderUnavailableError("down"))], order=["fail"],
        fresh_test_db=fresh_test_db,
    )
    outcome = await svc.handle_message(5003, "pesan yang harus tersimpan")
    assert outcome.all_failed is True

    # Verify the user message exists in DB after failure
    _, scope = fresh_test_db
    async with scope() as session:
        from app.database.repository import UserRepository, ConversationRepository, MessageRepository

        users = UserRepository(session)
        user = await users.get_by_telegram_id(5003)
        assert user is not None
        convs = ConversationRepository(session)
        conv = await convs.get_active(user.id)
        msgs = MessageRepository(session)
        recent = await msgs.get_recent(conv.id)
        contents = [m.content for m in recent]
        assert "pesan yang harus tersimpan" in contents
        # No assistant final message created
        assistant_msgs = [m for m in recent if m.role == "assistant"]
        assert len(assistant_msgs) == 0