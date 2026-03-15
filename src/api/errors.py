"""
Error response formatter for consistent API error handling.

This module provides a centralized error response formatter that consolidates
the duplicate try-except error handling pattern found across API endpoints.
Instead of repeating the same ValueError/Exception handling in every endpoint,
use this formatter to create consistent HTTP error responses.
"""

from typing import Any, Callable, Optional, TypeVar
from functools import wraps

from fastapi import HTTPException, status


T = TypeVar('T')


def format_error_response(
    error: Exception,
    operation_context: str,
    value_error_prefix: str = "Validation error"
) -> HTTPException:
    """
    Format an exception into a consistent HTTPException response.

    This function consolidates the common error handling pattern used throughout
    the API endpoints:
    - ValueError -> 400 Bad Request with validation error message
    - HTTPException -> Re-raised as-is (preserves existing HTTP errors)
    - Exception -> 500 Internal Server Error with operation context

    Args:
        error: The caught exception to format
        operation_context: Description of the operation that failed
                          (e.g., "update configuration", "start bot")
        value_error_prefix: Prefix for ValueError messages (default: "Validation error")

    Returns:
        HTTPException with appropriate status code and detail message

    Example:
        ```python
        try:
            config_manager.update(**update_data)
        except Exception as e:
            raise format_error_response(e, "update Discord configuration")
        ```
    """
    if isinstance(error, HTTPException):
        # Re-raise existing HTTPException as-is
        return error
    elif isinstance(error, ValueError):
        # Validation error -> 400 Bad Request
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{value_error_prefix}: {str(error)}"
        )
    else:
        # Generic error -> 500 Internal Server Error
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to {operation_context}: {str(error)}"
        )


def handle_api_errors(
    operation_context: str,
    value_error_prefix: str = "Validation error"
) -> Callable:
    """
    Decorator that wraps endpoint handlers with standardized error handling.

    This decorator consolidates the duplicate try-except blocks found in API endpoints.
    It catches ValueError and Exception, then formats them into appropriate HTTPExceptions.

    Args:
        operation_context: Description of the operation being performed
                          (e.g., "update Discord configuration", "start bot")
        value_error_prefix: Prefix for ValueError messages (default: "Validation error")

    Returns:
        Decorator function that wraps endpoint handlers

    Example:
        ```python
        @router.patch("/discord")
        @handle_api_errors("update Discord configuration")
        async def update_discord_config(
            config: ConfigDiscordUpdate,
            current_user: dict = Depends(get_current_admin_user)
        ) -> Dict[str, str]:
            config_manager = get_config_manager()
            update_data = config.model_dump(exclude_unset=True, exclude_none=True)
            if not update_data:
                raise ValueError("No Discord configuration updates provided")
            config_manager.update(**update_data)
            return {"message": "Discord configuration updated successfully"}
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                raise format_error_response(e, operation_context, value_error_prefix)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                raise format_error_response(e, operation_context, value_error_prefix)

        # Return async or sync wrapper based on whether the function is a coroutine
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def create_validation_error(message: str) -> HTTPException:
    """
    Create a 400 Bad Request HTTPException for validation errors.

    Args:
        message: The validation error message

    Returns:
        HTTPException with 400 status code

    Example:
        ```python
        if not update_data:
            raise create_validation_error("No configuration updates provided")
        ```
    """
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Validation error: {message}"
    )


def create_internal_error(
    operation_context: str,
    error: Optional[Exception] = None
) -> HTTPException:
    """
    Create a 500 Internal Server Error HTTPException.

    Args:
        operation_context: Description of the operation that failed
        error: Optional exception to include in the detail message

    Returns:
        HTTPException with 500 status code

    Example:
        ```python
        try:
            await manager.start()
        except RuntimeError as e:
            raise create_internal_error("start bot", e)
        ```
    """
    detail = f"Failed to {operation_context}"
    if error:
        detail += f": {str(error)}"

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail
    )


def create_conflict_error(message: str) -> HTTPException:
    """
    Create a 409 Conflict HTTPException for resource conflicts.

    Args:
        message: The conflict error message

    Returns:
        HTTPException with 409 status code

    Example:
        ```python
        if bot_manager.is_running():
            raise create_conflict_error("Bot is already running")
        ```
    """
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=message
    )


def create_not_found_error(resource: str) -> HTTPException:
    """
    Create a 404 Not Found HTTPException for missing resources.

    Args:
        resource: Description of the resource that was not found

    Returns:
        HTTPException with 404 status code

    Example:
        ```python
        if not user:
            raise create_not_found_error("User")
        ```
    """
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} not found"
    )
