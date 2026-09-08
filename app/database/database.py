from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def _async_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        # Convert sqlite:///./path to sqlite+aiosqlite:///./path
        if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+aiomysql://", 1)
    if url.startswith("mariadb://"):
        return url.replace("mariadb://", "mysql+aiomysql://", 1)
    # PostgreSQL async driver for future use
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _ensure_dir(url: str) -> None:
    if url.startswith("sqlite") and "///" in url:
        path = url.split("///", 1)[1]
        if "?" in path:
            path = path.split("?", 1)[0]
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)


async_url = _async_url(settings.database_url)
_ensure_dir(settings.database_url)

engine = create_async_engine(async_url, echo=settings.debug)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    from app.database import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
