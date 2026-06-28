"""
In-memory queue manager for per-group playback queues.

Tracks the live state of voice chat playback for each group:
- Current song being played
- Ordered queue of upcoming songs
- Loop and shuffle mode flags
- Volume
- Playback start time (for progress bar)

This complements the database queue (used for persistence) with a
fast in-memory representation used during active sessions.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from app.player.downloader import SongInfo


@dataclass
class TrackState:
    """Runtime state of a song currently playing."""

    song: SongInfo
    started_at: float = field(default_factory=time.monotonic)
    queue_item_id: Optional[int] = None   # DB QueueItem.id

    @property
    def elapsed(self) -> int:
        """Seconds since playback started."""
        return int(time.monotonic() - self.started_at)

    @property
    def remaining(self) -> int:
        """Estimated seconds remaining (may be negative when done)."""
        return max(0, self.song.duration - self.elapsed)


class GroupQueue:
    """
    Per-group in-memory queue.

    Thread-safe via asyncio lock. All public methods are async.
    """

    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id
        self._lock = asyncio.Lock()
        self._queue: list[SongInfo] = []
        self._current: Optional[TrackState] = None
        self.loop: bool = False
        self.shuffle: bool = False
        self.volume: int = 100
        self.is_paused: bool = False
        self._last_activity: float = time.monotonic()

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    async def add(self, song: SongInfo, queue_item_id: Optional[int] = None) -> int:
        """
        Add a song to the end of the queue.

        Returns the 1-based position in queue (1 = next to play).
        """
        async with self._lock:
            self._queue.append(song)
            self._last_activity = time.monotonic()
            logger.debug(
                "[chat_id={}] Added to queue: {} (position {})",
                self.chat_id,
                song.title,
                len(self._queue),
            )
            return len(self._queue)

    async def next(self) -> Optional[SongInfo]:
        """
        Pop and return the next song to play.

        Applies shuffle if enabled. If loop is enabled and a current track
        exists, re-adds the current track to the front before popping.
        """
        async with self._lock:
            if self._current and self.loop:
                # Re-insert the current song at the front
                self._queue.insert(0, self._current.song)

            if not self._queue:
                self._current = None
                return None

            if self.shuffle and len(self._queue) > 1:
                idx = random.randint(0, len(self._queue) - 1)
                song = self._queue.pop(idx)
            else:
                song = self._queue.pop(0)

            self._current = TrackState(song=song)
            self._last_activity = time.monotonic()
            logger.info("[chat_id={}] Now playing: {}", self.chat_id, song.title)
            return song

    async def skip(self) -> Optional[SongInfo]:
        """
        Skip the current song and return the next one.

        Loop is temporarily bypassed for skip.
        """
        async with self._lock:
            self._current = None

        # Return next without loop re-insertion
        original_loop = self.loop
        self.loop = False
        song = await self.next()
        self.loop = original_loop
        return song

    async def clear(self) -> int:
        """
        Clear all queued (not current) songs.

        Returns the number of songs removed.
        """
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    async def shuffle_queue(self) -> None:
        """Randomly shuffle all pending songs in the queue."""
        async with self._lock:
            random.shuffle(self._queue)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    async def get_queue(self) -> list[SongInfo]:
        """Return a snapshot of pending songs."""
        async with self._lock:
            return list(self._queue)

    async def get_current(self) -> Optional[TrackState]:
        """Return the currently playing track state."""
        async with self._lock:
            return self._current

    async def size(self) -> int:
        """Return the number of songs waiting in queue."""
        async with self._lock:
            return len(self._queue)

    async def is_empty(self) -> bool:
        """True if no songs are queued."""
        return await self.size() == 0

    # ------------------------------------------------------------------
    # Playback controls
    # ------------------------------------------------------------------

    async def pause(self) -> None:
        """Mark queue as paused."""
        async with self._lock:
            self.is_paused = True

    async def resume(self) -> None:
        """Mark queue as resumed."""
        async with self._lock:
            self.is_paused = False
            self._last_activity = time.monotonic()

    async def set_volume(self, volume: int) -> None:
        """Update the volume (1–200)."""
        async with self._lock:
            self.volume = max(1, min(200, volume))

    async def toggle_loop(self) -> bool:
        """Toggle loop mode and return the new state."""
        async with self._lock:
            self.loop = not self.loop
            return self.loop

    async def toggle_shuffle(self) -> bool:
        """Toggle shuffle mode and return the new state."""
        async with self._lock:
            self.shuffle = not self.shuffle
            return self.shuffle

    @property
    def seconds_since_activity(self) -> float:
        """Seconds since the last queue activity."""
        return time.monotonic() - self._last_activity

    async def mark_current_done(self) -> None:
        """Mark the current track as finished."""
        async with self._lock:
            self._current = None
            self._last_activity = time.monotonic()


class QueueManager:
    """
    Global manager for all active group queues.

    Maintains one GroupQueue instance per chat_id.
    """

    def __init__(self) -> None:
        self._queues: dict[int, GroupQueue] = {}
        self._lock = asyncio.Lock()

    async def get(self, chat_id: int) -> GroupQueue:
        """Return the GroupQueue for the given chat, creating if needed."""
        async with self._lock:
            if chat_id not in self._queues:
                self._queues[chat_id] = GroupQueue(chat_id)
            return self._queues[chat_id]

    async def remove(self, chat_id: int) -> None:
        """Remove a group's queue (when bot leaves the chat)."""
        async with self._lock:
            self._queues.pop(chat_id, None)

    async def active_chats(self) -> list[int]:
        """Return a list of all chat_ids with active queues."""
        async with self._lock:
            return list(self._queues.keys())


# Module-level singleton
queue_manager = QueueManager()
