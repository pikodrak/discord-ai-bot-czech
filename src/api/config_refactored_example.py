"""
Example of refactored config endpoints using the validation wrapper utility.

This file demonstrates how to use the validate_and_update_config utility
to eliminate code duplication in the config API handlers.

BEFORE (lines 395-443 in config.py):
    @router.patch("/discord", response_model=Dict[str, str])
    async def update_discord_config(
        config: ConfigDiscordUpdate,
        current_user: dict = Depends(get_current_admin_user)
    ) -> Dict[str, str]:
        try:
            config_manager = get_config_manager()
            update_data = config.model_dump(exclude_unset=True, exclude_none=True)

            if not update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No Discord configuration updates provided"
                )

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

AFTER (using validation wrapper):
"""

from typing import Dict
from fastapi import APIRouter, Depends

from src.api.auth import get_current_admin_user
from src.api.utils import async_validate_and_update_config
from src.api.config import ConfigDiscordUpdate, ConfigAIUpdate, ConfigBehaviorUpdate


router = APIRouter()


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
    return async_validate_and_update_config(
        config_model=config,
        empty_message="No Discord configuration updates provided",
        success_message="Discord configuration updated successfully",
        error_context="Discord configuration"
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
    return async_validate_and_update_config(
        config_model=config,
        empty_message="No AI configuration updates provided",
        success_message="AI configuration updated successfully",
        error_context="AI configuration"
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
    return async_validate_and_update_config(
        config_model=config,
        empty_message="No behavior configuration updates provided",
        success_message="Behavior configuration updated successfully",
        error_context="behavior configuration"
    )


# Code reduction summary:
# - Before: ~25 lines per endpoint × 3 endpoints = ~75 lines
# - After: ~7 lines per endpoint × 3 endpoints = ~21 lines
# - Eliminated: ~54 lines of duplicated error handling
# - Added: ~100 lines of reusable utility (used by multiple endpoints)
# - Net benefit: Better maintainability, consistent error handling, DRY principle
