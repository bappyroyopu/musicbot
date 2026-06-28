"""
Music Service — core orchestration layer.

Connects the downloader, queue manager, voice engine, and database
into a single high-level API used by all bot commands.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger
from pyrogram.types import Message

from app.config import settings
from app.database import get_session
from app.database.models.queue import QueueStatus
from app.database.routers import queue as queue_crud
from app.database.routers import groups as group_crud
from app.database.routers import history as history_crud
from app.player.downloader import SongInfo, downloader
from app.player.queue import queue_manager
from app.utils.formatters import format_duration


class MusicService:
    """
    Orchestrates the full lifecycle of music playback for a group.

    Responsibilities:
    - Validate and queue songs
    - Download audio asynchronously
    - Hand off to voice engine for playback
    - Manage queue transitions (skip, next, stop)
    - Clean up temp files after playback
    - Record history
    """

    def __init__(self) -> None:
        # Import lazily to avoid circular imports at module load time
        self._engine = None

    @property
    def engine(self):
        """Lazy accessor for the global voice engine."""
        if self._engine is None:
            from app.player.voice.engine import voice_engine
            self._engine = voice_engine
        return self._engine

    # ------------------------------------------------------------------
    # Queue a song
    # ------------------------------------------------------------------

    async def queue_song(
        self,
        chat_id: int,
        query: str,
        requested_by_id: int,
        requested_by_name: str,
        message: Optional[Message] = None,
    ) -> Optional[dict]:
        """
        Resolve a query (URL or search term), validate, and add to queue.

        Returns a dict with song metadata on success, None on failure.
        Sends status messages to the chat if `message` is provided.
        """
        # 1. Resolve metadata
        if message:
            status_msg = await message.reply("🔍 Searching...")

        song = await downloader.resolve(query)

        if song is None:
            if message:
                await status_msg.edit("❌ Could not find the song. Try again.")  # type: ignore
            return None

        # 2. Validate duration
        if settings.max_duration > 0 and song.duration > settings.max_duration:
            max_str = format_duration(settings.max_duration)
            if message:
                await status_msg.edit(  # type: ignore
                    f"❌ Song is too long. Maximum duration is <b>{max_str}</b>."
                )
            return None

        # 3. Check queue size limit
        gq = await queue_manager.get(chat_id)
        current_size = await gq.size()
        if settings.max_queue_size > 0 and current_size >= settings.max_queue_size:
            if message:
                await status_msg.edit(  # type: ignore
                    f"❌ Queue is full ({settings.max_queue_size} songs max). "
                    f"Use /skip or /clear first."
                )
            return None

        # 4. Add to in-memory queue
        position = await gq.add(song)

        # 5. Persist to database
        async with get_session() as session:
            db_item = await queue_crud.add_to_queue(
                session=session,
                chat_id=chat_id,
                title=song.title,
                url=song.url,
                duration=song.duration,
                requested_by_id=requested_by_id,
                requested_by_name=requested_by_name,
                video_id=song.video_id,
                thumbnail=song.thumbnail,
                uploader=song.uploader,
            )
            db_item_id = db_item.id if db_item else None

        # 6. Update status message
        if message:
            if position == 1 and not self.engine.is_active(chat_id):
                await status_msg.edit(  # type: ignore
                    f"✅ <b>{song.title}</b>\n\nDownloading and preparing playback..."
                )
            else:
                await status_msg.edit(  # type: ignore
                    f"✅ Added to queue at position <b>#{position}</b>\n\n"
                    f"🎵 <b>{song.title}</b>\n"
                    f"⏱ {format_duration(song.duration)}"
                )

        # 7. Start playback if not already playing
        if not self.engine.is_active(chat_id):
            asyncio.create_task(self._start_playback(chat_id))

        return {
            "title": song.title,
            "url": song.url,
            "duration": song.duration,
            "position": position,
            "thumbnail": song.thumbnail,
            "uploader": song.uploader,
        }

    async def queue_playlist(
        self,
        chat_id: int,
        url: str,
        requested_by_id: int,
        requested_by_name: str,
        message: Optional[Message] = None,
    ) -> int:
        """
        Queue all songs from a YouTube playlist.

        Returns the number of songs added.
        """
        if message:
            status_msg = await message.reply("📋 Loading playlist...")

        items = await downloader.resolve_playlist(url)
        if not items:
            if message:
                await status_msg.edit("❌ Could not load the playlist.")  # type: ignore
            return 0

        gq = await queue_manager.get(chat_id)
        count = 0
        for song in items[:settings.max_queue_size or len(items)]:
            await gq.add(song)
            async with get_session() as session:
                await queue_crud.add_to_queue(
                    session=session,
                    chat_id=chat_id,
                    title=song.title,
                    url=song.url,
                    duration=song.duration,
                    requested_by_id=requested_by_id,
                    requested_by_name=requested_by_name,
                    video_id=song.video_id,
                    thumbnail=song.thumbnail,
                    uploader=song.uploader,
                )
            count += 1

        if message:
            await status_msg.edit(  # type: ignore
                f"✅ Added <b>{count}</b> songs from playlist to queue."
            )

        if not self.engine.is_active(chat_id) and count > 0:
            asyncio.create_task(self._start_playback(chat_id))

        return count

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    async def _start_playback(self, chat_id: int) -> None:
        """
        Internal: start playing the next song in queue.

        Called as a background task when playback needs to begin.
        """
        gq = await queue_manager.get(chat_id)
        song = await gq.next()
        if song is None:
            return

        await self.play_next(chat_id, song)

    async def play_next(self, chat_id: int, song: SongInfo) -> None:
        """
        Download and play the given song.

        This is also called by VoiceEngine.on_stream_end to advance the queue.
        """
        logger.info("[chat_id={}] Downloading: {}", chat_id, song.title)

        # Update DB status
        async with get_session() as session:
            current_db = await queue_crud.get_currently_playing(session, chat_id)
            if current_db:
                # Record previous song to history
                await history_crud.record_played(session, chat_id, current_db)
                await queue_crud.set_status(session, current_db.id, QueueStatus.DONE)

            # Find the next DB item and mark as downloading
            next_db = await queue_crud.get_next_in_queue(session, chat_id)
            if next_db:
                await queue_crud.set_status(session, next_db.id, QueueStatus.DOWNLOADING)

        # Download the audio file
        file_path = await downloader.download(song)

        if file_path is None:
            logger.error("[chat_id={}] Download failed for: {}", chat_id, song.title)
            # Try next song
            gq = await queue_manager.get(chat_id)
            next_song = await gq.next()
            if next_song:
                await self.play_next(chat_id, next_song)
            return

        song.file_path = file_path

        # Update DB with file path and mark as playing
        async with get_session() as session:
            next_db = await queue_crud.get_next_in_queue(session, chat_id)
            if next_db:
                await queue_crud.update_file_path(session, next_db.id, file_path)
                await queue_crud.set_status(session, next_db.id, QueueStatus.PLAYING)

        # Play via voice engine
        success = await self.engine.play(chat_id, song, file_path)

        if not success:
            logger.error("[chat_id={}] Voice engine failed to play: {}", chat_id, song.title)
            # Clean up and try next
            downloader.cleanup(file_path)
            gq = await queue_manager.get(chat_id)
            next_song = await gq.next()
            if next_song:
                await self.play_next(chat_id, next_song)
            return

        # Schedule cleanup after song duration + buffer
        cleanup_delay = max(song.duration + 30, 60)
        asyncio.create_task(self._delayed_cleanup(file_path, cleanup_delay))

    async def skip(self, chat_id: int) -> Optional[SongInfo]:
        """Skip the current song and start the next one."""
        gq = await queue_manager.get(chat_id)

        # Get the currently playing item for cleanup
        current_state = await gq.get_current()
        if current_state and current_state.song.file_path:
            downloader.cleanup(current_state.song.file_path)

        next_song = await gq.skip()
        if next_song:
            asyncio.create_task(self.play_next(chat_id, next_song))
        else:
            await self.engine.leave(chat_id)

        return next_song

    async def stop(self, chat_id: int) -> bool:
        """Stop playback, clear queue, and leave voice chat."""
        gq = await queue_manager.get(chat_id)
        current_state = await gq.get_current()
        if current_state and current_state.song.file_path:
            downloader.cleanup(current_state.song.file_path)

        await gq.clear()
        await gq.mark_current_done()

        async with get_session() as session:
            await queue_crud.clear_queue(session, chat_id)

        return await self.engine.stop(chat_id)

    async def pause(self, chat_id: int) -> bool:
        """Pause playback."""
        return await self.engine.pause(chat_id)

    async def resume(self, chat_id: int) -> bool:
        """Resume paused playback."""
        return await self.engine.resume(chat_id)

    async def set_volume(self, chat_id: int, volume: int) -> bool:
        """Set playback volume."""
        success = await self.engine.set_volume(chat_id, volume)
        if success:
            async with get_session() as session:
                await group_crud.update_group_setting(
                    session, chat_id, volume=volume
                )
        return success

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    async def _delayed_cleanup(file_path: str, delay: float) -> None:
        """Delete a temp file after a delay."""
        await asyncio.sleep(delay)
        downloader.cleanup(file_path)


# Module-level singleton (fully initialized after voice engine is started)
music_service = MusicService()
