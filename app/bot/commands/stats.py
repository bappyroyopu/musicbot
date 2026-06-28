"""
/ping and /stats command handlers.
"""

from __future__ import annotations

import time
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message

from app.bot.filters import not_banned
from app.database import get_session
from app.database.routers import groups as group_crud
from app.database.routers import users as user_crud
from app.player.queue import queue_manager

# Bot start time for uptime calculation
_BOT_START_TIME = time.time()


@Client.on_message(filters.command("ping") & not_banned)
async def ping_command(client: Client, message: Message) -> None:
    """Measure round-trip latency."""
    sent_at = time.monotonic()
    sent = await message.reply("🏓 Pinging...")
    latency = (time.monotonic() - sent_at) * 1000
    await sent.edit(f"🏓 <b>Pong!</b> <code>{latency:.0f}ms</code>")


@Client.on_message(filters.command("stats") & not_banned)
async def stats_command(client: Client, message: Message) -> None:
    """Show bot statistics."""
    async with get_session() as session:
        total_users = await user_crud.get_total_users(session)
        total_groups = await group_crud.get_total_groups(session)

    active_chats = await queue_manager.active_chats()
    uptime_secs = int(time.time() - _BOT_START_TIME)
    hours, remainder = divmod(uptime_secs, 3600)
    mins, secs = divmod(remainder, 60)
    uptime_str = f"{hours}h {mins}m {secs}s"

    await message.reply(
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total users: <b>{total_users:,}</b>\n"
        f"🏠 Total groups: <b>{total_groups:,}</b>\n"
        f"🎵 Active voice chats: <b>{len(active_chats)}</b>\n"
        f"⏱ Uptime: <b>{uptime_str}</b>\n"
        f"📅 Started: <b>{datetime.utcfromtimestamp(_BOT_START_TIME).strftime('%Y-%m-%d %H:%M UTC')}</b>"
    )
