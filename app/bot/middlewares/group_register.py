"""
Group registration middleware.

Automatically registers new groups and users in the database
the first time they interact with the bot.
"""

from __future__ import annotations

from loguru import logger
from pyrogram import Client
from pyrogram.types import Message

from app.database import get_session
from app.database.routers import groups as group_crud
from app.database.routers import users as user_crud


async def group_register_middleware(client: Client, message: Message) -> None:
    """
    Ensure the group and user are registered in the database.

    Runs on every incoming message before command handlers.
    Injects `_is_banned` flag onto the message object.
    """
    # Register / update user
    if message.from_user:
        user = message.from_user
        async with get_session() as session:
            db_user, created = await user_crud.get_or_create_user(
                session=session,
                tg_id=user.id,
                first_name=user.first_name or "Unknown",
                username=user.username,
                last_name=user.last_name,
                language_code=user.language_code,
            )
            if created:
                logger.info(
                    "New user registered: tg_id={} username={}",
                    user.id,
                    user.username,
                )
            # Inject ban status
            message._is_banned = db_user.is_banned  # type: ignore[attr-defined]

            if db_user.is_banned:
                message.stop_propagation()
                return

    # Register / update group
    if message.chat and message.chat.type.name in ("GROUP", "SUPERGROUP"):
        chat = message.chat
        async with get_session() as session:
            _, created = await group_crud.get_or_create_group(
                session=session,
                chat_id=chat.id,
                title=chat.title or "Unknown Group",
                username=chat.username,
            )
            if created:
                logger.info(
                    "New group registered: chat_id={} title={}",
                    chat.id,
                    chat.title,
                )
