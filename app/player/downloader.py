"""
Audio downloader using yt-dlp.

Downloads the best available audio from YouTube (or any yt-dlp supported
source), converts to raw PCM/S16LE via FFmpeg for PyTgCalls streaming,
and stores files in the temporary directory.

All downloads are async — yt-dlp runs in a thread pool executor.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yt_dlp
from loguru import logger

from app.config import settings
from app.utils.validators import is_url, is_youtube_playlist


@dataclass
class SongInfo:
    """Metadata for a downloaded or resolved song."""

    title: str
    url: str                         # Original webpage URL
    stream_url: str = ""             # Direct audio stream URL (for piping)
    video_id: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: int = 0                # Seconds
    uploader: Optional[str] = None
    file_path: Optional[str] = None  # Local path after download
    is_playlist: bool = False
    playlist_items: list["SongInfo"] = field(default_factory=list)


class Downloader:
    """
    Async audio downloader and metadata resolver.

    Wraps yt-dlp in asyncio.run_in_executor to keep the event loop free.
    """

    def __init__(self) -> None:
        self._temp_dir = settings.temp_path
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._executor = None  # Use default ThreadPoolExecutor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def resolve(self, query: str) -> Optional[SongInfo]:
        """
        Resolve a search query or URL to song metadata WITHOUT downloading.

        - If query is a URL, extract metadata from the page.
        - If query is a search term, search YouTube and return the top result.

        Returns SongInfo on success, None on failure.
        """
        loop = asyncio.get_event_loop()
        try:
            info = await loop.run_in_executor(
                self._executor, self._sync_resolve, query
            )
            return info
        except Exception as exc:
            logger.error("resolve() failed for {!r}: {}", query, exc)
            return None

    async def download(self, info: SongInfo) -> Optional[str]:
        """
        Download the audio for the given SongInfo to a temp file.

        Returns the absolute path to the downloaded .mp3 file,
        or None on failure.
        """
        loop = asyncio.get_event_loop()
        try:
            path = await loop.run_in_executor(
                self._executor, self._sync_download, info
            )
            return path
        except Exception as exc:
            logger.error("download() failed for {!r}: {}", info.title, exc)
            return None

    async def search_youtube(
        self, query: str, max_results: int = 8
    ) -> list[SongInfo]:
        """
        Search YouTube for the query and return multiple results.

        Used by /search command.
        """
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                self._executor, self._sync_search, query, max_results
            )
            return results
        except Exception as exc:
            logger.error("search_youtube() failed for {!r}: {}", query, exc)
            return []

    async def resolve_playlist(self, url: str) -> list[SongInfo]:
        """
        Extract all entries from a YouTube playlist.

        Returns a list of SongInfo objects (metadata only, not downloaded).
        """
        loop = asyncio.get_event_loop()
        try:
            items = await loop.run_in_executor(
                self._executor, self._sync_playlist, url
            )
            return items
        except Exception as exc:
            logger.error("resolve_playlist() failed for {}: {}", url, exc)
            return []

    @staticmethod
    def cleanup(file_path: Optional[str]) -> None:
        """Delete a temporary audio file if it exists."""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.debug("Deleted temp file: {}", file_path)
            except OSError as exc:
                logger.warning("Could not delete {}: {}", file_path, exc)

    # ------------------------------------------------------------------
    # Synchronous implementations (run in executor)
    # ------------------------------------------------------------------

    def _base_opts(self) -> dict[str, Any]:
        """Common yt-dlp options."""
        return {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "noplaylist": True,
            "age_limit": None,
            "geo_bypass": True,
        }

    def _sync_resolve(self, query: str) -> Optional[SongInfo]:
        """Synchronous metadata extraction (called in executor)."""
        is_search = not is_url(query)
        url = f"ytsearch1:{query}" if is_search else query

        opts = {
            **self._base_opts(),
            "format": "bestaudio/best",
            "noplaylist": not is_youtube_playlist(query),
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            raw = ydl.extract_info(url, download=False)

        if raw is None:
            return None

        # Handle search results wrapping
        if "entries" in raw:
            entries = [e for e in raw["entries"] if e]
            if not entries:
                return None
            raw = entries[0]

        return self._build_song_info(raw)

    def _sync_download(self, info: SongInfo) -> Optional[str]:
        """Synchronous download (called in executor)."""
        uid = uuid.uuid4().hex[:10]
        output_tmpl = str(self._temp_dir / f"audio_{uid}.%(ext)s")
        final_path = str(self._temp_dir / f"audio_{uid}.mp3")

        opts = {
            **self._base_opts(),
            "format": "bestaudio/best",
            "outtmpl": output_tmpl,
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                },
            ],
            "ffmpeg_location": self._find_ffmpeg(),
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([info.url])

        if not os.path.exists(final_path):
            # Try to find any file matching the pattern
            for f in self._temp_dir.glob(f"audio_{uid}.*"):
                return str(f)
            return None

        return final_path

    def _sync_search(self, query: str, max_results: int) -> list[SongInfo]:
        """Synchronous YouTube search (called in executor)."""
        url = f"ytsearch{max_results}:{query}"
        opts = {
            **self._base_opts(),
            "format": "bestaudio/best",
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            raw = ydl.extract_info(url, download=False)

        if raw is None or "entries" not in raw:
            return []

        results: list[SongInfo] = []
        for entry in raw["entries"]:
            if entry:
                results.append(self._build_song_info(entry))
        return results

    def _sync_playlist(self, url: str) -> list[SongInfo]:
        """Synchronous playlist extraction (called in executor)."""
        opts = {
            **self._base_opts(),
            "extract_flat": True,
            "noplaylist": False,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            raw = ydl.extract_info(url, download=False)

        if raw is None or "entries" not in raw:
            return []

        items: list[SongInfo] = []
        for entry in raw["entries"]:
            if entry:
                video_url = entry.get("url") or entry.get("webpage_url", "")
                if not video_url.startswith("http"):
                    video_url = f"https://www.youtube.com/watch?v={video_url}"
                item = SongInfo(
                    title=entry.get("title", "Unknown"),
                    url=video_url,
                    video_id=entry.get("id"),
                    duration=int(entry.get("duration") or 0),
                    uploader=entry.get("uploader"),
                    thumbnail=entry.get("thumbnail"),
                )
                items.append(item)
        return items

    @staticmethod
    def _build_song_info(raw: dict) -> SongInfo:
        """Convert a yt-dlp info dict to a SongInfo object."""
        video_id = raw.get("id")
        thumbnail = raw.get("thumbnail")

        # Pick best thumbnail
        if not thumbnail and raw.get("thumbnails"):
            thumbs = sorted(
                raw["thumbnails"],
                key=lambda t: t.get("width", 0) or 0,
                reverse=True,
            )
            thumbnail = thumbs[0].get("url") if thumbs else None

        return SongInfo(
            title=raw.get("title", "Unknown"),
            url=raw.get("webpage_url") or raw.get("url", ""),
            video_id=video_id,
            thumbnail=thumbnail,
            duration=int(raw.get("duration") or 0),
            uploader=raw.get("uploader") or raw.get("channel"),
        )

    @staticmethod
    def _find_ffmpeg() -> Optional[str]:
        """Find the FFmpeg binary path."""
        import shutil
        return shutil.which("ffmpeg")


# Module-level singleton
downloader = Downloader()
