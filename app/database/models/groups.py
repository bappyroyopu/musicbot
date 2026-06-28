"""
Group model — tracks Telegram groups/supergroups using the bot.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base


class Group(Base):
    """Represents a Telegram group/supergroup registered with the bot."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True,
        comment="Telegram chat ID (negative for groups)",
    )
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="Group title"
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="Group @username if public"
    )
    language: Mapped[str] = mapped_column(
        String(10), default="en", nullable=False,
        comment="Bot language for this group",
    )
    volume: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False,
        comment="Default playback volume (1-200)",
    )
    loop: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Whether loop mode is enabled",
    )
    shuffle: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Whether shuffle mode is enabled",
    )
    auto_leave: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
        comment="Whether bot auto-leaves after inactivity",
    )
    max_queue: Mapped[int] = mapped_column(
        Integer, default=50, nullable=False,
        comment="Maximum queue size (0 = unlimited)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
        comment="Whether the bot is active in this group",
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )

    # Relationships
    queue_items: Mapped[list["QueueItem"]] = relationship(  # noqa: F821
        "QueueItem", back_populates="group", lazy="select",
        cascade="all, delete-orphan",
    )
    history_items: Mapped[list["HistoryItem"]] = relationship(  # noqa: F821
        "HistoryItem", back_populates="group", lazy="select",
        cascade="all, delete-orphan",
    )
    admin_records: Mapped[list["Admin"]] = relationship(  # noqa: F821
        "Admin", back_populates="group", lazy="select",
        cascade="all, delete-orphan",
    )
    settings: Mapped[list["GroupSetting"]] = relationship(  # noqa: F821
        "GroupSetting", back_populates="group", lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Group chat_id={self.chat_id} title={self.title!r}>"
