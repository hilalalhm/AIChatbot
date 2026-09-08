import pytest

from app.database.database import Base
from app.database.models import Conversation, Message, ProviderAttempt, User
from app.database.repository import (
    ConversationRepository,
    MessageRepository,
    ProviderAttemptRepository,
    UserRepository,
)
from app.utils.ids import new_attempt_id


@pytest.mark.asyncio
async def test_user_crud(session_factory):
    async with session_factory() as session:
        users = UserRepository(session)
        user = await users.get_or_create(111, "alice", "Alice")
        assert user.telegram_id == 111
        # Same telegram id returns same user (no duplicates)
        user2 = await users.get_or_create(111, "alice", "Alice")
        assert user2.id == user.id
        await session.commit()


@pytest.mark.asyncio
async def test_conversation_ownership(session_factory):
    async with session_factory() as session:
        users = UserRepository(session)
        u1 = await users.get_or_create(1, "u1", "U1")
        u2 = await users.get_or_create(2, "u2", "U2")
        convs = ConversationRepository(session)
        c1 = await convs.create(u1.id, title="A")
        c2 = await convs.create(u1.id, title="B")
        c3 = await convs.create(u2.id, title="C")
        await session.commit()

        # u1 owns c1 and c2, not c3
        assert (await convs.get_owned(c1.id, u1.id)) is not None
        assert (await convs.get_owned(c2.id, u1.id)) is not None
        assert (await convs.get_owned(c3.id, u1.id)) is None

        # u2 owns c3, not c1
        assert (await convs.get_owned(c3.id, u2.id)) is not None
        assert (await convs.get_owned(c1.id, u2.id)) is None

        listed = await convs.list_for_user(u1.id)
        assert {c.id for c in listed} == {c1.id, c2.id}


@pytest.mark.asyncio
async def test_message_and_attempts(session_factory):
    async with session_factory() as session:
        users = UserRepository(session)
        user = await users.get_or_create(7, "u7", "U7")
        convs = ConversationRepository(session)
        conv = await convs.create(user.id)
        msgs = MessageRepository(session)
        m = await msgs.add(conv.id, "user", "hello", status="completed", request_id="req_1")
        await msgs.set_status(m.id, "processing")
        await msgs.set_status(m.id, "completed")
        await session.commit()

        recent = await msgs.get_recent(conv.id)
        assert len(recent) == 1
        assert recent[0].content == "hello"


@pytest.mark.asyncio
async def test_persistence_across_sessions(session_factory):
    conv_id = None
    async with session_factory() as session:
        users = UserRepository(session)
        user = await users.get_or_create(99, "persist", "Persist")
        convs = ConversationRepository(session)
        conv = await convs.create(user.id)
        conv_id = conv.id
        msgs = MessageRepository(session)
        await msgs.add(conv.id, "user", "persist me", request_id="req_x")
        await session.commit()

    # New session (simulating restart) - data must survive
    async with session_factory() as session:
        conv = await session.get(Conversation, conv_id)
        assert conv is not None
        msgs = MessageRepository(session)
        recent = await msgs.get_recent(conv_id)
        assert len(recent) == 1
        assert recent[0].content == "persist me"
