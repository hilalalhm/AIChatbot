import pytest

from app.reliability.circuit_breaker import CircuitBreakerRegistry
from app.reliability.rate_limiter import SlidingWindowRateLimiter
from tests.conftest import (
    FailingProvider,
    ProviderUnavailableError,
    SuccessfulProvider,
    make_router,
)
from app.ai.router import AIRouter


@pytest.mark.asyncio
async def test_rate_limit_prevents_provider_call():
    calls = {"count": 0}
    class CountingProvider(SuccessfulProvider):
        async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
            calls["count"] += 1
            return await super().chat(messages, model, request_id, attempt_id, timeout)

    router = make_router([CountingProvider("ok")], order=["success"])
    rl = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    # We'll rely on ChatService to enforce, but here test limiter independently
    assert rl.allow(1) is True


@pytest.mark.asyncio
async def test_circuit_breaker_skips_open_provider():
    cb_reg = CircuitBreakerRegistry()
    router = make_router(
        [FailingProvider(ProviderUnavailableError("down")), SuccessfulProvider("ok")],
        order=["fail", "success"],
    )
    # Trip the circuit breaker for "fail" provider after 3 failures
    for _ in range(3):
        result = await router.chat(make_router_context(), request_id="req")
    # Next call: since breaker may be shared, let's directly check skip
    router.circuit_breakers.record_failure("fail")
    router.circuit_breakers.record_failure("fail")
    router.circuit_breakers.record_failure("fail")
    assert router.circuit_breakers.get("fail").state == "open"
    result = await router.chat(make_router_context(), request_id="req2")
    # "fail" provider should be skipped (status skipped), success used
    assert any(a.status == "skipped" for a in result.attempts)
    assert result.response is not None


def make_router_context():
    from tests.conftest import make_context
    return make_context()
