"""
/play command handler — the main entry point for music playback.

Supports:
  /play <song name>        — YouTube search
  /play <YouTube URL>      — Direct URL
  /play <playlist URL>     — YouTube playlist
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.bot.filters import group_only, not_banned
from app.services.music_service import music_service
from app.utils.keyboards import player_controls
from app.utils.validators import is_youtube_playlist, is_url, sanitize_query
from app.utils.formatters import format_duration


@Client.on_message(
    filters.command("play") & group_only & not_banned
)
async def play_command(client: Client, message: Message) -> None:
    """
    Handle the /play command.

    Usage:
        /play Believer
        /play https://youtu.be/xxxxx
        /play https://youtube.com/playlist?list=xxxxx
    """
    if not message.from_user:
        return

    # Extract query from command
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "❌ Please provide a song name or YouTube URL.\n\n"
            "<b>Usage:</b>\n"
            "<code>/play Believer</code>\n"
            "<code>/play https://youtu.be/...</code>"
        )
        return

    query = sanitize_query(args[1].strip())
    chat_id = message.chat.id
    user = message.from_user
    requested_by = user.first_name
    if user.username:
        requested_by = f"@{user.username}"

    # Handle YouTube playlists
    if is_url(query) and is_youtube_playlist(query):
        count = await music_service.queue_playlist(
            chat_id=chat_id,
            url=query,
            requested_by_id=user.id,
            requested_by_name=requested_by,
            message=message,
        )
        return

    # Handle single song / search
    result = await music_service.queue_song(
        chat_id=chat_id,
        query=query,
        requested_by_id=user.id,
        requested_by_name=requested_by,
        message=message,
    )

    if result and result.get("position", 1) == 1:
        # First song — show controls keyboard
        await message.reply(
            f"▶️ <b>Now Loading</b>\n\n"
            f"🎵 <b>{result['title']}</b>\n"
            f"⏱ Duration: {format_duration(result['duration'])}\n"
            f"👤 Requested by: {requested_by}",
            reply_markup=player_controls(chat_id, is_paused=False),
        )
