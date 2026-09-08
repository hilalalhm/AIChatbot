from __future__ import annotations

import asyncio
from typing import Dict


class ConversationLock:
    """In-process per-conversation mutex.

    Designed as an abstraction so it can be replaced with a distributed lock
    (e.g. Redis) later without changing callers.
    """

    def __init__(self):
        self._locks: Dict[int, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    def _get_lock(self, conversation_id: int) -> asyncio.Lock:
        lock = self._locks.get(conversation_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[conversation_id] = lock
        return lock

    async def acquire(self, conversation_id: int) -> asyncio.Lock:
        async with self._guard:
            lock = self._get_lock(conversation_id)
            await lock.acquire()
            return lock

    async def release(self, conversation_id: int, lock: asyncio.Lock) -> None:
        try:
            lock.release()
        except RuntimeError:
            # Already released
            pass
