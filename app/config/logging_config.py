"""
Logging configuration for the bot.

Uses Loguru for structured, rotating logs with separate files
for bot events, player events, errors, and downloads.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger

from app.config import settings


class InterceptHandler(logging.Handler):
    """
    Intercept standard library logging and redirect to Loguru.

    This ensures that SQLAlchemy, Pyrogram, and other libraries
    that use stdlib logging are captured by Loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """
    Configure Loguru with multiple sinks:

    - stdout (colored, human-readable)
    - logs/bot.log (all bot events, rotating)
    - logs/player.log (player-specific events)
    - logs/errors.log (WARNING and above only)
    - logs/downloads.log (download-specific events)
    """
    logs_path = settings.logs_path
    logs_path.mkdir(parents=True, exist_ok=True)

    log_level = settings.log_level

    # Remove default handler
    logger.remove()

    # --- Stdout sink (colored) ---
    logger.add(
        sys.stdout,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
    )

    # --- Main bot log ---
    logger.add(
        logs_path / "bot.log",
        level=log_level,
        rotation="50 MB",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        enqueue=True,
    )

    # --- Error log ---
    logger.add(
        logs_path / "errors.log",
        level="WARNING",
        rotation="20 MB",
        retention="60 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    # --- Player log ---
    logger.add(
        logs_path / "player.log",
        level="DEBUG",
        rotation="20 MB",
        retention="14 days",
        compression="gz",
        filter=lambda record: "player" in record["name"],
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        enqueue=True,
    )

    # --- Download log ---
    logger.add(
        logs_path / "downloads.log",
        level="DEBUG",
        rotation="20 MB",
        retention="14 days",
        compression="gz",
        filter=lambda record: "downloader" in record["name"],
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        enqueue=True,
    )

    # Intercept stdlib logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for lib in ["pyrogram", "sqlalchemy", "uvicorn", "fastapi", "pytgcalls"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    logger.info("Logging configured. Level={} Logs={}", log_level, logs_path)
