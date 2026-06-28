"""
Callback query handler — processes all InlineKeyboard button presses.

Handles:
  pause_{chat_id}          — Pause playback
  resume_{chat_id}         — Resume playback
  skip_{chat_id}           — Skip current song
  stop_{chat_id}           — Stop and leave
  shuffle_{chat_id}        — Toggle shuffle
  loop_{chat_id}           — Toggle loop
  vol_up_{chat_id}         — Volume +10
  vol_down_{chat_id}       — Volume -10
  queue_{chat_id}          — Show queue
  queue_page_{chat_id}_{n} — Queue pagination
  clear_queue_{chat_id}    — Clear queue
  select_{chat_id}_{idx}   — Select search result
  cancel_search_{chat_id}  — Cancel search
  toggle_loop_{chat_id}    — Toggle loop in settings
  toggle_shuffle_{chat_id} — Toggle shuffle in settings
  toggle_autoleave_{chat_id} — Toggle auto-leave in settings
  close_{chat_id}          — Delete the message
  noop                     — No operation
"""

from __future__ import annotations

import re

from loguru import logger
from pyrogram import Client
from pyrogram.types import CallbackQuery

from app.database import get_session
from app.database.routers import groups as group_crud
from app.player.queue import queue_manager
from app.services.music_service import music_service
from app.utils.formatters import format_duration, format_queue_list
from app.utils.keyboards import player_controls, queue_keyboard, settings_keyboard


def _extract_chat_id(data: str, prefix: str) -> int | None:
    """Extract chat_id from callback data like 'prefix_<chat_id>'."""
    rest = data[len(prefix):]
    try:
        return int(rest)
    except ValueError:
        return None


@Client.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery) -> None:
    """Route all InlineKeyboard callbacks to the appropriate handler."""
    data = query.data or ""
    user = query.from_user

    logger.debug("Callback from user_id={} data={!r}", user.id if user else "?", data)

    # ----------------------------------------------------------------
    # No-operation
    # ----------------------------------------------------------------
    if data == "noop":
        await query.answer()
        return

    # ----------------------------------------------------------------
    # Close message
    # ----------------------------------------------------------------
    if data.startswith("close_"):
        await query.message.delete()
        await query.answer("Closed.")
        return

    # ----------------------------------------------------------------
    # Pause
    # ----------------------------------------------------------------
    if data.startswith("pause_"):
        chat_id = _extract_chat_id(data, "pause_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        success = await music_service.pause(chat_id)
        if success:
            await query.answer("⏸ Paused!")
            try:
                await query.message.edit_reply_markup(
                    reply_markup=player_controls(chat_id, is_paused=True)
                )
            except Exception:
                pass
        else:
            await query.answer("❌ Could not pause.", show_alert=True)
        return

    # ----------------------------------------------------------------
    # Resume
    # ----------------------------------------------------------------
    if data.startswith("resume_"):
        chat_id = _extract_chat_id(data, "resume_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        success = await music_service.resume(chat_id)
        if success:
            await query.answer("▶️ Resumed!")
            try:
                await query.message.edit_reply_markup(
                    reply_markup=player_controls(chat_id, is_paused=False)
                )
            except Exception:
                pass
        else:
            await query.answer("❌ Could not resume.", show_alert=True)
        return

    # ----------------------------------------------------------------
    # Skip
    # ----------------------------------------------------------------
    if data.startswith("skip_"):
        chat_id = _extract_chat_id(data, "skip_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        next_song = await music_service.skip(chat_id)
        if next_song:
            await query.answer(f"⏭ Skipped! Now: {next_song.title[:30]}")
        else:
            await query.answer("⏹ Skipped. Queue empty.")
        return

    # ----------------------------------------------------------------
    # Stop
    # ----------------------------------------------------------------
    if data.startswith("stop_"):
        chat_id = _extract_chat_id(data, "stop_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        await music_service.stop(chat_id)
        await query.answer("⏹ Stopped!")
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    # ----------------------------------------------------------------
    # Shuffle
    # ----------------------------------------------------------------
    if data.startswith("shuffle_"):
        chat_id = _extract_chat_id(data, "shuffle_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        gq = await queue_manager.get(chat_id)
        new_state = await gq.toggle_shuffle()
        if new_state:
            await gq.shuffle_queue()
        state_text = "ON 🔀" if new_state else "OFF ➡️"
        await query.answer(f"Shuffle: {state_text}")
        return

    # ----------------------------------------------------------------
    # Loop
    # ----------------------------------------------------------------
    if data.startswith("loop_"):
        chat_id = _extract_chat_id(data, "loop_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        gq = await queue_manager.get(chat_id)
        new_state = await gq.toggle_loop()
        state_text = "ON 🔁" if new_state else "OFF ➡️"
        await query.answer(f"Loop: {state_text}")
        return

    # ----------------------------------------------------------------
    # Volume Up
    # ----------------------------------------------------------------
    if data.startswith("vol_up_"):
        chat_id = _extract_chat_id(data, "vol_up_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        gq = await queue_manager.get(chat_id)
        new_vol = min(200, gq.volume + 10)
        await music_service.set_volume(chat_id, new_vol)
        await query.answer(f"🔊 Volume: {new_vol}%")
        return

    # ----------------------------------------------------------------
    # Volume Down
    # ----------------------------------------------------------------
    if data.startswith("vol_down_"):
        chat_id = _extract_chat_id(data, "vol_down_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        gq = await queue_manager.get(chat_id)
        new_vol = max(1, gq.volume - 10)
        await music_service.set_volume(chat_id, new_vol)
        await query.answer(f"🔉 Volume: {new_vol}%")
        return

    # ----------------------------------------------------------------
    # Queue display
    # ----------------------------------------------------------------
    if re.match(r"^queue_\-?\d+$", data):
        chat_id = _extract_chat_id(data, "queue_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        gq = await queue_manager.get(chat_id)
        current = await gq.get_current()
        pending = await gq.get_queue()
        text = format_queue_list(
            items=pending,
            current_title=current.song.title if current else None,
            page=1,
        )
        total_pages = max(1, (len(pending) + 9) // 10)
        await query.answer()
        try:
            await query.message.edit_text(
                text,
                reply_markup=queue_keyboard(chat_id, page=1, total_pages=total_pages),
            )
        except Exception:
            pass
        return

    # ----------------------------------------------------------------
    # Queue pagination
    # ----------------------------------------------------------------
    m = re.match(r"^queue_page_(\-?\d+)_(\d+)$", data)
    if m:
        chat_id = int(m.group(1))
        page = int(m.group(2))
        gq = await queue_manager.get(chat_id)
        current = await gq.get_current()
        pending = await gq.get_queue()
        text = format_queue_list(
            items=pending,
            current_title=current.song.title if current else None,
            page=page,
        )
        total_pages = max(1, (len(pending) + 9) // 10)
        await query.answer()
        try:
            await query.message.edit_text(
                text,
                reply_markup=queue_keyboard(chat_id, page=page, total_pages=total_pages),
            )
        except Exception:
            pass
        return

    # ----------------------------------------------------------------
    # Clear queue
    # ----------------------------------------------------------------
    if data.startswith("clear_queue_"):
        chat_id = _extract_chat_id(data, "clear_queue_")
        if chat_id is None:
            await query.answer("Invalid button.")
            return
        gq = await queue_manager.get(chat_id)
        count = await gq.clear()
        await query.answer(f"🗑 Cleared {count} songs.")
        return

    # ----------------------------------------------------------------
    # Select search result
    # ----------------------------------------------------------------
    m = re.match(r"^select_(\-?\d+)_(\d+)$", data)
    if m:
        chat_id = int(m.group(1))
        idx = int(m.group(2))
        from app.bot.commands.search import get_search_results, clear_search_results
        results = get_search_results(chat_id)
        if not results or idx >= len(results):
            await query.answer("❌ Search results expired. Try /search again.", show_alert=True)
            return
        song = results[idx]
        clear_search_results(chat_id)
        await query.answer(f"▶️ Queuing: {song.title[:30]}")
        try:
            await query.message.delete()
        except Exception:
            pass
        user_name = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
        await music_service.queue_song(
            chat_id=chat_id,
            query=song.url,
            requested_by_id=query.from_user.id,
            requested_by_name=user_name,
        )
        return

    # ----------------------------------------------------------------
    # Cancel search
    # ----------------------------------------------------------------
    if data.startswith("cancel_search_"):
        from app.bot.commands.search import clear_search_results
        chat_id = _extract_chat_id(data, "cancel_search_")
        if chat_id:
            clear_search_results(chat_id)
        await query.answer("Search cancelled.")
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    # ----------------------------------------------------------------
    # Settings toggles
    # ----------------------------------------------------------------
    if data.startswith("toggle_loop_"):
        chat_id = _extract_chat_id(data, "toggle_loop_")
        if chat_id is None:
            await query.answer()
            return
        async with get_session() as session:
            group = await group_crud.get_group(session, chat_id)
            if group:
                await group_crud.update_group_setting(session, chat_id, loop=not group.loop)
                gq = await queue_manager.get(chat_id)
                gq.loop = not group.loop
                await _refresh_settings_message(query, chat_id)
        await query.answer(f"Loop: {'ON' if not (group.loop if group else False) else 'OFF'}")
        return

    if data.startswith("toggle_shuffle_"):
        chat_id = _extract_chat_id(data, "toggle_shuffle_")
        if chat_id is None:
            await query.answer()
            return
        async with get_session() as session:
            group = await group_crud.get_group(session, chat_id)
            if group:
                await group_crud.update_group_setting(session, chat_id, shuffle=not group.shuffle)
                gq = await queue_manager.get(chat_id)
                gq.shuffle = not group.shuffle
                await _refresh_settings_message(query, chat_id)
        await query.answer(f"Shuffle: {'ON' if not (group.shuffle if group else False) else 'OFF'}")
        return

    if data.startswith("toggle_autoleave_"):
        chat_id = _extract_chat_id(data, "toggle_autoleave_")
        if chat_id is None:
            await query.answer()
            return
        async with get_session() as session:
            group = await group_crud.get_group(session, chat_id)
            if group:
                await group_crud.update_group_setting(session, chat_id, auto_leave=not group.auto_leave)
                await _refresh_settings_message(query, chat_id)
        await query.answer(f"Auto-leave: {'ON' if not (group.auto_leave if group else True) else 'OFF'}")
        return

    # Unknown button
    await query.answer("❓ Unknown action.")


async def _refresh_settings_message(query: CallbackQuery, chat_id: int) -> None:
    """Reload settings and update the keyboard in place."""
    async with get_session() as session:
        group = await group_crud.get_group(session, chat_id)
    if group is None:
        return
    try:
        await query.message.edit_reply_markup(
            reply_markup=settings_keyboard(
                chat_id=chat_id,
                loop=group.loop,
                shuffle=group.shuffle,
                auto_leave=group.auto_leave,
                volume=group.volume,
            )
        )
    except Exception:
        pass
