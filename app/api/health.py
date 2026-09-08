from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import Container, get_container
from app.database.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(container: Container = Depends(get_container)) -> dict:
    body: dict = {"status": "ok"}

    # Database check
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_ok = False
    body["database"] = "ok" if db_ok else "error"

    # Providers
    providers = {}
    for name in container.registry.ordered_names():
        provider = container.registry.get(name)
        configured = bool(getattr(provider, "api_key", None))
        if not configured:
            providers[name] = "disabled"
            continue
        state = container.circuit_breakers.get(name).state
        providers[name] = state
    body["providers"] = providers

    # Telegram
    body["telegram"] = "ok" if container.bot.configured else "not_configured"

    if not db_ok:
        body["status"] = "degraded"

    return body
