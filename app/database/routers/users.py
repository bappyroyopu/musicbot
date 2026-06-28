"""
CRUD operations for User model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.users import User


async def get_user(session: AsyncSession, tg_id: int) -> Optional[User]:
    """Fetch a user by Telegram ID. Returns None if not found."""
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    tg_id: int,
    first_name: str,
    username: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: Optional[str] = None,
) -> tuple[User, bool]:
    """
    Fetch an existing user or create a new one.

    Returns:
        Tuple of (user, created) where created=True if a new record was made.
    """
    user = await get_user(session, tg_id)
    if user is not None:
        # Update mutable fields
        user.first_name = first_name
        user.username = username
        user.last_name = last_name
        user.last_seen = datetime.utcnow()
        return user, False

    user = User(
        tg_id=tg_id,
        first_name=first_name,
        username=username,
        last_name=last_name,
        language_code=language_code,
    )
    session.add(user)
    await session.flush()
    return user, True


async def ban_user(session: AsyncSession, tg_id: int) -> bool:
    """Ban a user. Returns True if the user existed."""
    result = await session.execute(
        update(User).where(User.tg_id == tg_id).values(is_banned=True)
    )
    return result.rowcount > 0


async def unban_user(session: AsyncSession, tg_id: int) -> bool:
    """Unban a user. Returns True if the user existed."""
    result = await session.execute(
        update(User).where(User.tg_id == tg_id).values(is_banned=False)
    )
    return result.rowcount > 0


async def is_banned(session: AsyncSession, tg_id: int) -> bool:
    """Check whether a user is banned."""
    result = await session.execute(
        select(User.is_banned).where(User.tg_id == tg_id)
    )
    value = result.scalar_one_or_none()
    return bool(value)


async def get_total_users(session: AsyncSession) -> int:
    """Return the total number of registered users."""
    from sqlalchemy import func
    result = await session.execute(select(func.count()).select_from(User))
    return result.scalar_one()
