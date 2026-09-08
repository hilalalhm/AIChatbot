from tests.conftest import (
    FailingProvider,
    ProviderUnavailableError,
    SuccessfulProvider,
    make_context,
    make_router,
)


async def test_fallback_one_provider():
    router = make_router(
        [
            FailingProvider(ProviderUnavailableError("down")),
            SuccessfulProvider("B response"),
        ],
        order=["fail", "success"],
    )
    result = await router.chat(make_context(), request_id="req_1")
    assert result.response is not None
    assert result.response.content == "B response"
    assert result.response.provider == "success"


async def test_multiple_fallback():
    router = make_router(
        [
            FailingProvider(ProviderUnavailableError("A down")),
            FailingProvider(ProviderUnavailableError("B down")),
            SuccessfulProvider("C response"),
        ],
        order=["fail", "fail2", "success"],
    )
    result = await router.chat(make_context(), request_id="req_1")
    assert result.response is not None
    assert result.response.content == "C response"
    assert result.response.provider == "success"


async def test_all_providers_failed():
    router = make_router(
        [
            FailingProvider(ProviderUnavailableError("A down"), name="fail"),
            FailingProvider(ProviderUnavailableError("B down"), name="fail2"),
            FailingProvider(ProviderUnavailableError("C down"), name="fail3"),
        ],
        order=["fail", "fail2", "fail3"],
    )
    router.max_retries = 0
    result = await router.chat(make_context(), request_id="req_1")
    assert result.response is None
    assert result.all_failed is True
    assert len(result.attempts) == 3


async def test_all_providers_failed_with_retries():
    """With max_retries=1, retriable failures consume retries per provider."""
    router = make_router(
        [
            FailingProvider(ProviderUnavailableError("A down"), name="fail"),
            FailingProvider(ProviderUnavailableError("B down"), name="fail2"),
            FailingProvider(ProviderUnavailableError("C down"), name="fail3"),
        ],
        order=["fail", "fail2", "fail3"],
    )
    router.max_retries = 1
    result = await router.chat(make_context(), request_id="req_1")
    assert result.response is None
    assert result.all_failed is True
    assert len(result.attempts) == 6  # 2 attempts per provider (1 retry)


async def test_context_preservation_during_fallback():
    seen = []
    router = make_router(
        [
            FailingProvider(ProviderUnavailableError("down")),
            SuccessfulProvider("B ok", seen=seen),
        ],
        order=["fail", "success"],
    )
    context = make_context()
    result = await router.chat(context, request_id="req_1")
    assert result.response is not None
    # The successful provider must have received the exact same message list
    assert len(seen) == 1
    provider_messages = seen[0]
    assert provider_messages == context.to_provider_messages()
