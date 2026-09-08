from __future__ import annotations

from typing import List, Optional

from app.database.models import Message
from app.database.repository import MessageRepository
from sqlalchemy.ext.asyncio import AsyncSession


class MessageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.messages = MessageRepository(session)

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
        return await self.messages.add(
            conversation_id,
            role,
            content,
            status=status,
            provider=provider,
            model=model,
            request_id=request_id,
            attempt_id=attempt_id,
        )

    async def get_recent(
        self, conversation_id: int, limit: int = 30
    ) -> List[Message]:
        return await self.messages.get_recent(conversation_id, limit)

    async def set_status(self, message_id: int, status: str) -> None:
        await self.messages.set_status(message_id, status)

    async def update_message(
        self,
        message_id: int,
        *,
        content: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Message]:
        return await self.messages.update_message(
            message_id,
            content=content,
            provider=provider,
            model=model,
            status=status,
        )
