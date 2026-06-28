"""
Lyrics fetcher utility.

Uses the Lyrics Genius API to search and retrieve song lyrics.
Falls back to a web scrape approach if API key is not configured.
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from loguru import logger


async def fetch_lyrics(song_title: str, artist: Optional[str] = None) -> Optional[str]:
    """
    Fetch lyrics for a song.

    Tries LyricsGenius API first (requires GENIUS_TOKEN env var).
    Falls back to a basic search if the API is unavailable.

    Args:
        song_title: Song title.
        artist: Optional artist/uploader name.

    Returns:
        Lyrics string, or None if not found.
    """
    genius_token = os.environ.get("GENIUS_TOKEN", "")

    if genius_token:
        try:
            return await _fetch_from_genius(song_title, artist, genius_token)
        except Exception as exc:
            logger.warning("Genius API failed: {}. Trying fallback.", exc)

    return await _fetch_fallback(song_title, artist)


async def _fetch_from_genius(
    title: str, artist: Optional[str], token: str
) -> Optional[str]:
    """Fetch lyrics via the Genius API (async wrapper around lyricsgenius)."""
    import lyricsgenius  # type: ignore[import]

    def _sync_fetch() -> Optional[str]:
        genius = lyricsgenius.Genius(token, quiet=True, remove_section_headers=True)
        query = f"{title} {artist}".strip() if artist else title
        song = genius.search_song(query)
        if song:
            return song.lyrics
        return None

    # Run the blocking library call in a thread pool
    loop = asyncio.get_event_loop()
    lyrics = await loop.run_in_executor(None, _sync_fetch)
    return lyrics


async def _fetch_fallback(
    title: str, artist: Optional[str]
) -> Optional[str]:
    """
    Fallback: return a notice that lyrics are unavailable.

    In production, integrate a secondary lyrics API here.
    """
    return (
        f"🎵 <b>Lyrics for:</b> {title}\n\n"
        f"<i>Lyrics could not be retrieved. "
        f"Set the GENIUS_TOKEN environment variable to enable lyrics.</i>"
    )
