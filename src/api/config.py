"""
Configuration management router with encrypted credential storage.

Provides secure REST API endpoints for reading and updating bot configuration
including Discord settings, AI API keys, and bot behavior settings.

All sensitive credentials (tokens, API keys, passwords) are automatically
persisted to an encrypted vault when updated through this API. The vault
provides:
- AES-256-GCM encryption
- Automatic credential rotation policies
- Access tracking and metadata
- Secure file permissions (0600)

Reading configuration automatically loads from:
1. Encrypted vault (for sensitive credentials)
2. Environment variables (as override)
3. Configuration files (.env, YAML)
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
import yaml

from src.config import (
    Settings,
    BotSettings,
    get_settings,
    get_config_manager,
    reload_settings
)
from src.api.auth import get_current_admin_user
from src.shared_config import get_shared_config_loader, save_bot_config_to_shared
from src.ipc import send_reload_command


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class ConfigDiscordUpdate(BaseModel):
    """Model for updating Discord configuration."""

    discord_bot_token: Optional[str] = Field(
        None,
        min_length=50,
        description="Discord bot token"
    )
    discord_guild_id: Optional[str] = Field(
        None,
        description="Discord guild/server ID"
    )
    discord_channel_ids: Optional[str] = Field(
        None,
        description="Comma-separated channel IDs"
    )

    @field_validator("discord_channel_ids")
    @classmethod
    def validate_channel_ids(cls, v: Optional[str]) -> Optional[str]:
        """Validate channel IDs format."""
        if v is None:
            return v

        # Check format: comma-separated integers
        try:
            channel_ids = [cid.strip() for cid in v.split(",") if cid.strip()]
            for cid in channel_ids:
                int(cid)  # Validate each ID is numeric
            return v
        except ValueError:
            raise ValueError("Channel IDs must be comma-separated integers")


class ConfigAIUpdate(BaseModel):
    """Model for updating AI API keys."""

    anthropic_api_key: Optional[str] = Field(
        None,
        min_length=10,
        description="Anthropic (Claude) API key"
    )
    google_api_key: Optional[str] = Field(
        None,
        min_length=10,
        description="Google (Gemini) API key"
    )
    openai_api_key: Optional[str] = Field(
        None,
        min_length=10,
        description="OpenAI API key"
    )


class ConfigBehaviorUpdate(BaseModel):
    """Model for updating bot behavior settings."""

    bot_response_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Response confidence threshold (0.0-1.0)"
    )
    bot_max_history: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Maximum message history to keep"
    )
    bot_language: Optional[str] = Field(
        None,
        description="Bot response language code (e.g., 'cs', 'en')"
    )
    bot_personality: Optional[str] = Field(
        None,
        description="Bot personality type"
    )

    @field_validator("bot_language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        """Validate language code."""
        if v is None:
            return v

        valid_languages = {"cs", "en", "sk", "de", "fr", "es"}
        if v.lower() not in valid_languages:
            raise ValueError(f"Language must be one of {valid_languages}")
        return v.lower()


class ConfigUpdate(BaseModel):
    """Model for comprehensive configuration updates."""

    # Discord settings
    discord_bot_token: Optional[str] = Field(None, description="Discord bot token")
    discord_guild_id: Optional[str] = Field(None, description="Discord guild ID")
    discord_channel_ids: Optional[str] = Field(None, description="Comma-separated channel IDs")

    # AI API keys
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    google_api_key: Optional[str] = Field(None, description="Google Gemini API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")

    # Bot behavior
    bot_response_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    bot_max_history: Optional[int] = Field(None, ge=1, le=1000)
    bot_language: Optional[str] = Field(None, description="Bot language code")
    bot_personality: Optional[str] = Field(None, description="Bot personality")

    # API settings
    api_host: Optional[str] = Field(None, description="API server host")
    api_port: Optional[int] = Field(None, ge=1, le=65535, description="API server port")

    # Logging
    log_level: Optional[str] = Field(None, description="Logging level")


class ConfigResponse(BaseModel):
    """Model for configuration response with sensitive data masked."""

    # Discord configuration
    discord_configured: bool
    discord_guild_id: Optional[str]
    channels: List[str]

    # AI configuration
    ai_providers_available: List[str]
    preferred_ai_provider: Optional[str]
    anthropic_configured: bool
    google_configured: bool
    openai_configured: bool

    # Bot behavior settings
    bot_settings: Dict[str, Any]

    # API settings
    api_settings: Dict[str, Any]

    # Environment
    environment: str


class ConfigSecretResponse(BaseModel):
    """Model for configuration with masked secrets."""

    discord_bot_token: Optional[str]
    anthropic_api_key: Optional[str]
    google_api_key: Optional[str]
    openai_api_key: Optional[str]
    secret_key: Optional[str]


class ValidationResult(BaseModel):
    """Model for configuration validation results."""

    valid: bool
    errors: List[str]
    warnings: List[str]


# ============================================================================
# Helper Functions
# ============================================================================


def mask_secret(value: Optional[str], show_chars: int = 4) -> Optional[str]:
    """
    Mask a secret value, showing only first and last few characters.

    Args:
        value: Secret value to mask
        show_chars: Number of characters to show at start/end

    Returns:
        Masked secret string or None
    """
    if not value:
        return None

    if len(value) <= show_chars * 2:
        return "***"

    return f"{value[:show_chars]}...{value[-show_chars:]}"




# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/", response_model=ConfigResponse)
async def get_config(
    settings: Settings = Depends(get_settings)
) -> ConfigResponse:
    """
    Get current bot configuration (read-only, sensitive data masked).

    Returns:
        ConfigResponse: Current configuration with masked secrets

    Example:
        ```
        GET /api/config/
        ```
    """
    return ConfigResponse(
        discord_configured=settings.has_discord_config(),
        discord_guild_id=settings.discord_guild_id,
        channels=settings.get_channel_ids_list(),
        ai_providers_available=settings.get_available_llm_providers(),
        preferred_ai_provider=settings.get_preferred_ai_provider(),
        anthropic_configured=bool(settings.anthropic_api_key),
        google_configured=bool(settings.google_api_key),
        openai_configured=bool(settings.openai_api_key),
        bot_settings={
            "language": settings.bot_language,
            "personality": settings.bot_personality,
            "response_threshold": settings.bot_response_threshold,
            "max_history": settings.bot_max_history,
        },
        api_settings={
            "host": settings.api_host,
            "port": settings.api_port,
            "reload": settings.api_reload,
        },
        environment=settings.environment
    )


@router.get("/secrets", response_model=ConfigSecretResponse)
async def get_config_secrets(
    current_user: dict = Depends(get_current_admin_user),
    settings: Settings = Depends(get_settings)
) -> ConfigSecretResponse:
    """
    Get configuration with masked secret values (admin only).

    Requires authentication with admin privileges.

    Args:
        current_user: Authenticated admin user
        settings: Application settings

    Returns:
        ConfigSecretResponse: Configuration with masked secrets

    Example:
        ```
        GET /api/config/secrets
        Authorization: Bearer <token>
        ```
    """
    return ConfigSecretResponse(
        discord_bot_token=mask_secret(settings.discord_bot_token),
        anthropic_api_key=mask_secret(settings.anthropic_api_key),
        google_api_key=mask_secret(settings.google_api_key),
        openai_api_key=mask_secret(settings.openai_api_key),
        secret_key=mask_secret(settings.secret_key)
    )


@router.put("/", response_model=Dict[str, str])
async def update_config(
    config: ConfigUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Update bot configuration (admin only).

    Updates configuration in memory and persists sensitive credentials
    to encrypted vault. Non-sensitive settings are updated in environment.
    Requires authentication with admin privileges.

    Args:
        config: Configuration updates
        current_user: Authenticated admin user

    Returns:
        Dict with success message and updated fields

    Raises:
        HTTPException: If validation or update fails

    Example:
        ```
        PUT /api/config/
        Authorization: Bearer <token>
        {
            "bot_language": "cs",
            "bot_response_threshold": 0.7
        }
        ```
    """
    try:
        config_manager = get_config_manager()
        update_data = config.model_dump(exclude_unset=True, exclude_none=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No configuration updates provided"
            )

        # Update configuration in memory and persist to vault
        # ConfigManager.update() now handles vault persistence automatically
        config_manager.update(**update_data)

        # Save to shared config storage
        try:
            current_settings = get_settings()
            shared_config = current_settings.model_dump()
            save_bot_config_to_shared(shared_config)

            # Notify bot process to reload configuration
            reload_sent = await send_reload_command()
            if reload_sent:
                import logging
                logging.info("Reload command sent to bot process")
            else:
                import logging
                logging.warning("Failed to send reload command to bot process")

        except Exception as e:
            import logging
            logging.warning(f"Failed to save to shared config or notify bot: {e}")

        return {
            "message": "Configuration updated successfully",
            "updated_fields": list(update_data.keys())
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.patch("/discord", response_model=Dict[str, str])
async def update_discord_config(
    config: ConfigDiscordUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Update Discord configuration (admin only).

    Args:
        config: Discord configuration updates
        current_user: Authenticated admin user

    Returns:
        Dict with success message

    Example:
        ```
        PATCH /api/config/discord
        Authorization: Bearer <token>
        {
            "discord_channel_ids": "123456789,987654321"
        }
        ```
    """
    try:
        config_manager = get_config_manager()
        update_data = config.model_dump(exclude_unset=True, exclude_none=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Discord configuration updates provided"
            )

        # Update configuration (vault persistence handled automatically)
        config_manager.update(**update_data)

        return {"message": "Discord configuration updated successfully"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update Discord configuration: {str(e)}"
        )


@router.patch("/ai", response_model=Dict[str, str])
async def update_ai_config(
    config: ConfigAIUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Update AI API keys configuration (admin only).

    Args:
        config: AI configuration updates
        current_user: Authenticated admin user

    Returns:
        Dict with success message

    Example:
        ```
        PATCH /api/config/ai
        Authorization: Bearer <token>
        {
            "anthropic_api_key": "sk-ant-..."
        }
        ```
    """
    try:
        config_manager = get_config_manager()
        update_data = config.model_dump(exclude_unset=True, exclude_none=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No AI configuration updates provided"
            )

        # Update configuration (vault persistence handled automatically)
        config_manager.update(**update_data)

        return {"message": "AI configuration updated successfully"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update AI configuration: {str(e)}"
        )


@router.patch("/behavior", response_model=Dict[str, str])
async def update_behavior_config(
    config: ConfigBehaviorUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Update bot behavior settings (admin only).

    Args:
        config: Behavior configuration updates
        current_user: Authenticated admin user

    Returns:
        Dict with success message

    Example:
        ```
        PATCH /api/config/behavior
        Authorization: Bearer <token>
        {
            "bot_language": "en",
            "bot_response_threshold": 0.8
        }
        ```
    """
    try:
        config_manager = get_config_manager()
        update_data = config.model_dump(exclude_unset=True, exclude_none=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No behavior configuration updates provided"
            )

        # Update configuration (vault persistence handled automatically)
        config_manager.update(**update_data)

        return {"message": "Behavior configuration updated successfully"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update behavior configuration: {str(e)}"
        )


@router.post("/reload", response_model=Dict[str, str])
async def reload_config(
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Reload configuration from vault, .env and YAML files (admin only).

    Reloads all configuration from disk and encrypted vault,
    discarding in-memory changes.

    Args:
        current_user: Authenticated admin user

    Returns:
        Dict with success message

    Example:
        ```
        POST /api/config/reload
        Authorization: Bearer <token>
        ```
    """
    try:
        reload_settings()
        return {"message": "Configuration reloaded successfully from disk"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload configuration: {str(e)}"
        )


@router.post("/hot-reload", response_model=Dict[str, Any])
async def hot_reload_bot_config(
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Trigger hot-reload of bot configuration (admin only).

    Sends IPC signal to bot process to reload its configuration
    without restarting the bot.

    Args:
        current_user: Authenticated admin user

    Returns:
        Dict with success status and message

    Example:
        ```
        POST /api/config/hot-reload
        Authorization: Bearer <token>
        ```
    """
    try:
        import logging
        logger = logging.getLogger(__name__)

        # Get current settings and save to shared storage
        current_settings = get_settings()
        shared_config = current_settings.model_dump()

        logger.info("Saving current configuration to shared storage...")
        save_bot_config_to_shared(shared_config)

        # Send reload command to bot process
        logger.info("Sending reload command to bot process...")
        reload_sent = await send_reload_command()

        if reload_sent:
            return {
                "success": True,
                "message": "Bot configuration reload triggered successfully",
                "config_saved": True,
                "reload_signal_sent": True
            }
        else:
            return {
                "success": False,
                "message": "Failed to send reload signal to bot (bot may not be running)",
                "config_saved": True,
                "reload_signal_sent": False
            }

    except Exception as e:
        import logging
        logging.error(f"Failed to trigger hot reload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger hot reload: {str(e)}"
        )


@router.get("/validate", response_model=ValidationResult)
async def validate_config(
    settings: Settings = Depends(get_settings)
) -> ValidationResult:
    """
    Validate current configuration.

    Checks for missing required settings, insecure defaults,
    and configuration issues.

    Args:
        settings: Application settings

    Returns:
        ValidationResult: Validation results with errors and warnings

    Example:
        ```
        GET /api/config/validate
        ```
    """
    errors = []
    warnings = []

    # Check Discord configuration
    if not settings.discord_bot_token:
        errors.append("Discord bot token is not configured")

    if not settings.discord_channel_ids:
        warnings.append("No Discord channels configured")

    # Check AI API keys
    if not settings.has_any_ai_key():
        errors.append("No AI API key configured (need at least one)")

    # Check for insecure defaults
    if settings.secret_key == "change-me-in-production":
        warnings.append("Using default secret key - change in production")

    if settings.admin_password == "admin":
        warnings.append("Using default admin password - change immediately")

    # Production-specific checks
    if settings.is_production():
        if settings.api_reload:
            warnings.append("API auto-reload is enabled in production")

        if settings.log_level == "DEBUG":
            warnings.append("Debug logging is enabled in production")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


@router.get("/export", response_model=Dict[str, Any])
async def export_config(
    current_user: dict = Depends(get_current_admin_user),
    mask_secrets: bool = True
) -> Dict[str, Any]:
    """
    Export current configuration as dictionary (admin only).

    Args:
        current_user: Authenticated admin user
        mask_secrets: Whether to mask sensitive values (default: True)

    Returns:
        Dict containing all configuration values

    Example:
        ```
        GET /api/config/export?mask_secrets=true
        Authorization: Bearer <token>
        ```
    """
    config_manager = get_config_manager()

    if mask_secrets:
        return config_manager.get_safe_dict()
    else:
        return config_manager.to_dict()
