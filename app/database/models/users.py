"""
User model — tracks Telegram users who interact with the bot.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base


class User(Base):
    """Represents a Telegram user registered with the bot."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True,
        comment="Telegram user ID",
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="Telegram @username without @"
    )
    first_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="User's first name"
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="User's last name"
    )
    language_code: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, comment="Telegram client language code"
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Whether the user is banned from using the bot",
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the user first interacted with the bot",
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
        comment="Last activity timestamp",
    )

    # Relationships
    playlists: Mapped[list["Playlist"]] = relationship(  # noqa: F821
        "Playlist", back_populates="owner", lazy="select"
    )
    admin_records: Mapped[list["Admin"]] = relationship(  # noqa: F821
        "Admin", back_populates="user", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<User tg_id={self.tg_id} username={self.username!r}>"

    @property
    def display_name(self) -> str:
        """Return the best available display name."""
        if self.username:
            return f"@{self.username}"
        full = self.first_name
        if self.last_name:
            full += f" {self.last_name}"
        return full

    @property
    def mention(self) -> str:
        """Return an HTML mention string for use in messages."""
        name = self.first_name
        if self.last_name:
            name += f" {self.last_name}"
        return f'<a href="tg://user?id={self.tg_id}">{name}</a>'
