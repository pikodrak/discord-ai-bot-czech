"""
Example demonstrating the use of validation wrapper utilities.

Shows how to refactor config API endpoints using the reusable validation
wrapper functions to eliminate code duplication.
"""

from typing import Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.auth import get_current_admin_user
from src.api.validation import (
    validate_config_update,
    validate_update_data,
    extract_update_data
)
from src.config import get_config_manager


router = APIRouter()


# ============================================================================
# Request Models
# ============================================================================


class ConfigDiscordUpdate(BaseModel):
    """Model for updating Discord configuration."""
    discord_channel_ids: str | None = None
    discord_bot_token: str | None = None


class ConfigAIUpdate(BaseModel):
    """Model for updating AI configuration."""
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None


class ConfigBehaviorUpdate(BaseModel):
    """Model for updating behavior configuration."""
    bot_language: str | None = None
    bot_response_threshold: float | None = None


# ============================================================================
# BEFORE: Repetitive error handling in each endpoint
# ============================================================================


@router.patch("/discord/old")
async def update_discord_config_old(
    config: ConfigDiscordUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Old approach with duplicated error handling."""
    try:
        config_manager = get_config_manager()
        update_data = config.model_dump(exclude_unset=True, exclude_none=True)

        if not update_data:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Discord configuration updates provided"
            )

        config_manager.update(**update_data)
        return {"message": "Discord configuration updated successfully"}

    except ValueError as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update Discord configuration: {str(e)}"
        )


# ============================================================================
# AFTER: Clean endpoints using validation utilities
# ============================================================================


@router.patch("/discord/new")
@validate_config_update(
    config_type="Discord configuration",
    success_message="Discord configuration updated successfully"
)
async def update_discord_config_new(
    config: ConfigDiscordUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    New approach using validation wrapper.

    Benefits:
    - No repetitive try/except blocks
    - Consistent error handling across all endpoints
    - Cleaner, more readable code
    - Less code to maintain
    """
    config_manager = get_config_manager()
    update_data = extract_update_data(config)
    validate_update_data(update_data, "Discord configuration")

    config_manager.update(**update_data)
    return {"message": "Discord configuration updated successfully"}


@router.patch("/ai/new")
@validate_config_update(
    config_type="AI configuration",
    success_message="AI configuration updated successfully"
)
async def update_ai_config_new(
    config: ConfigAIUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Update AI configuration using validation wrapper."""
    config_manager = get_config_manager()
    update_data = extract_update_data(config)
    validate_update_data(update_data, "AI configuration")

    config_manager.update(**update_data)
    return {"message": "AI configuration updated successfully"}


@router.patch("/behavior/new")
@validate_config_update(
    config_type="behavior configuration",
    success_message="Behavior configuration updated successfully"
)
async def update_behavior_config_new(
    config: ConfigBehaviorUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Update behavior configuration using validation wrapper."""
    config_manager = get_config_manager()
    update_data = extract_update_data(config)
    validate_update_data(update_data, "behavior configuration")

    config_manager.update(**update_data)
    return {"message": "Behavior configuration updated successfully"}


# ============================================================================
# Advanced: Inline validation without decorator
# ============================================================================


@router.patch("/advanced")
async def update_with_inline_validation(
    config: ConfigDiscordUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Example showing inline usage without decorator.

    This approach gives you more control over the flow
    while still using the validation utilities.
    """
    config_manager = get_config_manager()

    # Extract and validate update data
    update_data = extract_update_data(config)
    validate_update_data(update_data, "Discord configuration")

    # Perform update
    config_manager.update(**update_data)

    # Custom response logic
    return {
        "message": "Discord configuration updated successfully",
        "updated_fields": list(update_data.keys()),
        "field_count": len(update_data)
    }


# ============================================================================
# Summary of Benefits
# ============================================================================

"""
Key improvements from using validation utilities:

1. CODE REDUCTION:
   - Before: ~25 lines per endpoint (with try/except blocks)
   - After: ~7 lines per endpoint (using decorator + utilities)
   - Reduction: ~72% less code per endpoint

2. CONSISTENCY:
   - All endpoints handle errors the same way
   - Same HTTP status codes for same error types
   - Consistent error message format

3. MAINTAINABILITY:
   - Change error handling logic in one place
   - Easy to add new validation rules
   - Less code duplication

4. READABILITY:
   - Endpoint logic is clear and focused
   - Error handling doesn't obscure business logic
   - Self-documenting through decorator parameters

5. TESTABILITY:
   - Validation logic tested independently
   - Easier to mock and test endpoints
   - Clear separation of concerns
"""
