"""
FastAPI health check and monitoring service.

Exposes HTTP endpoints for Render/cloud health checks
and basic bot status monitoring.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings

# Bot startup time reference (set externally by main.py)
_start_time: float = time.time()

app = FastAPI(
    title="Music Bot Health Check",
    version="1.0.0",
    description="Telegram Voice Chat Music Bot — Health & Status API",
)


@app.get("/", response_class=JSONResponse, tags=["Health"])
async def root() -> dict[str, str]:
    """Root endpoint — confirms the service is running."""
    return {"status": "ok"}


@app.get("/health", response_class=JSONResponse, tags=["Health"])
async def health_check() -> dict[str, Any]:
    """
    Render health check endpoint.

    Returns HTTP 200 with service health information.
    Render uses this to determine if the service is healthy.
    """
    try:
        from app.player.queue import queue_manager
        from app.player.voice.engine import voice_engine

        if queue_manager:
            try:
                active_chats = await queue_manager.active_chats()
            except Exception:
                active_chats = []
        else:
            active_chats = []

        uptime = int(time.time() - _start_time)
        hours, remainder = divmod(uptime, 3600)
        mins, secs = divmod(remainder, 60)

        # Check configuration status
        is_configured = bool(
            settings.api_id and settings.api_hash and settings.bot_token and settings.session_string
        )

        return {
            "status": "healthy" if is_configured else "configuration_required",
            "uptime_seconds": uptime,
            "uptime_human": f"{hours}h {mins}m {secs}s",
            "active_voice_chats": len(active_chats),
            "engine_active": voice_engine is not None,
            "database": settings.database_url.split("://")[0] if settings.database_url else "unknown",
            "configured": is_configured,
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "error": str(exc),
            "configured": False,
        }


@app.get("/ping", tags=["Health"])
async def ping() -> dict[str, str]:
    """Simple ping — used for uptime monitoring."""
    return {"pong": "true"}


def set_start_time(t: float) -> None:
    """Set the bot start time for uptime calculation."""
    global _start_time
    _start_time = t
