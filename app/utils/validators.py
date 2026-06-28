"""
Input validation utilities.

Provides URL detection, YouTube URL parsing, and query sanitization.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

# YouTube URL patterns
_YT_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([\w-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtu\.be/([\w-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([\w-]+)"),
    re.compile(r"(?:https?://)?music\.youtube\.com/watch\?v=([\w-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([\w-]{11})"),
]

_URL_PATTERN = re.compile(
    r"https?://[^\s]+"
)


def is_url(text: str) -> bool:
    """Return True if the text looks like a URL."""
    return bool(_URL_PATTERN.match(text.strip()))


def is_youtube_url(text: str) -> bool:
    """Return True if the URL is a recognized YouTube URL."""
    text = text.strip()
    for pattern in _YT_PATTERNS:
        if pattern.search(text):
            return True
    # Also check domain
    try:
        parsed = urlparse(text)
        return parsed.netloc.replace("www.", "") in (
            "youtube.com", "youtu.be", "music.youtube.com"
        )
    except Exception:
        return False


def is_youtube_playlist(text: str) -> bool:
    """Return True if the URL is a YouTube playlist."""
    return "playlist?list=" in text or "&list=" in text


def extract_video_id(url: str) -> Optional[str]:
    """Extract the YouTube video ID from a URL, or None."""
    for pattern in _YT_PATTERNS[:2]:  # Only watch/short patterns
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def sanitize_query(query: str) -> str:
    """
    Clean a search query — strip leading/trailing whitespace,
    remove control characters, and limit length.
    """
    query = re.sub(r"[\x00-\x1f\x7f]", "", query)
    query = " ".join(query.split())
    return query[:200]


def is_valid_volume(value: int) -> bool:
    """Return True if the volume is in the valid range [1, 200]."""
    return 1 <= value <= 200
