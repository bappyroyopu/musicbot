"""
/search command — search YouTube and show selectable results.
/lyrics command — fetch lyrics for the current or a specified song.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.bot.filters import group_only, not_banned
from app.config import settings
from app.player.downloader import downloader
from app.player.queue import queue_manager
from app.utils.formatters import format_search_results
from app.utils.keyboards import search_results_keyboard
from app.utils.lyrics import fetch_lyrics
from app.utils.validators import sanitize_query

# Session storage for search results (chat_id -> list of SongInfo)
# In production this could be Redis; in-memory is fine for most use cases.
_search_sessions: dict[int, list] = {}


@Client.on_message(filters.command("search") & group_only & not_banned)
async def search_command(client: Client, message: Message) -> None:
    """
    Search YouTube and present results as selectable buttons.

    Usage: /search Never Gonna Give You Up
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "❌ Please provide a search query.\n\n"
            "Usage: <code>/search Bohemian Rhapsody</code>"
        )
        return

    query = sanitize_query(args[1].strip())
    chat_id = message.chat.id

    status_msg = await message.reply(f"🔍 Searching YouTube for: <i>{query}</i>...")

    results = await downloader.search_youtube(
        query, max_results=settings.max_search_results
    )

    if not results:
        await status_msg.edit("❌ No results found. Try a different search term.")
        return

    # Store results for callback resolution
    _search_sessions[chat_id] = results

    text = format_search_results(
        [
            {
                "title": r.title,
                "url": r.url,
                "duration": r.duration,
                "uploader": r.uploader or "Unknown",
            }
            for r in results
        ]
    )

    await status_msg.edit(
        text + "\n\n<i>Tap a number to play that song:</i>",
        reply_markup=search_results_keyboard(
            [{"title": r.title, "url": r.url} for r in results],
            chat_id,
        ),
    )


def get_search_results(chat_id: int) -> list:
    """Return stored search results for a chat."""
    return _search_sessions.get(chat_id, [])


def clear_search_results(chat_id: int) -> None:
    """Clear stored search results for a chat."""
    _search_sessions.pop(chat_id, None)


# ---------------------------------------------------------------------------
# /lyrics
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("lyrics") & not_banned)
async def lyrics_command(client: Client, message: Message) -> None:
    """
    Fetch and display lyrics.

    Usage:
        /lyrics              — Lyrics for the current song
        /lyrics <song name>  — Lyrics for a specific song
    """
    args = message.text.split(maxsplit=1)
    song_name: str | None = None
    artist: str | None = None

    if len(args) >= 2 and args[1].strip():
        song_name = sanitize_query(args[1].strip())
    else:
        # Try to get the current song's title
        if message.chat and message.chat.type.name in ("GROUP", "SUPERGROUP"):
            gq = await queue_manager.get(message.chat.id)
            current = await gq.get_current()
            if current:
                song_name = current.song.title
                artist = current.song.uploader

    if not song_name:
        await message.reply(
            "❌ No song is currently playing.\n\n"
            "Usage: <code>/lyrics Hotel California</code>"
        )
        return

    status_msg = await message.reply(f"🎤 Fetching lyrics for: <i>{song_name}</i>...")

    lyrics = await fetch_lyrics(song_name, artist)

    if not lyrics:
        await status_msg.edit(
            f"❌ Could not find lyrics for <b>{song_name}</b>."
        )
        return

    # Telegram message limit is ~4096 chars — split if needed
    MAX_LEN = 4000
    if len(lyrics) <= MAX_LEN:
        await status_msg.edit(
            f"🎤 <b>Lyrics: {song_name}</b>\n\n{lyrics}"
        )
    else:
        await status_msg.edit(f"🎤 <b>Lyrics: {song_name}</b>")
        chunks = [lyrics[i:i+MAX_LEN] for i in range(0, len(lyrics), MAX_LEN)]
        for chunk in chunks:
            await message.reply(chunk)
