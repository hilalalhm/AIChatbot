from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Conversation,
    Message,
    ProviderAttempt,
    User,
)
from app.utils.ids import utcnow


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def new_request_id() -> str:
    return new_id("req")


def new_attempt_id() -> str:
    return new_id("attempt")


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return await self.session.get(User, user_id)

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user is not None:
            return user
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, conversation_id: int) -> Optional[Conversation]:
        return await self.session.get(Conversation, conversation_id)

    async def get_owned(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, title: str = "New Chat") -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def list_for_user(self, user_id: int) -> Sequence[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return result.scalars().all()

    async def get_active(self, user_id: int) -> Conversation:
        conversations = await self.list_for_user(user_id)
        if conversations:
            return conversations[0]
        return await self.create(user_id)

    async def reset_context(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        conv = await self.get_owned(conversation_id, user_id)
        if conv is not None:
            conv.summary = None
            await self.session.flush()
        return conv


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        conversation_id: int,
        role: str,
        content: str,
        status: str = "completed",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        request_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            status=status,
            provider=provider,
            model=model,
            request_id=request_id,
            attempt_id=attempt_id,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get(self, message_id: int) -> Optional[Message]:
        return await self.session.get(Message, message_id)

    async def set_status(self, message_id: int, status: str) -> None:
        message = await self.get(message_id)
        if message is not None:
            message.status = status
            await self.session.flush()

    async def get_recent(
        self,
        conversation_id: int,
        limit: int = 30,
        roles: Optional[tuple] = None,
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
        )
        if roles:
            stmt = stmt.where(Message.role.in_(roles))
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def update_message(
        self,
        message_id: int,
        *,
        content: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Message]:
        message = await self.get(message_id)
        if message is None:
            return None
        if content is not None:
            message.content = content
        if provider is not None:
            message.provider = provider
        if model is not None:
            message.model = model
        if status is not None:
            message.status = status
        message.updated_at = utcnow()
        await self.session.flush()
        return message

    async def mark_stale_processing(self, conversation_id: int) -> int:
        """Mark any PROCESSING messages older than 30min as UNKNOWN."""
        from sqlalchemy import update as sa_update

        result = await self.session.execute(
            sa_update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.status == "processing",
            )
            .values(status="unknown", updated_at=utcnow())
        )
        return result.rowcount or 0


class ProviderAttemptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        provider: str,
        attempt_id: str,
        request_id: Optional[str] = None,
        message_id: Optional[int] = None,
        model: Optional[str] = None,
        status: str = "pending",
        error_type: Optional[str] = None,
        latency_ms: Optional[int] = None,
    ) -> ProviderAttempt:
        attempt = ProviderAttempt(
            provider=provider,
            attempt_id=attempt_id,
            request_id=request_id,
            message_id=message_id,
            model=model,
            status=status,
            error_type=error_type,
            latency_ms=latency_ms,
        )
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def complete(
        self, attempt_id: str, status: str, error_type: Optional[str] = None
    ) -> Optional[ProviderAttempt]:
        attempt = await self.get_by_attempt_id(attempt_id)
        if attempt is None:
            return None
        attempt.status = status
        attempt.error_type = error_type
        attempt.completed_at = utcnow()
        await self.session.flush()
        return attempt

    async def get_by_attempt_id(self, attempt_id: str) -> Optional[ProviderAttempt]:
        result = await self.session.execute(
            select(ProviderAttempt).where(ProviderAttempt.attempt_id == attempt_id)
        )
        return result.scalar_one_or_none()

    async def count_success_for_request(
        self, request_id: str, message_id: Optional[int] = None
    ) -> int:
        stmt = select(ProviderAttempt).where(
            ProviderAttempt.request_id == request_id,
            ProviderAttempt.status == "success",
        )
        if message_id is not None:
            stmt = select(ProviderAttempt).where(
                ProviderAttempt.request_id == request_id,
                ProviderAttempt.message_id == message_id,
                ProviderAttempt.status == "success",
            )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
