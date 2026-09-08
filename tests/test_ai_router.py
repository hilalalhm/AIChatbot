from tests.conftest import (
    FailingProvider,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SuccessfulProvider,
    TimeoutProvider,
    UnavailableProvider,
    make_context,
    make_router,
)


async def test_provider_success():
    router = make_router([SuccessfulProvider("hello")], order=["success"])
    result = await router.chat(make_context(), request_id="req_1")
    assert result.response is not None
    assert result.response.content == "hello"
    assert result.response.provider == "success"
    assert result.all_failed is False


async def test_authentication_provider_skipped_not_retried():
    router = make_router(
        [FailingProvider(ProviderAuthenticationError("auth"))],
        order=["auth"],
    )
    result = await router.chat(make_context(), request_id="req_1")
    assert result.response is None
    assert result.all_failed is True
    # Should not retry an auth failure
    assert result.attempts[0].status == "failed"
    assert result.attempts[0].error_type == "authentication"


async def test_timeout_marked_unknown():
    router = make_router(
        [TimeoutProvider(), SuccessfulProvider("recovered")],
        order=["timeout", "success"],
    )
    result = await router.chat(make_context(), request_id="req_1")
    assert result.response is not None
    assert result.response.provider == "success"
    assert result.attempts[0].status == "unknown"
    assert result.attempts[0].error_type == "timeout"


async def test_timeout_not_retried_same_provider():
    """Ambiguous timeouts must NOT be retried against the same provider."""
    calls = {"count": 0}
    class TrackingTimeoutProvider(TimeoutProvider):
        async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
            calls["count"] += 1
            raise ProviderTimeoutError("timeout")

    router = make_router(
        [TrackingTimeoutProvider(), SuccessfulProvider("ok")],
        order=["timeout", "success"],
    )
    # max_retries = 2 would normally allow retries; timeout must skip them
    router.max_retries = 2
    result = await router.chat(make_context(), request_id="req_1")
    assert calls["count"] == 1  # no same-provider retry for ambiguity
    assert result.response.provider == "success"


async def test_retriable_error_retries_same_provider():
    """Unavailable (5xx) is retriable; retries should happen on the same provider."""
    calls = {"count": 0}
    class FlakyProvider(UnavailableProvider):
        name = "flaky"
        async def chat(self, messages, model=None, request_id=None, attempt_id=None, timeout=None):
            calls["count"] += 1
            if calls["count"] < 2:
                raise ProviderUnavailableError("down")
            from app.ai.base import AIResponse
            return AIResponse(
                content="recovered", provider=self.name,
                model="m", request_id=request_id, attempt_id=attempt_id,
            )

    router = make_router([FlakyProvider()], order=["flaky"])
    router.max_retries = 2
    result = await router.chat(make_context(), request_id="req_1")
    assert result.response is not None
    assert result.response.provider == "flaky"
    assert calls["count"] == 2
    assert len(result.attempts) == 2
