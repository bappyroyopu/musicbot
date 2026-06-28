"""
Queue model — represents songs waiting to be played in a group.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base


class QueueStatus(str, enum.Enum):
    """Status of a queue item."""

    PENDING = "pending"      # Waiting in queue
    DOWNLOADING = "downloading"  # Being downloaded
    PLAYING = "playing"      # Currently playing
    DONE = "done"            # Finished playing
    FAILED = "failed"        # Download/play failed
    SKIPPED = "skipped"      # Skipped by user


class QueueItem(Base):
    """Represents a single song entry in a group's queue."""

    __tablename__ = "queue"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Position in queue (0 = next to play)",
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="Song title"
    )
    url: Mapped[str] = mapped_column(
        String(2048), nullable=False, comment="Original YouTube/source URL"
    )
    video_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="YouTube video ID"
    )
    thumbnail: Mapped[Optional[str]] = mapped_column(
        String(2048), nullable=True, comment="Thumbnail URL"
    )
    duration: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Duration in seconds",
    )
    uploader: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="Channel/uploader name"
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="Local path to downloaded audio file"
    )
    requested_by_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
        comment="Telegram user ID of requester",
    )
    requested_by_name: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="Display name of requester",
    )
    status: Mapped[QueueStatus] = mapped_column(
        Enum(QueueStatus),
        default=QueueStatus.PENDING,
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When playback started",
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="queue_items")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<QueueItem id={self.id} pos={self.position} "
            f"title={self.title!r} status={self.status}>"
        )

    @property
    def duration_str(self) -> str:
        """Return duration formatted as MM:SS or HH:MM:SS."""
        secs = self.duration
        hours, remainder = divmod(secs, 3600)
        mins, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
