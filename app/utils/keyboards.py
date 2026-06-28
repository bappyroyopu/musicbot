"""
Inline keyboard builders for bot messages.

All control panels use InlineKeyboardMarkup with callback_data
that encodes the action and the chat_id.
"""

from __future__ import annotations

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _btn(text: str, data: str) -> InlineKeyboardButton:
    """Shorthand for creating a callback button."""
    return InlineKeyboardButton(text, callback_data=data)


# ---------------------------------------------------------------------------
# Main player control panel
# ---------------------------------------------------------------------------
def player_controls(chat_id: int, is_paused: bool = False) -> InlineKeyboardMarkup:
    """
    Generate the main playback control keyboard.

    Row 1: Pause/Resume | Skip | Stop
    Row 2: Shuffle | Loop | Volume- | Volume+
    Row 3: Queue | Close
    """
    cid = chat_id
    pause_btn = (
        _btn("▶️ Resume", f"resume_{cid}")
        if is_paused
        else _btn("⏸ Pause", f"pause_{cid}")
    )
    return InlineKeyboardMarkup(
        [
            [pause_btn, _btn("⏭ Skip", f"skip_{cid}"), _btn("⏹ Stop", f"stop_{cid}")],
            [
                _btn("🔀 Shuffle", f"shuffle_{cid}"),
                _btn("🔁 Loop", f"loop_{cid}"),
                _btn("🔉 Vol-", f"vol_down_{cid}"),
                _btn("🔊 Vol+", f"vol_up_{cid}"),
            ],
            [_btn("📋 Queue", f"queue_{cid}"), _btn("❌ Close", f"close_{cid}")],
        ]
    )


# ---------------------------------------------------------------------------
# Search results selection keyboard
# ---------------------------------------------------------------------------
def search_results_keyboard(
    results: list[dict], chat_id: int
) -> InlineKeyboardMarkup:
    """
    Generate a keyboard where each button corresponds to a search result.

    Args:
        results: List of dicts with 'title' and 'url' keys.
        chat_id: Target chat for playback.
    """
    buttons: list[list[InlineKeyboardButton]] = []
    for idx, r in enumerate(results, 1):
        url = r.get("url", "")
        # Encode: select_<chat_id>_<index> — URL resolved server-side
        buttons.append([_btn(f"{idx}. {r['title'][:45]}", f"select_{chat_id}_{idx - 1}")])
    buttons.append([_btn("❌ Cancel", f"cancel_search_{chat_id}")])
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Queue navigation keyboard
# ---------------------------------------------------------------------------
def queue_keyboard(
    chat_id: int, page: int, total_pages: int
) -> InlineKeyboardMarkup:
    """Pagination keyboard for the queue listing."""
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(_btn("◀ Prev", f"queue_page_{chat_id}_{page - 1}"))
    if page < total_pages:
        nav.append(_btn("Next ▶", f"queue_page_{chat_id}_{page + 1}"))

    rows: list[list[InlineKeyboardButton]] = []
    if nav:
        rows.append(nav)
    rows.append(
        [_btn("🗑 Clear Queue", f"clear_queue_{chat_id}"), _btn("❌ Close", f"close_{chat_id}")]
    )
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Settings keyboard
# ---------------------------------------------------------------------------
def settings_keyboard(
    chat_id: int,
    loop: bool,
    shuffle: bool,
    auto_leave: bool,
    volume: int,
) -> InlineKeyboardMarkup:
    """Settings panel for per-group configuration."""
    loop_label = f"🔁 Loop: {'ON' if loop else 'OFF'}"
    shuffle_label = f"🔀 Shuffle: {'ON' if shuffle else 'OFF'}"
    leave_label = f"🚪 Auto-leave: {'ON' if auto_leave else 'OFF'}"

    return InlineKeyboardMarkup(
        [
            [_btn(loop_label, f"toggle_loop_{chat_id}")],
            [_btn(shuffle_label, f"toggle_shuffle_{chat_id}")],
            [_btn(leave_label, f"toggle_autoleave_{chat_id}")],
            [
                _btn("🔉 Vol-10", f"vol_down_{chat_id}"),
                _btn(f"🔊 {volume}%", f"noop"),
                _btn("🔊 Vol+10", f"vol_up_{chat_id}"),
            ],
            [_btn("❌ Close", f"close_{chat_id}")],
        ]
    )


# ---------------------------------------------------------------------------
# Confirmation keyboard (for destructive actions)
# ---------------------------------------------------------------------------
def confirm_keyboard(action: str, chat_id: int) -> InlineKeyboardMarkup:
    """Generic yes/no confirmation keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                _btn("✅ Yes", f"confirm_{action}_{chat_id}"),
                _btn("❌ No", f"cancel_{action}_{chat_id}"),
            ]
        ]
    )


# ---------------------------------------------------------------------------
# Playlist keyboard
# ---------------------------------------------------------------------------
def playlist_keyboard(
    playlists: list,  # list[Playlist]
    action: str = "load",
) -> InlineKeyboardMarkup:
    """List user playlists as selectable buttons."""
    buttons: list[list[InlineKeyboardButton]] = []
    for pl in playlists:
        buttons.append([_btn(f"📀 {pl.name}", f"pl_{action}_{pl.id}")])
    if not buttons:
        buttons.append([_btn("No playlists found", "noop")])
    return InlineKeyboardMarkup(buttons)
