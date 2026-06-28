"""
/settings command — view and modify per-group settings.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.bot.filters import admin_only, group_only, not_banned
from app.database import get_session
from app.database.routers import groups as group_crud
from app.player.queue import queue_manager
from app.utils.keyboards import settings_keyboard


@Client.on_message(filters.command("settings") & group_only & not_banned & admin_only)
async def settings_command(client: Client, message: Message) -> None:
    """Display and modify group settings panel."""
    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)

    async with get_session() as session:
        group = await group_crud.get_group(session, chat_id)

    if group is None:
        await message.reply("❌ Group not registered. Send /start first.")
        return

    text = (
        f"⚙️ <b>Settings for {message.chat.title}</b>\n\n"
        f"🔁 Loop: <b>{'ON' if group.loop else 'OFF'}</b>\n"
        f"🔀 Shuffle: <b>{'ON' if group.shuffle else 'OFF'}</b>\n"
        f"🚪 Auto-leave: <b>{'ON' if group.auto_leave else 'OFF'}</b>\n"
        f"🔊 Volume: <b>{group.volume}%</b>\n"
        f"📋 Max queue: <b>{group.max_queue or 'Unlimited'}</b>"
    )

    await message.reply(
        text,
        reply_markup=settings_keyboard(
            chat_id=chat_id,
            loop=group.loop,
            shuffle=group.shuffle,
            auto_leave=group.auto_leave,
            volume=group.volume,
        ),
    )
