"""
/help command handler — displays all available commands.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.bot.filters import not_banned


HELP_TEXT = """
🎵 <b>Music Bot — Command Reference</b>

<b>🎮 Playback</b>
/play &lt;song or URL&gt; — Search &amp; play a song
/pause — Pause playback
/resume — Resume playback
/skip — Skip current song
/stop — Stop and clear queue

<b>📋 Queue Management</b>
/queue — View current queue
/clear — Clear the entire queue
/shuffle — Toggle shuffle mode
/loop — Toggle loop mode
/nowplaying — Show current song info

<b>🔊 Volume</b>
/volume &lt;1-200&gt; — Set volume (e.g. /volume 80)

<b>🔍 Search</b>
/search &lt;query&gt; — Search YouTube and pick a result

<b>🎤 Lyrics</b>
/lyrics — Get lyrics for the current song
/lyrics &lt;song name&gt; — Get lyrics for any song

<b>📀 Playlists</b>
/playlist — View your playlists
/playlist create &lt;name&gt; — Create a playlist
/playlist add &lt;name&gt; — Add current song to playlist
/playlist play &lt;name&gt; — Play a playlist

<b>ℹ️ Info</b>
/ping — Check bot latency
/stats — Bot statistics
/settings — Group settings

<b>💡 Tips</b>
• You can paste YouTube playlist URLs with /play
• Use inline buttons below the now-playing message for quick control
• Admins can change group settings with /settings
"""


@Client.on_message(filters.command("help") & not_banned)
async def help_command(client: Client, message: Message) -> None:
    """Send the full command reference."""
    await message.reply(HELP_TEXT.strip())
