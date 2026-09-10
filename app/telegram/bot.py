from __future__ import annotations

import logging
import time
from typing import Callable, Optional

import httpx

from app.config import settings
from app.telegram.chunker import split_message

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramBot:
    def __init__(self, token: Optional[str] = None, client: Optional[httpx.AsyncClient] = None):
        self.token = token or settings.telegram_bot_token
        self._client = client or httpx.AsyncClient(timeout=30)

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def _url(self, method: str) -> str:
        return API_BASE.format(token=self.token, method=method)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
    ) -> bool:
        if not self.configured:
            logger.warning("Telegram bot not configured; skipping send.")
            return False
        chunks = split_message(text)
        ok = True
        for chunk in chunks:
            payload = {"chat_id": chat_id, "text": chunk}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            try:
                resp = await self._client.post(self._url("sendMessage"), json=payload)
                if resp.status_code != 200:
                    logger.warning(
                        "Telegram send failed chat=%s status=%s body=%s",
                        chat_id,
                        resp.status_code,
                        resp.text[:200],
                    )
                    ok = False
            except Exception as exc:  # noqa: BLE001
                logger.warning("Telegram send error: %s", exc)
                ok = False
        return ok

    def parse_update(self, payload: dict) -> Optional[dict]:
        """Extract message text + user info from a Telegram update, or None."""
        message = payload.get("message") or payload.get("edited_message")
        if not message:
            return None
        text = message.get("text") or message.get("caption")
        if not text:
            return None
        from_user = message.get("from") or {}
        chat = message.get("chat") or {}
        return {
            "chat_id": chat.get("id"),
            "telegram_id": from_user.get("id"),
            "username": from_user.get("username"),
            "first_name": from_user.get("first_name"),
            "text": text,
        }

    async def set_webhook(self, url: str, secret: Optional[str] = None, max_connections: Optional[int] = None) -> dict:
        if not self.configured:
            raise RuntimeError("Telegram bot token not configured.")
        payload: dict = {"url": url}
        if secret:
            payload["secret_token"] = secret
        if max_connections:
            payload["max_connections"] = max_connections
        resp = await self._client.post(self._url("setWebhook"), json=payload)
        return {"status": resp.status_code, "body": resp.json() if resp.status_code == 200 else resp.text}

    async def delete_webhook(self) -> dict:
        if not self.configured:
            raise RuntimeError("Telegram bot token not configured.")
        resp = await self._client.post(self._url("deleteWebhook"), json={})
        return {"status": resp.status_code}

    async def get_me(self) -> dict:
        if not self.configured:
            raise RuntimeError("Telegram bot token not configured.")
        resp = await self._client.post(self._url("getMe"))
        return resp.json()
