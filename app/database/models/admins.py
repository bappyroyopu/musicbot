"""
Admin model — tracks group administrators who can control the bot.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base


class Admin(Base):
    """
    Maps a user as an admin for a specific group.

    Bot admins can use privileged commands like /stop, /skip, /clear, etc.
    """

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_by_tg_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
        comment="Telegram user ID of who granted admin",
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="admin_records")  # noqa: F821
    group: Mapped["Group"] = relationship("Group", back_populates="admin_records")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Admin user_id={self.user_id} group_id={self.group_id}>"
