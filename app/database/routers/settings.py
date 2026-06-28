"""
CRUD operations for GroupSetting model.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.groups import Group
from app.database.models.settings_model import GroupSetting


async def _get_group_db_id(session: AsyncSession, chat_id: int) -> Optional[int]:
    """Resolve Telegram chat_id to the Group.id primary key."""
    result = await session.execute(
        select(Group.id).where(Group.chat_id == chat_id)
    )
    return result.scalar_one_or_none()


async def get_setting(
    session: AsyncSession, chat_id: int, key: str
) -> Optional[str]:
    """
    Return a single setting value for a group, or None if not set.
    """
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return None
    result = await session.execute(
        select(GroupSetting.value).where(
            GroupSetting.group_id == group_id,
            GroupSetting.key == key,
        )
    )
    return result.scalar_one_or_none()


async def set_setting(
    session: AsyncSession, chat_id: int, key: str, value: Any
) -> bool:
    """
    Upsert a setting value (create if not exists, update if exists).

    Returns True if the group was found.
    """
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return False

    result = await session.execute(
        select(GroupSetting).where(
            GroupSetting.group_id == group_id,
            GroupSetting.key == key,
        )
    )
    setting = result.scalar_one_or_none()

    str_value = str(value) if value is not None else None

    if setting is None:
        setting = GroupSetting(group_id=group_id, key=key, value=str_value)
        session.add(setting)
    else:
        setting.value = str_value

    return True


async def get_all_settings(
    session: AsyncSession, chat_id: int
) -> dict[str, Optional[str]]:
    """Return all settings for a group as a dict."""
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return {}
    result = await session.execute(
        select(GroupSetting).where(GroupSetting.group_id == group_id)
    )
    return {s.key: s.value for s in result.scalars().all()}


async def delete_setting(
    session: AsyncSession, chat_id: int, key: str
) -> bool:
    """Delete a specific setting. Returns True if it existed."""
    group_id = await _get_group_db_id(session, chat_id)
    if group_id is None:
        return False
    result = await session.execute(
        delete(GroupSetting).where(
            GroupSetting.group_id == group_id,
            GroupSetting.key == key,
        )
    )
    return result.rowcount > 0
