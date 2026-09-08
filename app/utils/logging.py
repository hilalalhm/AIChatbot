from __future__ import annotations

import logging
import sys
from typing import Optional

from app.config import settings

_LOGGER_PREFIX = "telegram_ai"


def get_logger(name: str = "app") -> logging.Logger:
    full_name = f"{_LOGGER_PREFIX}.{name}" if name != "app" else _LOGGER_PREFIX
    logger = logging.getLogger(full_name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | "
                "%(message)s"
            )
        )
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
        logger.propagate = False
    return logger
