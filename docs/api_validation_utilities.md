# API Validation Utilities

## Overview

The `src/api/validation.py` module provides reusable validation wrapper functions that handle request validation, error catching, and HTTPException raising in a consistent manner across all API endpoints.

This eliminates code duplication and ensures consistent error handling throughout the API.

## Problem Solved

### Before (Duplicated Code)

Each endpoint had repetitive error handling:

```python
@router.patch("/discord")
async def update_discord_config(config: ConfigDiscordUpdate) -> Dict[str, str]:
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

**Issues:**
- 25+ lines of code per endpoint
- Same error handling logic duplicated 4+ times
- Easy to introduce inconsistencies
- Hard to maintain and update

### After (Using Validation Utilities)

Clean, focused endpoint logic:

```python
@router.patch("/discord")
@validate_config_update(
    config_type="Discord configuration",
    success_message="Discord configuration updated successfully"
)
async def update_discord_config(config: ConfigDiscordUpdate) -> Dict[str, str]:
    config_manager = get_config_manager()
    update_data = extract_update_data(config)
    validate_update_data(update_data, "Discord configuration")

    config_manager.update(**update_data)
    return {"message": "Discord configuration updated successfully"}
```

**Benefits:**
- ~7 lines of code per endpoint (72% reduction)
- Error handling logic in one place
- Consistent behavior across all endpoints
- Easy to maintain and update

## Functions

### `validate_config_update(config_type, success_message)`

Decorator that wraps endpoint handlers to provide consistent error handling.

**Parameters:**
- `config_type` (str): Human-readable type of configuration being updated
  - Examples: "Discord configuration", "AI configuration", "behavior configuration"
- `success_message` (str, optional): Message to return on successful update
  - Default: "Configuration updated successfully"

**Error Handling:**
- `ValueError` → 400 Bad Request with "Validation error: {message}"
- `HTTPException` → Re-raised as-is (from wrapped function)
- `Exception` → 500 Internal Server Error with "Failed to update {config_type}: {message}"

**Example:**

```python
@validate_config_update(
    config_type="Discord configuration",
    success_message="Discord configuration updated successfully"
)
async def update_discord_config(config: ConfigDiscordUpdate) -> Dict[str, str]:
    # Your endpoint logic here
    pass
```

### `validate_update_data(update_data, config_type)`

Validates that update data is not empty.

**Parameters:**
- `update_data` (Dict[str, Any]): Dictionary of configuration updates
- `config_type` (str): Human-readable type of configuration being updated

**Raises:**
- `HTTPException` (400): If update_data is empty

**Example:**

```python
update_data = extract_update_data(config)
validate_update_data(update_data, "Discord configuration")
```

### `extract_update_data(config)`

Extracts update data from Pydantic model, excluding unset and None values.

**Parameters:**
- `config` (BaseModel): Pydantic model instance containing configuration updates

**Returns:**
- `Dict[str, Any]`: Dictionary with only set and non-None values

**Example:**

```python
config = ConfigDiscordUpdate(discord_channel_ids="123456789")
update_data = extract_update_data(config)
# Returns: {"discord_channel_ids": "123456789"}
```

## Usage Patterns

### Pattern 1: Decorator-Based (Recommended)

Use the decorator for most endpoints:

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
    update_data = extract_update_data(config)
    validate_update_data(update_data, "Discord configuration")

    config_manager.update(**update_data)
    return {"message": "Discord configuration updated successfully"}
```

### Pattern 2: Inline Validation

For more control over the flow:

```python
@router.patch("/discord")
async def update_discord_config(
    config: ConfigDiscordUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    config_manager = get_config_manager()

    # Extract and validate
    update_data = extract_update_data(config)
    validate_update_data(update_data, "Discord configuration")

    # Perform update
    config_manager.update(**update_data)

    # Custom response logic
    return {
        "message": "Discord configuration updated successfully",
        "updated_fields": list(update_data.keys())
    }
```

### Pattern 3: Custom Error Handling

Combine decorator with custom error handling:

```python
@router.patch("/discord")
@validate_config_update("Discord configuration")
async def update_discord_config(
    config: ConfigDiscordUpdate,
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, str]:
    config_manager = get_config_manager()
    update_data = extract_update_data(config)
    validate_update_data(update_data, "Discord configuration")

    # Custom validation
    if "discord_channel_ids" in update_data:
        channel_ids = update_data["discord_channel_ids"].split(",")
        if len(channel_ids) > 10:
            raise ValueError("Maximum 10 channel IDs allowed")

    config_manager.update(**update_data)
    return {"message": "Discord configuration updated successfully"}
```

## Migration Guide

### Step 1: Add Import

```python
from src.api.validation import (
    validate_config_update,
    validate_update_data,
    extract_update_data
)
```

### Step 2: Refactor Endpoint

**Before:**

```python
@router.patch("/discord")
async def update_discord_config(config: ConfigDiscordUpdate) -> Dict[str, str]:
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

**After:**

```python
@router.patch("/discord")
@validate_config_update(
    config_type="Discord configuration",
    success_message="Discord configuration updated successfully"
)
async def update_discord_config(config: ConfigDiscordUpdate) -> Dict[str, str]:
    config_manager = get_config_manager()
    update_data = extract_update_data(config)
    validate_update_data(update_data, "Discord configuration")

    config_manager.update(**update_data)
    return {"message": "Discord configuration updated successfully"}
```

### Step 3: Test

Run the existing tests to ensure behavior hasn't changed:

```bash
pytest tests/test_config_management.py -v
```

## Testing

The validation utilities are fully tested in `tests/test_api_validation.py`:

```bash
# Run all validation tests
pytest tests/test_api_validation.py -v

# Run specific test class
pytest tests/test_api_validation.py::TestValidateConfigUpdateDecorator -v

# Run with coverage
pytest tests/test_api_validation.py --cov=src.api.validation --cov-report=html
```

### Test Coverage

- ✅ Empty update data validation
- ✅ ValueError catching (400 Bad Request)
- ✅ Generic exception catching (500 Internal Server Error)
- ✅ HTTPException re-raising
- ✅ Custom config types in error messages
- ✅ Function metadata preservation
- ✅ Arguments and kwargs handling
- ✅ Pydantic model integration
- ✅ Extract update data with partial fields
- ✅ Extract update data excluding None values

## Benefits Summary

### Code Reduction
- **Before:** ~25 lines per endpoint
- **After:** ~7 lines per endpoint
- **Reduction:** 72% less code

### Consistency
- ✅ Same HTTP status codes for same error types
- ✅ Consistent error message format
- ✅ Uniform validation across all endpoints

### Maintainability
- ✅ Change error handling logic in one place
- ✅ Easy to add new validation rules
- ✅ Less code duplication

### Readability
- ✅ Endpoint logic is clear and focused
- ✅ Error handling doesn't obscure business logic
- ✅ Self-documenting through decorator parameters

### Testability
- ✅ Validation logic tested independently
- ✅ Easier to mock and test endpoints
- ✅ Clear separation of concerns

## Error Response Format

All validation errors follow a consistent format:

### 400 Bad Request (Validation Error)

```json
{
  "detail": "Validation error: Invalid channel ID format"
}
```

### 400 Bad Request (Empty Update)

```json
{
  "detail": "No Discord configuration updates provided"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to update Discord configuration: Database connection failed"
}
```

## Best Practices

1. **Use the decorator for standard CRUD endpoints**
   - Provides consistent error handling
   - Reduces boilerplate code

2. **Use inline validation for complex flows**
   - When you need custom logic between validation steps
   - When you need to return custom response data

3. **Always validate update data is not empty**
   - Prevents unnecessary database operations
   - Provides clear error messages to clients

4. **Use descriptive config_type names**
   - Makes error messages more helpful
   - Improves debugging experience

5. **Keep success messages consistent**
   - Use past tense: "updated", "created", "deleted"
   - Be specific about what was updated

## Related Files

- `src/api/validation.py` - Validation utilities implementation
- `tests/test_api_validation.py` - Comprehensive test suite
- `examples/validation_usage_example.py` - Usage examples and patterns
- `src/api/config.py` - Config endpoints (refactoring target)

## Future Enhancements

Potential improvements to consider:

1. **Request logging decorator**
   - Log all incoming requests with metadata
   - Track request duration and status

2. **Rate limiting wrapper**
   - Protect endpoints from abuse
   - Per-user rate limits

3. **Response caching decorator**
   - Cache GET endpoint responses
   - Configurable TTL

4. **Audit logging wrapper**
   - Track who made what changes
   - Store audit trail in database

5. **Schema validation decorator**
   - Additional validation beyond Pydantic
   - Business rule enforcement
