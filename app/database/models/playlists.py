"""
Playlist and PlaylistItem models — user-created playlists.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base


class Playlist(Base):
    """A named playlist created by a user."""

    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Playlist name"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="Optional playlist description"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="playlists")  # noqa: F821
    items: Mapped[list["PlaylistItem"]] = relationship(
        "PlaylistItem",
        back_populates="playlist",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="PlaylistItem.position",
    )

    def __repr__(self) -> str:
        return f"<Playlist id={self.id} name={self.name!r}>"

    @property
    def item_count(self) -> int:
        """Number of items in this playlist (requires loaded relationship)."""
        return len(self.items)


class PlaylistItem(Base):
    """A single song entry in a user playlist."""

    __tablename__ = "playlist_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    playlist_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("playlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Order in playlist"
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="Song title"
    )
    url: Mapped[str] = mapped_column(
        String(2048), nullable=False, comment="YouTube URL"
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
        String(256), nullable=True, comment="Channel name"
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    playlist: Mapped["Playlist"] = relationship("Playlist", back_populates="items")

    def __repr__(self) -> str:
        return f"<PlaylistItem id={self.id} pos={self.position} title={self.title!r}>"
