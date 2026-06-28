"""
SQLAlchemy declarative base and model imports.

All models must be imported here so that Base.metadata contains
all tables for `create_all` and Alembic autogeneration.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# Import all models to register them with Base.metadata
from app.database.models.users import User  # noqa: E402, F401
from app.database.models.groups import Group  # noqa: E402, F401
from app.database.models.queue import QueueItem  # noqa: E402, F401
from app.database.models.history import HistoryItem  # noqa: E402, F401
from app.database.models.playlists import Playlist, PlaylistItem  # noqa: E402, F401
from app.database.models.admins import Admin  # noqa: E402, F401
from app.database.models.settings_model import GroupSetting  # noqa: E402, F401

__all__ = [
    "Base",
    "User",
    "Group",
    "QueueItem",
    "HistoryItem",
    "Playlist",
    "PlaylistItem",
    "Admin",
    "GroupSetting",
]
