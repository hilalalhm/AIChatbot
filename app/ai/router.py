from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.ai.base import AIProvider, AIResponse
from app.ai.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from app.ai.health import ProviderHistory
from app.ai.registry import ProviderRegistry
from app.context.manager import ContextSnapshot
from app.reliability.circuit_breaker import CircuitBreakerRegistry


@dataclass
class AttemptResult:
    provider: str
    model: Optional[str]
    attempt_id: str
    status: str  # success | failed | unknown
    error_type: Optional[str] = None
    latency_ms: Optional[int] = None


@dataclass
class RouterResult:
    response: Optional[AIResponse] = None
    attempts: List[AttemptResult] = field(default_factory=list)
    all_failed: bool = False

    @property
    def last_status(self) -> str:
        if self.response:
            return "success"
        return self.all_failed and "failed" or "failed"


class AIRouter:
    def __init__(
        self,
        registry: ProviderRegistry,
        circuit_breakers: Optional[CircuitBreakerRegistry] = None,
        history: Optional[ProviderHistory] = None,
        max_retries: int = 1,
        timeout: float = 60.0,
    ):
        self.registry = registry
        self.circuit_breakers = circuit_breakers or CircuitBreakerRegistry()
        self.history = history or ProviderHistory()
        self.max_retries = max_retries
        self.timeout = timeout

    def _is_retriable(self, error: ProviderError) -> bool:
        return bool(getattr(error, "retriable", False))

    def _is_retryable_overall(self, error: ProviderError) -> bool:
        # Timeouts produce UNKNOWN outcomes; retrying same provider may duplicate.
        # We only retry the same provider for rate-limit / availability / network
        # where no ambiguity is involved. Timeouts move to next provider instead.
        if isinstance(error, ProviderTimeoutError):
            return False
        return self._is_retriable(error)

    async def chat(
        self,
        context: ContextSnapshot,
        request_id: Optional[str] = None,
        provider_order: Optional[List[str]] = None,
    ) -> RouterResult:
        result = RouterResult()
        if provider_order is None:
            provider_order = self.registry.ordered_names()

        for provider_name in provider_order:
            provider = self.registry.get(provider_name)
            if provider is None:
                continue
            breaker = self.circuit_breakers.get(provider_name)
            if not breaker.is_available():
                result.attempts.append(
                    AttemptResult(
                        provider=provider_name,
                        model=None,
                        attempt_id="",
                        status="skipped",
                        error_type="circuit_open",
                    )
                )
                continue

            done, result = await self._try_provider(
                provider,
                provider_name,
                context,
                request_id,
                result,
            )
            if done:
                break

        result.all_failed = result.response is None
        return result

    async def _try_provider(
        self,
        provider: AIProvider,
        provider_name: str,
        context: ContextSnapshot,
        request_id: Optional[str],
        result: RouterResult,
    ) -> tuple:
        """Attempt one provider, with bounded retries for unambiguous errors.

        Returns (done, result). done=True means a final response was produced
        (whether success or all-failed-for-this-provider) and iteration must stop.
        """
        retries_left = max(0, self.max_retries)
        attempt_index = 0

        while True:
            attempt_index += 1
            attempt_id = _gen_attempt_id()
            latency = int(time.monotonic() * 1000)
            try:
                response = await provider.chat(
                    messages=context.to_provider_messages(),
                    model=getattr(provider, "model", None),
                    request_id=request_id,
                    attempt_id=attempt_id,
                    timeout=self.timeout,
                )
                self._record_success(provider_name, response.latency_ms or 0)
                result.response = response
                result.attempts.append(
                    AttemptResult(
                        provider=provider_name,
                        model=response.model,
                        attempt_id=attempt_id,
                        status="success",
                        latency_ms=response.latency_ms,
                    )
                )
                return True, result
            except ProviderError as exc:
                el = int((time.monotonic() * 1000) - latency)
                status = getattr(exc, "status", "failed")
                self._record_failure(provider_name, status, exc.error_type)
                result.attempts.append(
                    AttemptResult(
                        provider=provider_name,
                        model=getattr(provider, "model", None),
                        attempt_id=attempt_id,
                        status=status,
                        error_type=exc.error_type,
                        latency_ms=el,
                    )
                )
                if self._is_retryable_overall(exc) and retries_left > 0:
                    retries_left -= 1
                    await asyncio.sleep(self._backoff(attempt_index))
                    continue
                # Timeouts are ambiguous: do not retry the same provider
                # (the request may have been accepted). Move to next provider.
                await self._maybe_sleep_before_next(exc)
                return False, result
            except Exception as exc:  # noqa: BLE001
                el = int((time.monotonic() * 1000) - latency)
                self._record_failure(provider_name, "failed", "internal")
                result.attempts.append(
                    AttemptResult(
                        provider=provider_name,
                        model=getattr(provider, "model", None),
                        attempt_id=attempt_id,
                        status="failed",
                        error_type="internal",
                        latency_ms=el,
                    )
                )
                await self._maybe_sleep_before_next(None)
                return False, result

    def _backoff(self, attempt_index: int) -> float:
        return min(2.0, 0.5 * (2 ** (attempt_index - 1)))

    def _record_success(self, provider: str, latency_ms: int) -> None:
        self.circuit_breakers.record_success(provider)
        self.history.record_success(provider, latency_ms)

    def _record_failure(self, provider: str, status: str, error_type: str) -> None:
        self.history.record_failure(provider, error_type)
        if status == "unknown":
            self.circuit_breakers.get(provider).record_unknown()
        else:
            self.circuit_breakers.record_failure(provider)

    async def _maybe_sleep_before_next(self, exc: Optional[Exception]) -> None:
        if isinstance(exc, ProviderRateLimitError):
            await asyncio.sleep(0.5)


def _gen_attempt_id() -> str:
    from app.utils.ids import new_attempt_id

    return new_attempt_id()
