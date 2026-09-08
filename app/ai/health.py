from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ProviderState:
    status: str = "healthy"  # healthy | degraded | open | half_open
    failure_count: int = 0
    success_count: int = 0
    timeout_count: int = 0
    rate_limit_count: int = 0
    total_latency_ms: int = 0
    request_count: int = 0
    last_failure_at: Optional[float] = None
    opened_at: Optional[float] = None

    @property
    def average_latency_ms(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count


class ProviderHistory:
    def __init__(self):
        self._states: Dict[str, ProviderState] = {}

    def get(self, provider: str) -> ProviderState:
        state = self._states.get(provider)
        if state is None:
            state = ProviderState()
            self._states[provider] = state
        return state

    def record_success(self, provider: str, latency_ms: int = 0) -> None:
        state = self.get(provider)
        state.success_count += 1
        state.request_count += 1
        state.total_latency_ms += latency_ms
        state.status = "healthy"

    def record_failure(self, provider: str, error_type: str = None) -> None:
        state = self.get(provider)
        state.failure_count += 1
        state.request_count += 1
        state.last_failure_at = time.time()
        if error_type == "timeout":
            state.timeout_count += 1
        elif error_type == "rate_limit":
            state.rate_limit_count += 1

    def states(self) -> Dict[str, ProviderState]:
        return self._states
