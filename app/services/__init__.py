"""Services package."""
from app.services.music_service import MusicService, music_service
from app.services.health import app as health_app

__all__ = ["MusicService", "music_service", "health_app"]
