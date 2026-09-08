from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def new_attempt_id() -> str:
    return f"attempt_{secrets.token_hex(6)}"


def utcnow() -> datetime:
    """Naive UTC now (keeps DB DateTime columns naive-aware compatible)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
