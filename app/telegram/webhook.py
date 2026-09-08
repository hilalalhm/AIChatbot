from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.config import settings
from app.deps import Container, get_container

logger = logging.getLogger(__name__)

router = APIRouter(tags=["telegram"])


async def _validate_secret(request: Request, x_telegram_bot_api_secret: str = Header(None)) -> None:
    if not settings.telegram_webhook_secret:
        return
    provided = x_telegram_bot_api_secret or ""
    expected = settings.telegram_webhook_secret
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")


@router.post("/telegram/webhook", dependencies=[Depends(_validate_secret)])
async def telegram_webhook(
    request: Request,
    container: Container = Depends(get_container),
) -> dict:
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        await container.handlers.handle_update(payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Webhook handler error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal handler error")

    return {"ok": True}
