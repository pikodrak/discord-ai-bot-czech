"""
API utilities for common request handling patterns.

This module provides reusable utilities for FastAPI endpoints, including
validation wrappers and error handling decorators.
"""

from typing import Any, Callable, Dict, Optional, TypeVar, cast
from functools import wraps

from fastapi import HTTPException, status
from pydantic import BaseModel

from src.config import get_config_manager


T = TypeVar("T", bound=BaseModel)


def validate_and_update_config(
    config_model: T,
    empty_message: str,
    success_message: str,
    error_context: str
) -> Dict[str, str]:
    """
    Validate request data and update configuration with error handling.

    This wrapper handles the common pattern of:
    1. Extracting non-null fields from Pydantic model
    2. Validating that at least one field is present
    3. Updating configuration via ConfigManager
    4. Catching and re-raising ValueError as 400 Bad Request
    5. Catching and re-raising other exceptions as 500 Internal Server Error

    Args:
        config_model: Pydantic model containing configuration updates
        empty_message: Error message when no fields are provided
        success_message: Message to return on successful update
        error_context: Context string for error messages (e.g., "Discord configuration")

    Returns:
        Dict with success message

    Raises:
        HTTPException: On validation error (400) or update failure (500)

    Example:
        ```python
        @router.patch("/discord")
        async def update_discord_config(
            config: ConfigDiscordUpdate,
            current_user: dict = Depends(get_current_admin_user)
        ) -> Dict[str, str]:
            return validate_and_update_config(
                config_model=config,
                empty_message="No Discord configuration updates provided",
                success_message="Discord configuration updated successfully",
                error_context="Discord configuration"
            )
        ```
    """
    try:
        config_manager = get_config_manager()
        update_data = config_model.model_dump(exclude_unset=True, exclude_none=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=empty_message
            )

        # Update configuration (vault persistence handled automatically)
        config_manager.update(**update_data)

        return {"message": success_message}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update {error_context}: {str(e)}"
        )


def async_validate_and_update_config(
    config_model: T,
    empty_message: str,
    success_message: str,
    error_context: str
) -> Dict[str, str]:
    """
    Async version of validate_and_update_config for async endpoint handlers.

    See validate_and_update_config for full documentation.

    Args:
        config_model: Pydantic model containing configuration updates
        empty_message: Error message when no fields are provided
        success_message: Message to return on successful update
        error_context: Context string for error messages

    Returns:
        Dict with success message

    Raises:
        HTTPException: On validation error (400) or update failure (500)
    """
    return validate_and_update_config(
        config_model=config_model,
        empty_message=empty_message,
        success_message=success_message,
        error_context=error_context
    )
