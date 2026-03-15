"""
Configuration management module.

Provides unified configuration interface using the refactored configuration system
based on encrypted vault storage and shared configuration loader.
"""

from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings

from src.shared_config import SharedConfigLoader, get_shared_config_loader
from bot.config_loader import AdvancedBotConfig as BotSettings


class Settings(BaseSettings):
    """
    Application settings.

    Provides configuration for the Discord AI bot admin interface.
    Bot-specific configuration should use bot.config_loader.AdvancedBotConfig instead.
    """

    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=False, description="Enable auto-reload")

    # Security
    jwt_secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION",
        description="JWT secret key for token signing"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT token expiration in hours")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )

    # Database (for user authentication)
    database_url: str = Field(
        default="data/admin_users.db",
        description="SQLite database path for admin users"
    )

    # Project paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent,
        description="Project root directory"
    )

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings
    """
    return Settings()


def get_config_manager() -> SharedConfigLoader:
    """
    Get shared configuration manager.

    This is used for bot configuration that can be hot-reloaded
    and shared between the bot process and admin interface.

    Returns:
        SharedConfigLoader: Shared configuration manager
    """
    settings = get_settings()
    return get_shared_config_loader(settings.project_root)


def reload_settings() -> Settings:
    """
    Reload settings by clearing cache.

    Returns:
        Settings: New settings instance
    """
    get_settings.cache_clear()
    return get_settings()


# Export commonly used items
__all__ = [
    "Settings",
    "BotSettings",
    "get_settings",
    "get_config_manager",
    "reload_settings",
]