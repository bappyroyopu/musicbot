"""
Custom Pyrogram filters for the music bot.

Provides reusable filters for admin checks, voice chat state,
group-only restrictions, and owner-only commands.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.config import settings


# ---------------------------------------------------------------------------
# Group-only filter
# ---------------------------------------------------------------------------
async def _is_group(_, __, message: Message) -> bool:
    """True if the message was sent in a group or supergroup."""
    return message.chat and message.chat.type.name in ("GROUP", "SUPERGROUP")


group_only = filters.create(_is_group, name="GroupOnly")


# ---------------------------------------------------------------------------
# Admin filter (Telegram chat admin or bot admin or owner)
# ---------------------------------------------------------------------------
async def _is_admin(client: Client, _, message: Message) -> bool:
    """
    True if the sender is:
    - The bot owner (from settings.owner_id)
    - A Telegram chat administrator
    """
    if message.from_user is None:
        return False

    user_id = message.from_user.id

    # Owner always has access
    if settings.owner_id and user_id == settings.owner_id:
        return True

    # Check Telegram admin status
    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        return member.status.name in ("ADMINISTRATOR", "OWNER")
    except Exception:
        return False


admin_only = filters.create(_is_admin, name="AdminOnly")


# ---------------------------------------------------------------------------
# Owner-only filter
# ---------------------------------------------------------------------------
async def _is_owner(_, __, message: Message) -> bool:
    """True only for the bot owner."""
    if message.from_user is None:
        return False
    return settings.owner_id != 0 and message.from_user.id == settings.owner_id


owner_only = filters.create(_is_owner, name="OwnerOnly")


# ---------------------------------------------------------------------------
# Not banned filter
# ---------------------------------------------------------------------------
async def _not_banned(_, __, message: Message) -> bool:
    """
    True if the user is not banned.
    The actual DB check is performed in the group_register middleware.
    This filter reads the pre-computed flag injected into message.
    """
    return not getattr(message, "_is_banned", False)


not_banned = filters.create(_not_banned, name="NotBanned")
