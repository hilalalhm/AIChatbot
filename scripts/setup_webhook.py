"""Set the Telegram webhook URL for the bot.

Usage:
    python scripts/setup_webhook.py

Reads TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL, TELEGRAM_WEBHOOK_SECRET
from the environment / .env file.
"""
from __future__ import annotations

import asyncio

from app.config import settings
from app.telegram.bot import TelegramBot
from app.utils.logging import get_logger

logger = get_logger("setup_webhook")


async def main() -> None:
    bot = TelegramBot()
    if not settings.telegram_webhook_url:
        logger.error("TELEGRAM_WEBHOOK_URL is not set. Aborting.")
        return 1

    result = await bot.set_webhook(
        settings.telegram_webhook_url,
        secret=settings.telegram_webhook_secret,
        max_connections=10,
    )
    logger.info("setWebhook result: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
