"""Commands package — imports all command modules to register handlers."""

from app.bot.commands import (
    start,
    help,
    play,
    controls,
    queue_cmd,
    search,
    playlist,
    settings,
    stats,
)

__all__ = [
    "start",
    "help",
    "play",
    "controls",
    "queue_cmd",
    "search",
    "playlist",
    "settings",
    "stats",
]
