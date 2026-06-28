"""
/queue command — display the current playback queue.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.bot.filters import group_only, not_banned
from app.player.queue import queue_manager
from app.utils.formatters import format_queue_list, format_duration
from app.utils.keyboards import queue_keyboard


PAGE_SIZE = 10


@Client.on_message(filters.command("queue") & group_only & not_banned)
async def queue_command(client: Client, message: Message) -> None:
    """
    Display the current queue for the group.

    Shows:
    - Currently playing song
    - Upcoming songs (paginated)
    - Total count and estimated duration
    """
    chat_id = message.chat.id
    gq = await queue_manager.get(chat_id)

    current = await gq.get_current()
    pending = await gq.get_queue()

    current_title = current.song.title if current else None

    if current is None and not pending:
        await message.reply(
            "📭 The queue is empty.\n\nUse /play to add songs!"
        )
        return

    # Calculate total duration
    total_secs = sum(s.duration for s in pending)
    if current:
        total_secs += max(0, current.song.duration - current.elapsed)

    text = format_queue_list(
        items=pending,
        current_title=current_title,
        page=1,
        page_size=PAGE_SIZE,
    )

    total_pages = max(1, (len(pending) + PAGE_SIZE - 1) // PAGE_SIZE)
    footer = f"\n\n⏱ Total remaining: <b>{format_duration(total_secs)}</b>"
    if gq.loop:
        footer += " • 🔁 Loop ON"
    if gq.shuffle:
        footer += " • 🔀 Shuffle ON"

    await message.reply(
        text + footer,
        reply_markup=queue_keyboard(chat_id, page=1, total_pages=total_pages),
    )
