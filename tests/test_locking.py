import asyncio
import time

import pytest

from app.reliability.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry
from app.reliability.lock import ConversationLock
from app.reliability.rate_limiter import SlidingWindowRateLimiter


def test_circuit_breaker_states():
    cb = CircuitBreaker("test", failure_threshold=3, cooldown_seconds=1000)
    assert cb.is_available() is True
    cb.record_failure()
    cb.record_failure()
    assert cb.is_available() is True  # threshold not reached (3 failures needed)
    cb.record_failure()
    assert cb.state == cb.OPEN
    assert cb.is_available() is False


def test_circuit_breaker_recovers_after_success():
    cb = CircuitBreaker("test", failure_threshold=2, cooldown_seconds=60)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == cb.OPEN
    # Simulate cooldown passing -> half open
    cb._opened_at = time.monotonic() - 1000  # opened long ago
    assert cb.state == cb.HALF_OPEN
    assert cb.is_available() is True
    cb.record_success()
    assert cb.state == cb.HEALTHY


def test_circuit_breaker_registry():
    reg = CircuitBreakerRegistry()
    reg.record_failure("p1")
    reg.record_failure("p1")
    reg.record_failure("p1")
    assert reg.get("p1").state == "open"
    assert "p1" in reg.states()


@pytest.mark.asyncio
async def test_conversation_lock_serializes():
    lock = ConversationLock()
    result = []
    async def worker(i):
        lk = await lock.acquire(1)
        try:
            await asyncio.sleep(0.01)
            result.append(i)
        finally:
            await lock.release(1, lk)
    await asyncio.gather(*(worker(i) for i in range(5)))
    assert result == sorted(result)


def test_rate_limiter_blocks_excess():
    rl = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    assert rl.allow(1) is True
    assert rl.allow(1) is True
    assert rl.allow(1) is True
    assert rl.allow(1) is False  # exceeded
    # Different user unaffected
    assert rl.allow(2) is True


def test_rate_limiter_window_reset():
    import time
    rl = SlidingWindowRateLimiter(max_requests=2, window_seconds=0)
    assert rl.allow(1) is True
    # window_seconds=0 means everything expires immediately
    assert rl.allow(1) is True
    assert rl.allow(1) is True
