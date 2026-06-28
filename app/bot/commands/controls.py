"""
Playback control commands: /pause, /resume, /skip, /stop, /loop, /shuffle,
/volume, /nowplaying, /clear.
"""

from __future__ import annotations

import time

from pyrogram import Client, filters
from pyrogram.types import Message

from app.bot.filters import admin_only, group_only, not_banned
from app.player.queue import queue_manager
from app.services.music_service import music_service
from app.utils.formatters import format_duration, format_now_playing, make_progress_bar
from app.utils.keyboards import player_controls
from app.utils.validators import is_valid_volume


# ---------------------------------------------------------------------------
# /pause
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("pause") & group_only & not_banned & admin_only)
async def pause_command(client: Client, message: Message) -> None:
    """Pause the current playback."""
    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)
    current = await gq.get_current()

    if current is None:
        await message.reply("❌ Nothing is playing right now.")
        return

    if gq.is_paused:
        await message.reply("⚠️ Playback is already paused. Use /resume to continue.")
        return

    success = await music_service.pause(chat_id)
    if success:
        await message.reply(
            f"⏸ <b>Paused</b>: {current.song.title}",
            reply_markup=player_controls(chat_id, is_paused=True),
        )
    else:
        await message.reply("❌ Could not pause. Is the bot in a voice chat?")


# ---------------------------------------------------------------------------
# /resume
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("resume") & group_only & not_banned & admin_only)
async def resume_command(client: Client, message: Message) -> None:
    """Resume paused playback."""
    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)

    if not gq.is_paused:
        await message.reply("⚠️ Playback is not paused.")
        return

    success = await music_service.resume(chat_id)
    if success:
        current = await gq.get_current()
        title = current.song.title if current else "Unknown"
        await message.reply(
            f"▶️ <b>Resumed</b>: {title}",
            reply_markup=player_controls(chat_id, is_paused=False),
        )
    else:
        await message.reply("❌ Could not resume. Is the bot in a voice chat?")


# ---------------------------------------------------------------------------
# /skip
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("skip") & group_only & not_banned & admin_only)
async def skip_command(client: Client, message: Message) -> None:
    """Skip the current song and play the next one."""
    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)
    current = await gq.get_current()

    if current is None:
        await message.reply("❌ Nothing is playing right now.")
        return

    next_song = await music_service.skip(chat_id)
    if next_song:
        await message.reply(
            f"⏭ Skipped. Now playing:\n"
            f"🎵 <b>{next_song.title}</b>",
            reply_markup=player_controls(chat_id, is_paused=False),
        )
    else:
        await message.reply("⏹ Skipped. Queue is now empty.")


# ---------------------------------------------------------------------------
# /stop
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("stop") & group_only & not_banned & admin_only)
async def stop_command(client: Client, message: Message) -> None:
    """Stop playback, clear queue, and leave voice chat."""
    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)
    current = await gq.get_current()

    if current is None and await gq.is_empty():
        await message.reply("❌ Nothing is playing right now.")
        return

    await music_service.stop(chat_id)
    await message.reply("⏹ <b>Stopped.</b> Queue cleared and left the voice chat.")


# ---------------------------------------------------------------------------
# /nowplaying
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("nowplaying") & group_only & not_banned)
async def nowplaying_command(client: Client, message: Message) -> None:
    """Show the currently playing song with a progress bar."""
    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)
    current = await gq.get_current()

    if current is None:
        await message.reply("❌ Nothing is playing right now. Use /play to start.")
        return

    queue_size = await gq.size()
    text = format_now_playing(
        title=current.song.title,
        url=current.song.url,
        duration=current.song.duration,
        elapsed=current.elapsed,
        requested_by=current.song.uploader or "Unknown",
        uploader=current.song.uploader,
        loop=gq.loop,
        volume=gq.volume,
        queue_size=queue_size,
    )
    await message.reply(
        text,
        reply_markup=player_controls(chat_id, is_paused=gq.is_paused),
    )


# ---------------------------------------------------------------------------
# /loop
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("loop") & group_only & not_banned & admin_only)
async def loop_command(client: Client, message: Message) -> None:
    """Toggle loop mode for the current group."""
    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)
    new_state = await gq.toggle_loop()
    icon = "🔁" if new_state else "➡️"
    state_text = "enabled" if new_state else "disabled"
    await message.reply(f"{icon} Loop mode <b>{state_text}</b>.")


# ---------------------------------------------------------------------------
# /shuffle
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("shuffle") & group_only & not_banned & admin_only)
async def shuffle_command(client: Client, message: Message) -> None:
    """Toggle shuffle mode and reshuffle the current queue."""
    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)
    new_state = await gq.toggle_shuffle()
    if new_state:
        await gq.shuffle_queue()
    icon = "🔀" if new_state else "➡️"
    state_text = "enabled" if new_state else "disabled"
    await message.reply(f"{icon} Shuffle mode <b>{state_text}</b>.")


# ---------------------------------------------------------------------------
# /volume
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("volume") & group_only & not_banned & admin_only)
async def volume_command(client: Client, message: Message) -> None:
    """Set the playback volume (1–200)."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        gq = await queue_manager.get(message.chat.id)
        await message.reply(
            f"🔊 Current volume: <b>{gq.volume}%</b>\n\n"
            f"Usage: <code>/volume 80</code> (1-200)"
        )
        return

    try:
        volume = int(args[1].strip())
    except ValueError:
        await message.reply("❌ Please provide a valid number. Example: <code>/volume 80</code>")
        return

    if not is_valid_volume(volume):
        await message.reply("❌ Volume must be between <b>1</b> and <b>200</b>.")
        return

    success = await music_service.set_volume(message.chat.id, volume)
    if success:
        icon = "🔇" if volume == 0 else ("🔉" if volume < 60 else "🔊")
        await message.reply(f"{icon} Volume set to <b>{volume}%</b>.")
    else:
        await message.reply("❌ Could not set volume. Is the bot in a voice chat?")


# ---------------------------------------------------------------------------
# /clear
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("clear") & group_only & not_banned & admin_only)
async def clear_command(client: Client, message: Message) -> None:
    """Clear all pending songs from the queue."""
    from app.database import get_session
    from app.database.routers import queue as queue_crud

    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)
    count = await gq.clear()

    async with get_session() as session:
        db_count = await queue_crud.clear_queue(session, chat_id)

    await message.reply(
        f"🗑 Cleared <b>{max(count, db_count)}</b> song(s) from the queue."
    )
