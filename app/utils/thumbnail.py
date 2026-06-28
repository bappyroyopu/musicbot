"""
Thumbnail download and processing utility.

Downloads YouTube thumbnails, resizes them for Telegram,
and saves to the temp directory.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Optional

import aiohttp
from loguru import logger

from app.config import settings


async def download_thumbnail(
    url: str,
    video_id: Optional[str] = None,
) -> Optional[Path]:
    """
    Download a thumbnail from a URL and save it to the temp directory.

    Args:
        url: Thumbnail URL.
        video_id: Optional video ID used for the filename.

    Returns:
        Path to the downloaded thumbnail, or None on failure.
    """
    if not url:
        return None

    # Derive a stable filename
    name = video_id or hashlib.md5(url.encode()).hexdigest()[:12]
    dest = settings.temp_path / f"thumb_{name}.jpg"

    # Return cached if already downloaded
    if dest.exists():
        return dest

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()

        import aiofiles
        async with aiofiles.open(dest, "wb") as f:
            await f.write(data)
        logger.debug("Thumbnail downloaded: {}", dest)
        return dest

    except Exception as exc:
        logger.warning("Failed to download thumbnail {}: {}", url, exc)
        return None


async def get_best_thumbnail_url(video_id: str) -> str:
    """
    Return the best available YouTube thumbnail URL for a video.

    Tries maxresdefault → hqdefault → mqdefault in order.
    """
    base = f"https://i.ytimg.com/vi/{video_id}"
    candidates = [
        f"{base}/maxresdefault.jpg",
        f"{base}/hqdefault.jpg",
        f"{base}/mqdefault.jpg",
        f"{base}/default.jpg",
    ]

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10)
    ) as session:
        for url in candidates:
            try:
                async with session.head(url) as resp:
                    if resp.status == 200:
                        return url
            except Exception:
                continue

    return candidates[-1]  # Fallback to default
