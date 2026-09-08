from __future__ import annotations

import logging
from typing import Optional

from app.ai.health import ProviderHistory
from app.ai.router import AIRouter
from app.ai.registry import ProviderRegistry
from app.config import settings
from app.database.database import session_scope
from app.reliability.circuit_breaker import CircuitBreakerRegistry
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)

WELCOME = (
    "Halo! Saya asisten AI berbasis Telegram.\n\n"
    "Gunakan perintah:\n"
    "/start - mulai\n"
    "/new - percakapan baru\n"
    "/reset - reset konteks\n"
    "/history - riwayat percakapan\n"
    "/models - daftar provider\n"
    "/status - status sistem\n"
    "/help - bantuan\n\n"
    "Atau langsung kirim pesan untuk mulai chat."
)

HELP = (
    "Bantuan:\n\n"
    "/start - mulai dan buat percakapan default\n"
    "/new - buat percakapan baru\n"
    "/reset - reset konteks percakapan aktif\n"
    "/history - tampilkan daftar percakapan\n"
    "/models - tampilkan AI provider yang dikonfigurasi\n"
    "/status - status sistem dan kesehatan provider\n"
)


class TelegramHandlers:
    def __init__(
        self,
        chat_service: ChatService,
        registry: ProviderRegistry,
        circuit_breakers: CircuitBreakerRegistry,
        history: ProviderHistory,
        bot: TelegramBot,
    ):
        self.chat_service = chat_service
        self.registry = registry
        self.circuit_breakers = circuit_breakers
        self.history = history
        self.bot = bot

    async def handle_update(self, update: dict) -> Optional[str]:
        parsed = self.bot.parse_update(update)
        if parsed is None:
            return None
        text = parsed["text"].strip()
        chat_id = parsed["chat_id"]
        telegram_id = parsed["telegram_id"]
        username = parsed["username"]
        first_name = parsed["first_name"]

        if text.startswith("/"):
            reply = await self._handle_command(
                text, telegram_id, chat_id, username, first_name
            )
            if reply:
                await self.bot.send_message(chat_id, reply)
            return reply

        outcome = await self.chat_service.handle_message(
            telegram_id, text, username, first_name
        )
        if outcome.reply_text:
            await self.bot.send_message(chat_id, outcome.reply_text)
        return outcome.reply_text

    async def _handle_command(
        self,
        command: str,
        telegram_id: int,
        chat_id: int,
        username: Optional[str],
        first_name: Optional[str],
    ) -> Optional[str]:
        cmd = command.lower().split("@")[0].split()[0]

        if cmd == "/start":
            async with session_scope() as session:
                svc = ConversationService(session)
                user = await svc.get_or_create_user(telegram_id, username, first_name)
                await svc.get_active(user.id)
            return WELCOME

        if cmd == "/help":
            return HELP

        if cmd == "/new":
            async with session_scope() as session:
                svc = ConversationService(session)
                user = await svc.get_or_create_user(telegram_id, username, first_name)
                conv = await svc.create(user.id, title="New Chat")
            return f"Percakapan baru dibuat (ID {conv.id})."

        if cmd == "/reset":
            async with session_scope() as session:
                svc = ConversationService(session)
                user = await svc.get_or_create_user(telegram_id, username, first_name)
                active = await svc.get_active(user.id)
                await svc.reset_context(active.id, user.id)
            return "Konteks percakapan aktif telah di-reset."

        if cmd == "/history":
            async with session_scope() as session:
                svc = ConversationService(session)
                user = await svc.get_or_create_user(telegram_id, username, first_name)
                convs = await svc.list_for_user(user.id)
            if not convs:
                return "Belum ada percakapan."
            lines = []
            for i, c in enumerate(convs, 1):
                title = c.title if c.title else "(tanpa judul)"
                lines.append(f"{i}. {title} (ID {c.id})")
            return "Percakapan Anda:\n" + "\n".join(lines[:20])

        if cmd == "/models":
            return self._format_models()

        if cmd == "/status":
            return self._format_status()

        if cmd == "/id":
            return f"ID Anda: {telegram_id}"

        return "Perintah tidak dikenal. Ketik /help untuk bantuan."

    def _format_models(self) -> str:
        lines = ["AI Providers", "----------------"]
        for name in self.registry.ordered_names():
            provider = self.registry.get(name)
            configured = bool(getattr(provider, "api_key", None))
            status = "Available" if configured else "Disabled"
            lines.append(f"{name.capitalize()}: {status}")
        return "\n".join(lines)

    def _format_status(self) -> str:
        lines = ["Bot: Online", "Database: OK", ""]
        lines.append("AI Providers:")
        for name in self.registry.ordered_names():
            provider = self.registry.get(name)
            configured = bool(getattr(provider, "api_key", None))
            if not configured:
                lines.append(f"  {name}: Disabled")
                continue
            circuit_state = self.circuit_breakers.get(name).state
            state_label = {
                "healthy": "Healthy",
                "degraded": "Degraded",
                "open": "Open",
                "half_open": "Half-Open",
            }.get(circuit_state, circuit_state)
            lines.append(f"  {name}: {state_label}")
        return "\n".join(lines)
