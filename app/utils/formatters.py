"""
Formatting utilities for bot messages.

Provides helpers for progress bars, duration strings, queue listings,
now-playing cards, and other formatted output.
"""

from __future__ import annotations

from typing import Optional


def format_duration(seconds: int) -> str:
    """
    Convert seconds to human-readable duration string.

    Examples:
        format_duration(65)    -> "01:05"
        format_duration(3700)  -> "1:01:40"
    """
    if seconds <= 0:
        return "00:00"
    hours, remainder = divmod(int(seconds), 3600)
    mins, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def make_progress_bar(
    elapsed: int,
    total: int,
    length: int = 15,
    filled: str = "▓",
    empty: str = "░",
) -> str:
    """
    Generate a text-based progress bar.

    Args:
        elapsed: Seconds elapsed.
        total: Total duration in seconds.
        length: Number of characters in the bar.
        filled: Character for filled portion.
        empty: Character for empty portion.

    Returns:
        E.g. "▓▓▓▓▓░░░░░░░░░░"
    """
    if total <= 0:
        return empty * length
    ratio = min(elapsed / total, 1.0)
    filled_count = int(ratio * length)
    return filled * filled_count + empty * (length - filled_count)


def format_now_playing(
    title: str,
    url: str,
    duration: int,
    elapsed: int,
    requested_by: str,
    uploader: Optional[str] = None,
    thumbnail: Optional[str] = None,
    position: int = 1,
    queue_size: int = 0,
    loop: bool = False,
    volume: int = 100,
) -> str:
    """
    Build the now-playing message with progress bar.

    Returns an HTML-formatted string.
    """
    bar = make_progress_bar(elapsed, duration)
    elapsed_str = format_duration(elapsed)
    total_str = format_duration(duration)

    loop_icon = "🔁 " if loop else ""
    vol_icon = "🔇" if volume == 0 else "🔊"

    lines = [
        f"🎵 <b>Now Playing</b>",
        f"",
        f"<b>{title}</b>",
        f"",
        f"{bar}",
        f"<code>{elapsed_str}</code> / <code>{total_str}</code>",
        f"",
        f"👤 Requested by: {requested_by}",
    ]
    if uploader:
        lines.append(f"📺 Channel: <i>{uploader}</i>")
    lines += [
        f"{vol_icon} Volume: <b>{volume}%</b>  {loop_icon}",
        f"📋 Queue: <b>{queue_size}</b> song(s)",
    ]

    return "\n".join(lines)


def format_queue_list(
    items: list,  # list[QueueItem]
    current_title: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> str:
    """
    Format the queue as a numbered HTML list.

    Args:
        items: List of QueueItem ORM objects.
        current_title: Title of the currently playing song (shown at top).
        page: Current page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        HTML-formatted queue listing.
    """
    if not items and not current_title:
        return "📭 The queue is empty."

    lines: list[str] = ["📋 <b>Music Queue</b>\n"]

    if current_title:
        lines.append(f"▶️ <b>Now Playing:</b> {current_title}\n")

    if not items:
        lines.append("<i>No songs in queue.</i>")
        return "\n".join(lines)

    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]
    total_pages = (len(items) + page_size - 1) // page_size

    for idx, item in enumerate(page_items, start=start + 1):
        duration_str = format_duration(item.duration)
        lines.append(
            f"<b>{idx}.</b> {item.title} "
            f"[<code>{duration_str}</code>] — {item.requested_by_name}"
        )

    lines.append(f"\n<i>Page {page}/{total_pages} • {len(items)} song(s)</i>")
    return "\n".join(lines)


def format_search_results(results: list[dict]) -> str:
    """
    Format YouTube search results as a numbered list.

    Args:
        results: List of dicts with keys: title, url, duration, uploader.
    """
    if not results:
        return "🔍 No results found."

    lines = ["🔍 <b>Search Results</b>\n"]
    for idx, r in enumerate(results, 1):
        dur = format_duration(r.get("duration", 0))
        uploader = r.get("uploader", "Unknown")
        lines.append(
            f"<b>{idx}.</b> {r['title']}\n"
            f"    ⏱ {dur} • 📺 {uploader}"
        )
    return "\n".join(lines)


def truncate(text: str, max_len: int = 40) -> str:
    """Truncate text to max_len characters with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
