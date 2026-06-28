"""
History model — records played songs per group.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base


class HistoryItem(Base):
    """Records a played song for a group."""

    __tablename__ = "history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="Song title"
    )
    url: Mapped[str] = mapped_column(
        String(2048), nullable=False, comment="Source URL"
    )
    video_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="YouTube video ID"
    )
    thumbnail: Mapped[Optional[str]] = mapped_column(
        String(2048), nullable=True, comment="Thumbnail URL"
    )
    duration: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Duration in seconds"
    )
    uploader: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="Channel/uploader name"
    )
    requested_by_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Telegram user ID"
    )
    requested_by_name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="Display name"
    )
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="history_items")  # noqa: F821

    def __repr__(self) -> str:
        return f"<HistoryItem id={self.id} title={self.title!r}>"
