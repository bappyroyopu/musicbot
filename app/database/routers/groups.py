"""
CRUD operations for Group model.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.groups import Group


async def get_group(session: AsyncSession, chat_id: int) -> Optional[Group]:
    """Fetch a group by Telegram chat ID."""
    result = await session.execute(select(Group).where(Group.chat_id == chat_id))
    return result.scalar_one_or_none()


async def get_or_create_group(
    session: AsyncSession,
    chat_id: int,
    title: str,
    username: Optional[str] = None,
) -> tuple[Group, bool]:
    """
    Fetch an existing group or create a new one.

    Returns:
        Tuple of (group, created).
    """
    from app.config import settings

    group = await get_group(session, chat_id)
    if group is not None:
        group.title = title
        group.username = username
        return group, False

    group = Group(
        chat_id=chat_id,
        title=title,
        username=username,
        volume=settings.default_volume,
        max_queue=settings.max_queue_size,
    )
    session.add(group)
    await session.flush()
    return group, True


async def update_group_setting(
    session: AsyncSession,
    chat_id: int,
    **kwargs: object,
) -> bool:
    """
    Update one or more Group columns by chat_id.

    Usage::
        await update_group_setting(session, chat_id, volume=80, loop=True)
    """
    group = await get_group(session, chat_id)
    if group is None:
        return False
    for key, value in kwargs.items():
        if hasattr(group, key):
            setattr(group, key, value)
    return True


async def get_group_volume(session: AsyncSession, chat_id: int) -> int:
    """Return the configured volume for a group (default 100)."""
    result = await session.execute(
        select(Group.volume).where(Group.chat_id == chat_id)
    )
    return result.scalar_one_or_none() or 100


async def get_total_groups(session: AsyncSession) -> int:
    """Return the total number of registered groups."""
    from sqlalchemy import func
    result = await session.execute(select(func.count()).select_from(Group))
    return result.scalar_one()


async def get_all_active_groups(session: AsyncSession) -> list[Group]:
    """Return all groups where the bot is active."""
    result = await session.execute(
        select(Group).where(Group.is_active.is_(True))
    )
    return list(result.scalars().all())
