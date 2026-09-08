from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from app.ai.base import AIResponse, ChatMessage
from app.ai.router import AIRouter
from app.ai.registry import ProviderRegistry
from app.config import settings
from app.context.memory import estimate_tokens
from app.context.summarizer import Summarizer, SYSTEM_SUMMARY_PROMPT
from app.database.database import session_scope
from app.database.repository import (
    ProviderAttemptRepository,
)
from app.reliability.lock import ConversationLock
from app.reliability.rate_limiter import SlidingWindowRateLimiter
from app.services.context_service import ContextManager, SYSTEM_INSTRUCTIONS
from app.context.manager import ContextMessage, ContextSnapshot
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.utils.ids import new_request_id

logger = logging.getLogger(__name__)

FRIENDLY_ALL_FAILED = (
    "Maaf, semua AI provider sedang tidak tersedia.\n"
    "Pesan Anda sudah tersimpan. Silakan coba lagi nanti."
)
RATE_LIMIT_MESSAGE = "Terlalu banyak permintaan. Silakan coba lagi sebentar lagi."
TOO_LONG_MESSAGE = "Pesan terlalu panjang. Silakan pecah menjadi beberapa pesan."

MAX_INPUT_LENGTH = 4000


@dataclass
class ChatOutcome:
    reply_text: Optional[str] = None
    success: bool = False
    all_failed: bool = False
    rate_limited: bool = False
    user_message_id: Optional[int] = None
    request_id: Optional[str] = None


class ChatService:
    def __init__(
        self,
        ai_router: AIRouter,
        registry: ProviderRegistry,
        lock: Optional[ConversationLock] = None,
        rate_limiter: Optional[SlidingWindowRateLimiter] = None,
        context_manager: Optional[ContextManager] = None,
        summarizer: Optional[Summarizer] = None,
        max_retries: int = None,
        session_factory: Optional[Callable] = None,
    ):
        self.ai_router = ai_router
        self.registry = registry
        self.lock = lock or ConversationLock()
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter(
            settings.rate_limit_requests, settings.rate_limit_window_seconds
        )
        self.context_manager = context_manager or ContextManager()
        self.summarizer = summarizer or Summarizer()
        self.max_retries = max_retries if max_retries is not None else settings.ai_max_retries
        self.session_factory = session_factory or session_scope

    async def handle_message(
        self,
        telegram_id: int,
        text: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> ChatOutcome:
        if len(text) > MAX_INPUT_LENGTH:
            return ChatOutcome(
                reply_text=TOO_LONG_MESSAGE,
                success=False,
                rate_limited=False,
            )

        if not self.rate_limiter.allow(telegram_id):
            return ChatOutcome(
                reply_text=RATE_LIMIT_MESSAGE,
                success=False,
                rate_limited=True,
            )

        request_id = new_request_id()

        async with self.session_factory() as session:
            conv_svc = ConversationService(session)
            user = await conv_svc.get_or_create_user(
                telegram_id, username, first_name
            )
            conversation = await conv_svc.get_active(user.id)

            # Conversation lock to serialize per-conversation processing
            cl = await self.lock.acquire(conversation.id)
            try:
                msg_svc = MessageService(session)
                # Recover stale PROCESSING records left by a previous crash:
                # mark them UNKNOWN so they are never regenerated as duplicates.
                await msg_svc.messages.mark_stale_processing(conversation.id)
                user_message = await msg_svc.add(
                    conversation.id,
                    "user",
                    text,
                    status="completed",
                    request_id=request_id,
                )

                # Build context from persisted history
                recent = await msg_svc.get_recent(
                    conversation.id, limit=settings.recent_message_limit
                )
                messages_for_context = [m for m in recent if m.id != user_message.id]
                summary = conversation.summary or ""

                context = self.context_manager.build_context(
                    messages=messages_for_context,
                    current_message=text,
                    summary=summary,
                    memory="",
                )

                router_result = await self.ai_router.chat(
                    context=context,
                    request_id=request_id,
                    provider_order=self.registry.ordered_names(),
                )

                if router_result.response is not None:
                    resp: AIResponse = router_result.response
                    assistant_message = await msg_svc.add(
                        conversation.id,
                        "assistant",
                        resp.content,
                        status="completed",
                        provider=resp.provider,
                        model=resp.model,
                        request_id=request_id,
                        attempt_id=resp.attempt_id,
                    )
                    assistant_id = assistant_message.id
                    await self._save_attempts(
                        session,
                        router_result,
                        request_id,
                        assistant_id,
                    )

                    # Best-effort automatic summarization for large conversations
                    await self._maybe_summarize(
                        session,
                        conversation,
                        msg_svc,
                    )

                    return ChatOutcome(
                        reply_text=resp.content,
                        success=True,
                        all_failed=False,
                        user_message_id=user_message.id,
                        request_id=request_id,
                    )
                else:
                    # All providers failed
                    await self._save_attempts(
                        session, router_result, request_id, None
                    )
                    return ChatOutcome(
                        reply_text=FRIENDLY_ALL_FAILED,
                        success=False,
                        all_failed=True,
                        user_message_id=user_message.id,
                        request_id=request_id,
                    )
            finally:
                await self.lock.release(conversation.id, cl)

    async def _maybe_summarize(self, session, conversation, msg_svc: MessageService) -> None:
        """Summarize older messages when the conversation transcript gets large.

        Best-effort: failures are logged and never fail the user request.
        """
        recent = await msg_svc.get_recent(
            conversation.id, limit=settings.recent_message_limit
        )
        transcript = "\n".join(f"{m.role}: {m.content}" for m in recent)
        if not self.summarizer.should_summarize(
            transcript, settings.summary_trigger_tokens
        ):
            return

        try:
            messages = [
                ChatMessage(role="system", content=SYSTEM_SUMMARY_PROMPT),
                ChatMessage(role="user", content=transcript),
            ]
            result = await self.ai_router.chat(
                context=_summary_context(messages),
                request_id=None,
                provider_order=self.registry.ordered_names(),
            )
            if result.response is not None:
                conversation.summary = result.response.content.strip()
                await session.flush()
        except Exception:  # noqa: BLE001
            logger.exception("Automatic summarization failed; skipping.")

    async def _save_attempts(
        self,
        session,
        router_result,
        request_id: str,
        assistant_message_id: Optional[int],
    ) -> None:
        repo = ProviderAttemptRepository(session)
        for attempt in router_result.attempts:
            if not attempt.attempt_id:
                continue
            await repo.add(
                provider=attempt.provider,
                attempt_id=attempt.attempt_id,
                request_id=request_id,
                message_id=assistant_message_id,
                model=attempt.model,
                status="success" if attempt.status == "success" else attempt.status,
                error_type=attempt.error_type,
                latency_ms=attempt.latency_ms,
            )


def _summary_context(messages: List[ChatMessage]) -> ContextSnapshot:
    """Build a minimal context snapshot that feeds the raw messages as-is."""
    return ContextSnapshot(
        system=SYSTEM_INSTRUCTIONS,
        summary="",
        memory="",
        recent_messages=[
            ContextMessage(role=m.role, content=m.content) for m in messages
        ],
        current_message="",
    )
