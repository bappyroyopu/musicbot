"""
/start command handler.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.bot.filters import group_only, not_banned
from app.config import settings


@Client.on_message(filters.command("start") & filters.private)
async def start_private(client: Client, message: Message) -> None:
    """Handle /start in private chat — show welcome message."""
    user = message.from_user
    first_name = user.first_name if user else "there"

    text = (
        f"👋 Hello, <b>{first_name}</b>!\n\n"
        f"🎵 I'm a <b>Telegram Voice Chat Music Bot</b>.\n\n"
        f"<b>How to use me:</b>\n"
        f"1. Add me to a group\n"
        f"2. Grant me admin permissions\n"
        f"3. Start a Voice Chat in your group\n"
        f"4. Type <code>/play Believer</code> or paste a YouTube link\n\n"
        f"<b>Commands:</b>\n"
        f"/help — Full command list\n"
        f"/play &lt;song/URL&gt; — Play music\n"
        f"/queue — View queue\n\n"
        f"📢 Need help? Join: @{settings.support_chat or 'your_support_chat'}"
    )
    await message.reply(text)


@Client.on_message(filters.command("start") & group_only & not_banned)
async def start_group(client: Client, message: Message) -> None:
    """Handle /start in group chat."""
    await message.reply(
        "👋 <b>Music Bot is active!</b>\n\n"
        "Use <code>/play &lt;song name or YouTube URL&gt;</code> to start playing music.\n"
        "Type /help for all commands."
    )
