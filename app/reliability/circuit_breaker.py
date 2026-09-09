from __future__ import annotations

import threading
import time
from typing import Dict

from app.config import settings


class CircuitBreaker:
    """Per-provider circuit breaker with HEALTHY/DEGRADED/OPEN/HALF_OPEN states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        name: str,
        failure_threshold: int = None,
        cooldown_seconds: int = None,
    ):
        self.name = name
        self.failure_threshold = (
            failure_threshold if failure_threshold is not None else settings.circuit_breaker_failure_threshold
        )
        self.cooldown_seconds = (
            cooldown_seconds if cooldown_seconds is not None else settings.circuit_breaker_cooldown_seconds
        )
        self._state = self.HEALTHY
        self._failure_count = 0
        self._opened_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN:
                if time.monotonic() - self._opened_at >= self.cooldown_seconds:
                    self._state = self.HALF_OPEN
            return self._state

    def is_available(self) -> bool:
        return self.state not in (self.OPEN,)

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = self.HEALTHY

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = self.OPEN
                self._opened_at = time.monotonic()

    def record_unknown(self) -> None:
        """An ambiguous outcome. Count it but do not necessarily open."""
        with self._lock:
            # Unknown results don't trip the breaker immediately but keep it mild.
            self._failure_count = max(0, self._failure_count - 1)


class CircuitBreakerRegistry:
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name)
        return self._breakers[name]

    def record_success(self, name: str) -> None:
        self.get(name).record_success()

    def record_failure(self, name: str) -> None:
        self.get(name).record_failure()

    def states(self) -> Dict[str, str]:
        return {name: breaker.state for name, breaker in self._breakers.items()}
