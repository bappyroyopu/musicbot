"""
Error handler — catches unhandled Pyrogram exceptions.

Handles:
  - FloodWait (auto-sleeps)
  - ChatAdminRequired
  - UserNotParticipant
  - General errors (logged, user notified)
"""

from __future__ import annotations

from pyrogram import Client
from pyrogram.errors import (
    ChatAdminRequired,
    FloodWait,
    UserNotParticipant,
    MessageNotModified,
    PeerIdInvalid,
)
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from loguru import logger
import asyncio


async def error_handler(client: Client, message: Message, error: Exception) -> None:
    """
    Global error handler for all message handlers.

    Logs the error and sends a user-friendly notification.
    """
    chat_id = message.chat.id if message.chat else "?"
    user_id = message.from_user.id if message.from_user else "?"
    text = message.text or ""

    if isinstance(error, FloodWait):
        wait = error.value
        logger.warning(
            "FloodWait for {}s in chat_id={}", wait, chat_id
        )
        await asyncio.sleep(wait)
        return

    if isinstance(error, ChatAdminRequired):
        logger.warning("ChatAdminRequired in chat_id={}", chat_id)
        try:
            await message.reply(
                "❌ <b>Admin permissions required.</b>\n\n"
                "Please make me an admin with permission to manage voice chats."
            )
        except Exception:
            pass
        return

    if isinstance(error, UserNotParticipant):
        logger.warning("UserNotParticipant in chat_id={}", chat_id)
        return

    if isinstance(error, MessageNotModified):
        # Silently ignore — message content didn't change
        return

    if isinstance(error, PeerIdInvalid):
        logger.warning("PeerIdInvalid chat_id={}", chat_id)
        return

    # General error
    logger.exception(
        "Unhandled error in chat_id={} user_id={} text={!r}",
        chat_id,
        user_id,
        text[:100],
    )
    try:
        await message.reply(
            "❌ An unexpected error occurred. Please try again.\n"
            "<i>The error has been logged.</i>"
        )
    except Exception:
        pass
