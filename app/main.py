from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import settings
from app.database.database import init_db
from app.telegram.webhook import router as telegram_router
from app.utils.logging import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized. Environment=%s", settings.app_env)
    yield


app = FastAPI(
    title="Telegram AI Chat",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(telegram_router)


@app.get("/")
async def root() -> dict:
    return {"service": "Telegram AI Chat", "status": "running"}
