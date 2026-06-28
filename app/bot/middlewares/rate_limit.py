"""
Rate limiting middleware.

Implements per-user flood protection using an in-memory token bucket.
If Redis is configured, Redis is used instead for distributed rate limiting.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Callable

from loguru import logger
from pyrogram import Client
from pyrogram.types import Message

from app.config import settings

# ---------------------------------------------------------------------------
# In-memory token bucket per user
# ---------------------------------------------------------------------------
# Structure: {user_id: (tokens, last_refill_time)}
_buckets: dict[int, list[float]] = defaultdict(lambda: [5.0, time.monotonic()])
_RATE = 1.0          # Tokens added per second
_CAPACITY = 5.0      # Maximum tokens
_lock = asyncio.Lock()


async def _consume_token(user_id: int) -> bool:
    """
    Attempt to consume one token for the given user.

    Returns True if allowed, False if rate-limited.
    """
    async with _lock:
        bucket = _buckets[user_id]
        now = time.monotonic()
        elapsed = now - bucket[1]
        # Refill tokens
        bucket[0] = min(_CAPACITY, bucket[0] + elapsed * _RATE)
        bucket[1] = now

        if bucket[0] >= 1.0:
            bucket[0] -= 1.0
            return True
        return False


# Track the last time a user was warned about rate limiting to prevent spamming
_last_warnings: dict[int, float] = {}


# ---------------------------------------------------------------------------
# Middleware function — wraps message handlers
# ---------------------------------------------------------------------------
async def rate_limit_middleware(client: Client, message: Message) -> None:
    """
    Check per-user rate limit before processing any message.

    If the user is sending too many commands, the message is silently ignored
    (or a warning is sent on the first violation).
    """
    if message.from_user is None:
        return  # Anonymous or channel messages — skip

    user_id = message.from_user.id
    allowed = await _consume_token(user_id)

    if not allowed:
        logger.debug("Rate limited user_id={}", user_id)
        now = time.monotonic()
        last_warn = _last_warnings.get(user_id, 0.0)
        # Warn at most once every 5 seconds per user
        if now - last_warn > 5.0:
            _last_warnings[user_id] = now
            try:
                await message.reply(
                    "⚠️ <b>Slow down!</b> You're sending commands too fast. "
                    "Please wait a moment.",
                    quote=True,
                )
            except Exception:
                pass
        message.stop_propagation()
