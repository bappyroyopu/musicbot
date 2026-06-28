"""
CRUD operations for Playlist and PlaylistItem models.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.playlists import Playlist, PlaylistItem
from app.database.models.users import User


async def _get_user_db_id(session: AsyncSession, tg_id: int) -> Optional[int]:
    """Resolve Telegram user ID to the User.id primary key."""
    result = await session.execute(select(User.id).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()


async def create_playlist(
    session: AsyncSession,
    tg_id: int,
    name: str,
    description: Optional[str] = None,
) -> Optional[Playlist]:
    """Create a new playlist for a user. Returns None if user not found."""
    user_id = await _get_user_db_id(session, tg_id)
    if user_id is None:
        return None
    playlist = Playlist(user_id=user_id, name=name, description=description)
    session.add(playlist)
    await session.flush()
    return playlist


async def get_user_playlists(
    session: AsyncSession, tg_id: int
) -> list[Playlist]:
    """Return all playlists owned by a user."""
    user_id = await _get_user_db_id(session, tg_id)
    if user_id is None:
        return []
    result = await session.execute(
        select(Playlist)
        .where(Playlist.user_id == user_id)
        .order_by(Playlist.name)
    )
    return list(result.scalars().all())


async def get_playlist_with_items(
    session: AsyncSession, playlist_id: int
) -> Optional[Playlist]:
    """Return a playlist with all its items eagerly loaded."""
    result = await session.execute(
        select(Playlist)
        .where(Playlist.id == playlist_id)
        .options(selectinload(Playlist.items))
    )
    return result.scalar_one_or_none()


async def add_item_to_playlist(
    session: AsyncSession,
    playlist_id: int,
    title: str,
    url: str,
    duration: int,
    video_id: Optional[str] = None,
    thumbnail: Optional[str] = None,
    uploader: Optional[str] = None,
) -> Optional[PlaylistItem]:
    """Add a song to an existing playlist."""
    # Get current max position
    result = await session.execute(
        select(func.max(PlaylistItem.position)).where(
            PlaylistItem.playlist_id == playlist_id
        )
    )
    max_pos: Optional[int] = result.scalar_one_or_none()
    next_pos = (max_pos or 0) + 1

    item = PlaylistItem(
        playlist_id=playlist_id,
        position=next_pos,
        title=title,
        url=url,
        video_id=video_id,
        thumbnail=thumbnail,
        duration=duration,
        uploader=uploader,
    )
    session.add(item)
    await session.flush()
    return item


async def delete_playlist(session: AsyncSession, playlist_id: int) -> bool:
    """Delete a playlist and all its items. Returns True if found."""
    playlist = await session.get(Playlist, playlist_id)
    if playlist is None:
        return False
    await session.delete(playlist)
    return True


async def rename_playlist(
    session: AsyncSession, playlist_id: int, new_name: str
) -> bool:
    """Rename a playlist. Returns True if found."""
    playlist = await session.get(Playlist, playlist_id)
    if playlist is None:
        return False
    playlist.name = new_name
    return True
