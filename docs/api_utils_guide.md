# API Utilities Guide

## Overview

The `src/api/utils.py` module provides reusable utilities for FastAPI endpoints, specifically designed to eliminate code duplication in configuration update handlers.

## Problem Statement

Before the utility, config API handlers (`update_discord_config`, `update_ai_config`, `update_behavior_config`) repeated the same pattern:

1. Get config manager
2. Extract non-null fields from request model
3. Validate at least one field is present
4. Update configuration
5. Handle ValueError → 400 Bad Request
6. Handle Exception → 500 Internal Server Error

This resulted in ~25 lines of duplicated code per endpoint.

## Solution: `validate_and_update_config`

The validation wrapper function consolidates this pattern into a single reusable utility.

### Function Signature

```python
def validate_and_update_config(
    config_model: T,
    empty_message: str,
    success_message: str,
    error_context: str
) -> Dict[str, str]:
    """
    Validate request data and update configuration with error handling.

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
```

### Usage Example

#### Before (25 lines)

```python
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
```

#### After (7 lines)

```python
@router.patch("/discord", response_model=Dict[str, str])
async def update_discord_config(
    config: ConfigDiscordUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    return async_validate_and_update_config(
        config_model=config,
        empty_message="No Discord configuration updates provided",
        success_message="Discord configuration updated successfully",
        error_context="Discord configuration"
    )
```

## Benefits

1. **DRY Principle**: Eliminates ~54 lines of duplicated code across 3 endpoints
2. **Consistency**: Ensures all config endpoints handle errors identically
3. **Maintainability**: Bug fixes and improvements need only be made once
4. **Testability**: Single utility function is easier to test comprehensively
5. **Readability**: Endpoint handlers are more concise and focused

## Error Handling

The utility provides consistent error handling:

### 400 Bad Request
- **Trigger**: No fields provided in request (empty update)
- **Response**: Custom `empty_message` parameter
- **Example**: `{"detail": "No Discord configuration updates provided"}`

### 400 Bad Request (Validation)
- **Trigger**: `ValueError` raised during config update
- **Response**: `"Validation error: {error_message}"`
- **Example**: `{"detail": "Validation error: Invalid channel ID format"}`

### 500 Internal Server Error
- **Trigger**: Unexpected exception during update
- **Response**: `"Failed to update {error_context}: {error_message}"`
- **Example**: `{"detail": "Failed to update Discord configuration: Database connection failed"}`

### HTTPException Pass-Through
- **Trigger**: HTTPException raised during update
- **Response**: Original HTTPException re-raised as-is
- **Example**: Preserves custom status codes and messages

## Implementation Details

### Field Extraction

```python
update_data = config_model.model_dump(exclude_unset=True, exclude_none=True)
```

- `exclude_unset=True`: Only include fields explicitly set in request
- `exclude_none=True`: Exclude fields with `None` values
- Result: Only actual updates are sent to config manager

### Configuration Update

```python
config_manager.update(**update_data)
```

- Uses ConfigManager's `update()` method
- Automatically handles vault persistence
- Applies validation rules from Settings model

## Testing

The utility includes comprehensive unit tests in `tests/test_api_utils.py`:

```bash
# Run tests
pytest tests/test_api_utils.py -v

# Run with coverage
pytest tests/test_api_utils.py --cov=src.api.utils --cov-report=term-missing
```

### Test Coverage

- ✅ Successful update
- ✅ Empty update (no fields)
- ✅ Validation error (ValueError)
- ✅ Unexpected error handling
- ✅ HTTPException pass-through
- ✅ Partial updates (some fields)
- ✅ None value exclusion
- ✅ Async wrapper function

## Future Enhancements

Potential improvements for the utility:

1. **Generic Response Type**: Allow custom response models beyond `Dict[str, str]`
2. **Post-Update Hooks**: Optional callbacks after successful update
3. **Audit Logging**: Automatic logging of configuration changes
4. **Diff Tracking**: Return list of changed fields
5. **Rollback Support**: Automatic rollback on validation failure

## Migration Guide

To refactor existing endpoints to use the utility:

1. Import the utility:
   ```python
   from src.api.utils import async_validate_and_update_config
   ```

2. Replace endpoint body with utility call:
   ```python
   return async_validate_and_update_config(
       config_model=config,
       empty_message="No {section} configuration updates provided",
       success_message="{Section} configuration updated successfully",
       error_context="{section} configuration"
   )
   ```

3. Remove try/except boilerplate

4. Keep authentication and docstring

## Related Files

- **Implementation**: `src/api/utils.py`
- **Tests**: `tests/test_api_utils.py`
- **Example Usage**: `src/api/config_refactored_example.py`
- **Original Endpoints**: `src/api/config.py` (lines 395-546)

## See Also

- [FastAPI Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [Pydantic Model Export](https://docs.pydantic.dev/latest/concepts/serialization/)
- [DRY Principle](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)
