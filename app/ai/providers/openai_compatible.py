from __future__ import annotations

import time
from typing import List, Optional

import httpx

from app.ai.base import AIProvider, AIResponse, ChatMessage
from app.ai.exceptions import (
    ProviderAuthenticationError,
    ProviderHTTPError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class OpenAICompatibleProvider(AIProvider):
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: Optional[str],
        model: Optional[str] = None,
        timeout: float = 60.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = client

    @property
    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def _endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        request_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> AIResponse:
        if not self.api_key:
            raise ProviderAuthenticationError(
                f"Provider '{self.name}' is not configured (missing API key)."
            )

        ff_model = model or self.model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": ff_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        url = self._endpoint()

        start = time.monotonic()
        try:
            resp = await self._http_client.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout or self.timeout,
            )
        except httpx.TimeoutException as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            raise _annotate(ProviderTimeoutError(
                f"Provider '{self.name}' timed out.", latency_ms
            ))
        except httpx.HTTPError as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            raise _annotate(ProviderNetworkError(
                f"Provider '{self.name}' network error: {exc}", latency_ms
            ))

        latency_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code == 401 or resp.status_code == 403:
            raise _annotate(ProviderAuthenticationError(
                f"Provider '{self.name}' authentication failed (HTTP {resp.status_code}).",
                latency_ms,
            ))
        if resp.status_code == 429:
            raise _annotate(ProviderRateLimitError(
                f"Provider '{self.name}' rate limited (HTTP 429).", latency_ms
            ))
        if resp.status_code == 408:
            raise _annotate(ProviderTimeoutError(
                f"Provider '{self.name}' timeout (HTTP 408).", latency_ms
            ))
        if resp.status_code >= 500:
            raise _annotate(ProviderUnavailableError(
                f"Provider '{self.name}' unavailable (HTTP {resp.status_code}).",
                latency_ms,
            ))
        if resp.status_code != 200:
            raise _annotate(ProviderHTTPError(
                resp.status_code,
                f"Provider '{self.name}' returned HTTP {resp.status_code}.",
                latency_ms,
            ))

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            returned_model = data.get("model") or ff_model
            usage_raw = data.get("usage")
            from app.ai.base import Usage

            usage = None
            if usage_raw:
                usage = Usage(
                    prompt_tokens=usage_raw.get("prompt_tokens"),
                    completion_tokens=usage_raw.get("completion_tokens"),
                    total_tokens=usage_raw.get("total_tokens"),
                )
        except (KeyError, IndexError, ValueError) as exc:
            raise _annotate(ProviderUnavailableError(
                f"Provider '{self.name}' returned unexpected payload: {exc}",
                latency_ms,
            ))

        return AIResponse(
            content=content,
            provider=self.name,
            model=returned_model,
            request_id=request_id,
            attempt_id=attempt_id,
            usage=usage,
            latency_ms=latency_ms,
            status="success",
        )


def _annotate(exc: Exception, latency_ms: int) -> Exception:
    setattr(exc, "latency_ms", latency_ms)
    return exc
