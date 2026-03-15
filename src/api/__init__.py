"""
API routers package.

Provides REST API endpoints for bot management, authentication, and configuration.
"""

from src.api.auth import router as auth_router
from src.api.bot import router as bot_router
from src.api.config import router as config_router

__all__ = [
    "auth_router",
    "bot_router",
    "config_router",
]
