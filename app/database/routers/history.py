"""
CRUD operations for HistoryItem model.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.groups import Group
from app.database.models.history import HistoryItem
from app.database.models.queue import QueueItem


async def _get_group_db_id(session: AsyncSession, chat_id: int) -> Optional[int]:
    """Resolve Telegram chat_id to the Group.id primary key."""
    result = await session.execute(
        select(Group.id).where(Group.chat_id == chat_id)
    )
    return result.scalar_one_or_none()


async def record_played(
    session: AsyncSession,
    chat_id: int,
    queue_item: QueueItem,
) -> HistoryItem:
    """
    Move a finished QueueItem into history.

    Creates a HistoryItem from the QueueItem's data.
    """
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        raise ValueError(f"Group with chat_id={chat_id} not found")

    history = HistoryItem(
        group_id=group_id,
        title=queue_item.title,
        url=queue_item.url,
        video_id=queue_item.video_id,
        thumbnail=queue_item.thumbnail,
        duration=queue_item.duration,
        uploader=queue_item.uploader,
        requested_by_id=queue_item.requested_by_id,
        requested_by_name=queue_item.requested_by_name,
    )
    session.add(history)
    await session.flush()
    return history


async def get_recent_history(
    session: AsyncSession, chat_id: int, limit: int = 10
) -> list[HistoryItem]:
    """Return the most recently played songs for a group."""
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return []
    result = await session.execute(
        select(HistoryItem)
        .where(HistoryItem.group_id == group_id)
        .order_by(HistoryItem.played_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_total_played(session: AsyncSession, chat_id: int) -> int:
    """Return the total number of songs ever played in a group."""
    from sqlalchemy import func
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return 0
    result = await session.execute(
        select(func.count()).select_from(HistoryItem).where(
            HistoryItem.group_id == group_id
        )
    )
    return result.scalar_one()
