"""
CRUD operations for QueueItem model.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.groups import Group
from app.database.models.queue import QueueItem, QueueStatus


async def _get_group_db_id(session: AsyncSession, chat_id: int) -> Optional[int]:
    """Resolve Telegram chat_id to the Group.id primary key."""
    result = await session.execute(
        select(Group.id).where(Group.chat_id == chat_id)
    )
    return result.scalar_one_or_none()


async def add_to_queue(
    session: AsyncSession,
    chat_id: int,
    title: str,
    url: str,
    duration: int,
    requested_by_id: int,
    requested_by_name: str,
    video_id: Optional[str] = None,
    thumbnail: Optional[str] = None,
    uploader: Optional[str] = None,
) -> Optional[QueueItem]:
    """
    Add a song to the group's queue.

    Returns the created QueueItem, or None if the group doesn't exist.
    """
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return None

    # Determine the next position
    result = await session.execute(
        select(func.max(QueueItem.position)).where(
            QueueItem.group_id == group_id,
            QueueItem.status.in_([QueueStatus.PENDING, QueueStatus.DOWNLOADING]),
        )
    )
    max_pos: Optional[int] = result.scalar_one_or_none()
    next_pos = (max_pos or 0) + 1

    item = QueueItem(
        group_id=group_id,
        position=next_pos,
        title=title,
        url=url,
        video_id=video_id,
        thumbnail=thumbnail,
        duration=duration,
        uploader=uploader,
        requested_by_id=requested_by_id,
        requested_by_name=requested_by_name,
        status=QueueStatus.PENDING,
    )
    session.add(item)
    await session.flush()
    return item


async def get_queue(session: AsyncSession, chat_id: int) -> list[QueueItem]:
    """Return all pending/downloading queue items ordered by position."""
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return []
    result = await session.execute(
        select(QueueItem)
        .where(
            QueueItem.group_id == group_id,
            QueueItem.status.in_([QueueStatus.PENDING, QueueStatus.DOWNLOADING]),
        )
        .order_by(QueueItem.position)
    )
    return list(result.scalars().all())


async def get_next_in_queue(
    session: AsyncSession, chat_id: int
) -> Optional[QueueItem]:
    """Return the first pending item in queue (lowest position)."""
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return None
    result = await session.execute(
        select(QueueItem)
        .where(
            QueueItem.group_id == group_id,
            QueueItem.status == QueueStatus.PENDING,
        )
        .order_by(QueueItem.position)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_currently_playing(
    session: AsyncSession, chat_id: int
) -> Optional[QueueItem]:
    """Return the item currently marked as PLAYING."""
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return None
    result = await session.execute(
        select(QueueItem).where(
            QueueItem.group_id == group_id,
            QueueItem.status == QueueStatus.PLAYING,
        )
    )
    return result.scalar_one_or_none()


async def set_status(
    session: AsyncSession, item_id: int, status: QueueStatus
) -> None:
    """Update the status of a specific queue item."""
    from datetime import datetime

    extra: dict = {"status": status}
    if status == QueueStatus.PLAYING:
        extra["started_at"] = datetime.utcnow()
    await session.execute(
        update(QueueItem).where(QueueItem.id == item_id).values(**extra)
    )


async def update_file_path(
    session: AsyncSession, item_id: int, file_path: str
) -> None:
    """Store the local file path for a downloaded queue item."""
    await session.execute(
        update(QueueItem)
        .where(QueueItem.id == item_id)
        .values(file_path=file_path)
    )


async def clear_queue(session: AsyncSession, chat_id: int) -> int:
    """
    Delete all pending items from a group's queue.

    Returns the number of deleted items.
    """
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return 0
    result = await session.execute(
        delete(QueueItem).where(
            QueueItem.group_id == group_id,
            QueueItem.status.in_([QueueStatus.PENDING, QueueStatus.DOWNLOADING]),
        )
    )
    return result.rowcount


async def get_queue_size(session: AsyncSession, chat_id: int) -> int:
    """Return the number of songs currently in the queue."""
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return 0
    result = await session.execute(
        select(func.count()).select_from(QueueItem).where(
            QueueItem.group_id == group_id,
            QueueItem.status.in_([QueueStatus.PENDING, QueueStatus.DOWNLOADING]),
        )
    )
    return result.scalar_one()
