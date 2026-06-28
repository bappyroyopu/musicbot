"""
GroupSetting model — key/value store for per-group configuration.

Complements the structured columns in the Group model with
arbitrary extensible key-value settings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base


class GroupSetting(Base):
    """Key-value setting for a group."""

    __tablename__ = "group_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="Setting key"
    )
    value: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="Setting value (serialized as string)"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        onupdate=func.now(),
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="settings")  # noqa: F821

    def __repr__(self) -> str:
        return f"<GroupSetting group_id={self.group_id} {self.key}={self.value!r}>"
