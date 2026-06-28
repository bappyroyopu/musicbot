"""Middlewares package."""
from app.bot.middlewares.rate_limit import rate_limit_middleware
from app.bot.middlewares.group_register import group_register_middleware

__all__ = ["rate_limit_middleware", "group_register_middleware"]
