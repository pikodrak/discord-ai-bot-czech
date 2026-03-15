"""
Validation utilities for API request handling.

Provides reusable wrapper functions for handling request validation,
error catching, and HTTPException raising in a consistent manner.
"""

from typing import Any, Callable, Dict, TypeVar
from functools import wraps

from fastapi import HTTPException, status
from pydantic import BaseModel


T = TypeVar('T')


def validate_config_update(
    config_type: str,
    success_message: str = "Configuration updated successfully"
) -> Callable:
    """
    Decorator to validate and handle configuration update requests.

    This wrapper handles:
    - Request validation (checking for empty update data)
    - ValueError catching (validation errors) -> 400 Bad Request
    - Generic Exception catching -> 500 Internal Server Error
    - HTTPException raising with appropriate status codes

    Args:
        config_type: Human-readable type of configuration being updated
                    (e.g., "Discord configuration", "AI configuration")
        success_message: Message to return on successful update

    Returns:
        Decorator function that wraps endpoint handlers

    Example:
        ```python
        @router.patch("/discord")
        @validate_config_update(
            config_type="Discord configuration",
            success_message="Discord configuration updated successfully"
        )
        async def update_discord_config(
            config: ConfigDiscordUpdate,
            current_user: dict = Depends(get_current_admin_user)
        ) -> Dict[str, str]:
            config_manager = get_config_manager()
            update_data = config.model_dump(exclude_unset=True, exclude_none=True)
            config_manager.update(**update_data)
            return {"message": success_message}
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                # Call the wrapped function
                result = await func(*args, **kwargs)
                return result

            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Validation error: {str(e)}"
                )
            except HTTPException:
                # Re-raise HTTPExceptions as-is (from wrapped function)
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update {config_type}: {str(e)}"
                )

        return wrapper
    return decorator


def validate_update_data(
    update_data: Dict[str, Any],
    config_type: str
) -> None:
    """
    Validate that update data is not empty.

    Args:
        update_data: Dictionary of configuration updates
        config_type: Human-readable type of configuration being updated

    Raises:
        HTTPException: If update_data is empty (400 Bad Request)

    Example:
        ```python
        update_data = config.model_dump(exclude_unset=True, exclude_none=True)
        validate_update_data(update_data, "Discord configuration")
        ```
    """
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No {config_type} updates provided"
        )


def extract_update_data(config: BaseModel) -> Dict[str, Any]:
    """
    Extract update data from Pydantic model, excluding unset and None values.

    Args:
        config: Pydantic model instance containing configuration updates

    Returns:
        Dictionary with only set and non-None values

    Example:
        ```python
        config = ConfigDiscordUpdate(discord_channel_ids="123456789")
        update_data = extract_update_data(config)
        # Returns: {"discord_channel_ids": "123456789"}
        ```
    """
    return config.model_dump(exclude_unset=True, exclude_none=True)
