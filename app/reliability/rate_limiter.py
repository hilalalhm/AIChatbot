from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict


class SlidingWindowRateLimiter:
    """Sliding-window per-user rate limiter running in process memory."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[int, Deque[float]] = {}

    def _bucket(self, user_id: int) -> Deque[float]:
        bucket = self._buckets.get(user_id)
        if bucket is None:
            bucket = deque()
            self._buckets[user_id] = bucket
        return bucket

    def allow(self, user_id: int) -> bool:
        now = time.monotonic()
        bucket = self._bucket(user_id)
        # Drop expired timestamps
        while bucket and now - bucket[0] >= self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True

    def reset(self, user_id: int) -> None:
        self._buckets.pop(user_id, None)
