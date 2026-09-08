from __future__ import annotations

from typing import List, Optional

from app.database.models import Conversation
from app.database.repository import ConversationRepository, UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.conversations = ConversationRepository(session)

    async def get_or_create_user(
        self, telegram_id: int, username: Optional[str] = None, first_name: Optional[str] = None
    ):
        return await self.users.get_or_create(telegram_id, username, first_name)

    async def get_active(self, user_id: int) -> Conversation:
        return await self.conversations.get_active(user_id)

    async def create(self, user_id: int, title: str = "New Chat") -> Conversation:
        return await self.conversations.create(user_id, title)

    async def list_for_user(self, user_id: int) -> List[Conversation]:
        return await self.conversations.list_for_user(user_id)

    async def get_owned(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        return await self.conversations.get_owned(conversation_id, user_id)

    async def reset_context(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        return await self.conversations.reset_context(conversation_id, user_id)
