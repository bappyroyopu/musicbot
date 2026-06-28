"""
Configuration module for the Telegram Voice Chat Music Bot.

Uses Pydantic BaseSettings for environment variable management.
Supports .env files and direct environment variable injection (Render, Docker).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Telegram API Credentials
    # ------------------------------------------------------------------
    api_id: int = Field(default=0, description="Telegram API ID from my.telegram.org")
    api_hash: str = Field(default="", description="Telegram API Hash from my.telegram.org")
    bot_token: str = Field(default="", description="Bot token from @BotFather")
    session_string: str = Field(
        default="", description="Pyrogram StringSession for user/assistant client"
    )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = Field(
        default="sqlite+aiosqlite:///./musicbot.db",
        description="SQLAlchemy async database URL",
    )

    # ------------------------------------------------------------------
    # Redis (optional)
    # ------------------------------------------------------------------
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis URL for caching and rate limiting",
    )

    # ------------------------------------------------------------------
    # Bot Behaviour
    # ------------------------------------------------------------------
    log_level: str = Field(default="INFO", description="Python logging level")
    max_queue_size: int = Field(
        default=50,
        ge=0,
        description="Maximum songs in queue per group (0 = unlimited)",
    )
    auto_leave_timeout: int = Field(
        default=300,
        ge=0,
        description="Seconds of inactivity before leaving voice chat (0 = never)",
    )
    default_volume: int = Field(
        default=100,
        ge=1,
        le=200,
        description="Default playback volume (1-200)",
    )
    max_search_results: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Maximum YouTube search results",
    )
    download_timeout: int = Field(
        default=120,
        ge=30,
        description="Download timeout in seconds",
    )
    max_duration: int = Field(
        default=3600,
        ge=0,
        description="Maximum audio duration in seconds (0 = unlimited)",
    )

    # ------------------------------------------------------------------
    # Owner & Support
    # ------------------------------------------------------------------
    owner_id: int = Field(default=0, description="Bot owner's Telegram user ID")
    support_chat: str = Field(
        default="",
        description="Support group/channel username",
    )

    # ------------------------------------------------------------------
    # Web server
    # ------------------------------------------------------------------
    port: int = Field(default=10000, ge=1, le=65535, description="Health check port")

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    temp_dir: str = Field(
        default="storage/temp",
        description="Directory for temporary audio files",
    )
    logs_dir: str = Field(
        default="logs",
        description="Directory for log files",
    )

    # ------------------------------------------------------------------
    # Render / Cloud flags
    # ------------------------------------------------------------------
    on_render: bool = Field(
        default=False,
        description="Set to True when deploying on Render",
    )

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------
    @property
    def temp_path(self) -> Path:
        """Resolved absolute path to the temporary storage directory."""
        return Path(self.temp_dir).resolve()

    @property
    def logs_path(self) -> Path:
        """Resolved absolute path to the logs directory."""
        return Path(self.logs_dir).resolve()

    @property
    def is_sqlite(self) -> bool:
        """True when using SQLite database."""
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        """True when using PostgreSQL database."""
        return "postgresql" in self.database_url or "postgres" in self.database_url

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: Optional[str]) -> str:
        """Automatically detect database URL and rewrite for async compatibility."""
        if not v:
            return "sqlite+aiosqlite:///./musicbot.db"
        
        # Convert standard Postgres to asyncpg
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("sqlite://"):
            if not v.startswith("sqlite+aiosqlite://"):
                v = v.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return v

    @field_validator("temp_dir", mode="before")
    @classmethod
    def validate_temp_dir(cls, v: Optional[str]) -> str:
        """Use /tmp/music inside Render."""
        if os.getenv("RENDER") == "true" or os.getenv("ON_RENDER") == "true":
            return "/tmp/music"
        return v or "storage/temp"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}, got {v!r}")
        return upper

    @model_validator(mode="after")
    def create_directories(self) -> "Settings":
        """Create required directories on startup."""
        for directory in [self.temp_path, self.logs_path]:
            directory.mkdir(parents=True, exist_ok=True)
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()  # type: ignore[call-arg]


# Module-level singleton for convenient import
settings: Settings = get_settings()
