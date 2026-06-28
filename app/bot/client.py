"""
Pyrogram client setup.

Creates both the bot client and the user/assistant client (for PyTgCalls).
The assistant client uses a StringSession to avoid storing session files.
"""

from __future__ import annotations

from pyrogram import Client
from pyrogram.enums import ParseMode

from app.config import settings

# Safe fallback values to prevent Pyrogram from crashing during module import
api_id = settings.api_id or 123456
api_hash = settings.api_hash or "0123456789abcdef0123456789abcdef"
bot_token = settings.bot_token or "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
session_string = settings.session_string or "BQAAAAA..."  # Minimal dummy format string

# ---------------------------------------------------------------------------
# Bot client — used for sending messages, handling commands
# ---------------------------------------------------------------------------
bot = Client(
    name="musicbot",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token,
    parse_mode=ParseMode.HTML,
    sleep_threshold=30,
    max_concurrent_transmissions=5,
    workers=8,
)

# ---------------------------------------------------------------------------
# Assistant (user) client — required by PyTgCalls to join voice chats
# ---------------------------------------------------------------------------
assistant = Client(
    name="assistant",
    api_id=api_id,
    api_hash=api_hash,
    session_string=session_string,
    parse_mode=ParseMode.HTML,
    sleep_threshold=30,
    workers=4,
)
