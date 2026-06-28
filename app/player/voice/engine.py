"""
PyTgCalls voice chat streaming engine.

Manages voice chat sessions for multiple groups simultaneously.
Handles joining, leaving, playback, pause/resume, volume,
auto-reconnect, and auto-leave after inactivity.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from loguru import logger
from pyrogram import Client
from pytgcalls import PyTgCalls  # type: ignore[import]
from pytgcalls.types import (  # type: ignore[import]
    AudioPiped,
    AudioParameters,
)
from pytgcalls.exceptions import (  # type: ignore[import]
    GroupCallNotFound,
    NoActiveGroupCall,
    NotInGroupCallError,
    AlreadyJoinedError,
)

from app.config import settings
from app.player.downloader import SongInfo, downloader
from app.player.queue import GroupQueue, queue_manager


class VoiceEngine:
    """
    Wraps PyTgCalls to manage multi-group voice chat playback.

    One VoiceEngine instance is shared across the entire application.
    It owns a single PyTgCalls client bound to the assistant Pyrogram client.
    """

    def __init__(self, assistant: Client) -> None:
        self._assistant = assistant
        self._calls = PyTgCalls(assistant)
        self._active: dict[int, bool] = {}          # chat_id -> is_playing
        self._inactivity_tasks: dict[int, asyncio.Task] = {}
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register PyTgCalls event handlers with robust error boundaries."""

        @self._calls.on_stream_end()
        async def on_stream_end(client: PyTgCalls, update) -> None:
            """Called when a stream ends (song finished)."""
            try:
                chat_id = getattr(update, "chat_id", None)
                if chat_id is None:
                    return
                logger.info("[chat_id={}] Stream ended", chat_id)
                await self._handle_stream_end(chat_id)
            except Exception as e:
                logger.exception("Error in PyTgCalls on_stream_end handler: {}", e)

        @self._calls.on_closed_voice_chat()
        async def on_closed(client: PyTgCalls, update) -> None:
            """Called when the voice chat is closed externally."""
            try:
                chat_id = getattr(update, "chat_id", None)
                if chat_id is None:
                    return
                logger.warning("[chat_id={}] Voice chat closed externally", chat_id)
                await self._handle_vc_closed(chat_id)
            except Exception as e:
                logger.exception("Error in PyTgCalls on_closed handler: {}", e)

        @self._calls.on_kicked()
        async def on_kicked(client: PyTgCalls, update) -> None:
            """Called when the assistant is kicked from VC."""
            try:
                chat_id = getattr(update, "chat_id", None)
                if chat_id is None:
                    return
                logger.warning("[chat_id={}] Assistant kicked from VC", chat_id)
                await self._handle_vc_closed(chat_id)
            except Exception as e:
                logger.exception("Error in PyTgCalls on_kicked handler: {}", e)

        @self._calls.on_left()
        async def on_left(client: PyTgCalls, update) -> None:
            """Called when the assistant leaves VC."""
            try:
                chat_id = getattr(update, "chat_id", None)
                if chat_id is None:
                    return
                self._active.pop(chat_id, None)
                logger.info("[chat_id={}] Left voice chat", chat_id)
            except Exception as e:
                logger.exception("Error in PyTgCalls on_left handler: {}", e)

    async def start(self) -> None:
        """Start the PyTgCalls engine."""
        await self._calls.start()
        logger.info("PyTgCalls voice engine started")

    async def stop(self) -> None:
        """Stop all active calls and the engine."""
        for chat_id in list(self._active.keys()):
            await self.leave(chat_id)
        logger.info("PyTgCalls voice engine stopped")

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    async def play(self, chat_id: int, song: SongInfo, file_path: str) -> bool:
        """
        Start or resume playing a song in the group's voice chat.

        Args:
            chat_id: Telegram chat ID.
            song: SongInfo metadata.
            file_path: Path to the downloaded audio file.

        Returns:
            True on success, False on failure.
        """
        try:
            stream = AudioPiped(
                file_path,
                audio_parameters=AudioParameters(
                    bitrate=128,
                ),
            )

            if chat_id in self._active:
                # Already in call — change the stream
                await self._calls.change_stream(chat_id, stream)
            else:
                # Join the voice chat
                await self._calls.join_group_call(
                    chat_id,
                    stream,
                    stream_type=stream,
                )

            self._active[chat_id] = True
            self._cancel_inactivity_task(chat_id)
            logger.info("[chat_id={}] Playing: {}", chat_id, song.title)
            return True

        except AlreadyJoinedError:
            # Already in VC — just change stream
            try:
                stream = AudioPiped(file_path, audio_parameters=AudioParameters(bitrate=128))
                await self._calls.change_stream(chat_id, stream)
                self._active[chat_id] = True
                return True
            except Exception as exc:
                logger.error("[chat_id={}] AlreadyJoinedError recovery failed: {}", chat_id, exc)
                return False

        except (NoActiveGroupCall, GroupCallNotFound) as exc:
            logger.warning("[chat_id={}] No active voice chat: {}", chat_id, exc)
            return False

        except Exception as exc:
            logger.error("[chat_id={}] play() error: {}", chat_id, exc)
            return False

    async def pause(self, chat_id: int) -> bool:
        """Pause playback in the group's voice chat."""
        try:
            await self._calls.pause_stream(chat_id)
            gq = await queue_manager.get(chat_id)
            await gq.pause()
            logger.info("[chat_id={}] Paused", chat_id)
            return True
        except NotInGroupCallError:
            return False
        except Exception as exc:
            logger.error("[chat_id={}] pause() error: {}", chat_id, exc)
            return False

    async def resume(self, chat_id: int) -> bool:
        """Resume paused playback."""
        try:
            await self._calls.resume_stream(chat_id)
            gq = await queue_manager.get(chat_id)
            await gq.resume()
            logger.info("[chat_id={}] Resumed", chat_id)
            return True
        except NotInGroupCallError:
            return False
        except Exception as exc:
            logger.error("[chat_id={}] resume() error: {}", chat_id, exc)
            return False

    async def stop(self, chat_id: int) -> bool:
        """Stop playback and clear the queue."""
        try:
            gq = await queue_manager.get(chat_id)
            await gq.clear()
            await gq.mark_current_done()
            await self.leave(chat_id)
            return True
        except Exception as exc:
            logger.error("[chat_id={}] stop() error: {}", chat_id, exc)
            return False

    async def leave(self, chat_id: int) -> bool:
        """Leave the voice chat."""
        try:
            await self._calls.leave_group_call(chat_id)
        except Exception:
            pass
        self._active.pop(chat_id, None)
        self._cancel_inactivity_task(chat_id)
        logger.info("[chat_id={}] Left voice chat", chat_id)
        return True

    async def set_volume(self, chat_id: int, volume: int) -> bool:
        """Set playback volume (1–200)."""
        try:
            await self._calls.change_volume_call(chat_id, volume)
            gq = await queue_manager.get(chat_id)
            await gq.set_volume(volume)
            return True
        except Exception as exc:
            logger.error("[chat_id={}] set_volume() error: {}", chat_id, exc)
            return False

    def is_active(self, chat_id: int) -> bool:
        """True if the bot is currently in a voice chat for this group."""
        return chat_id in self._active

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    async def _handle_stream_end(self, chat_id: int) -> None:
        """
        Handle a finished stream: play the next song or start inactivity timer.

        Called by the PyTgCalls on_stream_end handler.
        """
        from app.services.music_service import music_service

        gq = await queue_manager.get(chat_id)
        await gq.mark_current_done()

        next_song = await gq.next()
        if next_song is None:
            logger.info("[chat_id={}] Queue exhausted", chat_id)
            self._start_inactivity_task(chat_id)
            return

        # Download and play next song
        asyncio.create_task(music_service.play_next(chat_id, next_song))

    async def _handle_vc_closed(self, chat_id: int) -> None:
        """Handle VC closure — clean up state."""
        self._active.pop(chat_id, None)
        gq = await queue_manager.get(chat_id)
        await gq.clear()
        await gq.mark_current_done()

    def _start_inactivity_task(self, chat_id: int) -> None:
        """Start a timer that leaves VC after AUTO_LEAVE_TIMEOUT seconds."""
        if settings.auto_leave_timeout <= 0:
            return
        self._cancel_inactivity_task(chat_id)
        self._inactivity_tasks[chat_id] = asyncio.create_task(
            self._inactivity_leave(chat_id)
        )

    def _cancel_inactivity_task(self, chat_id: int) -> None:
        """Cancel any existing inactivity timer for a group."""
        task = self._inactivity_tasks.pop(chat_id, None)
        if task and not task.done():
            task.cancel()

    async def _inactivity_leave(self, chat_id: int) -> None:
        """Wait for the inactivity timeout then leave VC."""
        try:
            await asyncio.sleep(settings.auto_leave_timeout)
            gq = await queue_manager.get(chat_id)
            if await gq.is_empty():
                logger.info(
                    "[chat_id={}] Leaving due to {} s inactivity",
                    chat_id,
                    settings.auto_leave_timeout,
                )
                await self.leave(chat_id)
        except asyncio.CancelledError:
            pass


# Module-level singleton (initialized in main.py after clients start)
voice_engine: Optional[VoiceEngine] = None


def init_voice_engine(assistant: Client) -> VoiceEngine:
    """Create and store the global VoiceEngine singleton."""
    global voice_engine
    voice_engine = VoiceEngine(assistant)
    return voice_engine
