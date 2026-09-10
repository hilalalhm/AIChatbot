from __future__ import annotations

import hmac

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request

from app.config import settings
from app.deps import Container, get_container

router = APIRouter(tags=["telegram"])


async def _validate_secret(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> None:
    if not settings.telegram_webhook_secret:
        return
    provided = x_telegram_bot_api_secret_token or ""
    expected = settings.telegram_webhook_secret
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")


@router.post("/telegram/webhook", dependencies=[Depends(_validate_secret)])
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    container: Container = Depends(get_container),
) -> dict:
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    background_tasks.add_task(container.handlers.handle_update, payload)
    return {"ok": True}
