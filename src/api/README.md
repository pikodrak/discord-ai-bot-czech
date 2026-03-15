# API Module

This directory contains FastAPI routers and utilities for the Discord AI Bot admin interface.

## Structure

```
src/api/
├── __init__.py              # Package initialization
├── auth.py                  # Authentication endpoints and dependencies
├── bot.py                   # Bot management endpoints (start, stop, status)
├── config.py                # Configuration management endpoints
├── utils.py                 # Reusable API utilities (NEW)
└── config_refactored_example.py  # Example of refactored endpoints (NEW)
```

## Files

### `auth.py`
- JWT-based authentication
- User login/logout endpoints
- Admin user verification dependency
- Token generation and validation

### `bot.py`
- Bot process management (start, stop, restart)
- Bot status monitoring
- Health check endpoints

### `config.py`
- Configuration CRUD operations
- Encrypted credential storage
- Hot-reload configuration
- Validation endpoints

### `utils.py` ⭐ NEW
Reusable utilities for common API patterns:

- `validate_and_update_config()`: Validation wrapper for config updates
- `async_validate_and_update_config()`: Async version of validation wrapper

**Purpose**: Eliminate code duplication in config update endpoints

**Usage Example**:
```python
from src.api.utils import async_validate_and_update_config

@router.patch("/discord")
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

**Benefits**:
- Reduces endpoint code from ~25 lines to ~7 lines
- Ensures consistent error handling across all config endpoints
- Easier to maintain and test

### `config_refactored_example.py`
Demonstrates how to refactor existing config endpoints using `utils.py`.

Shows before/after comparison for:
- `update_discord_config()`
- `update_ai_config()`
- `update_behavior_config()`

## Common Patterns

### Error Handling

All endpoints use consistent error handling:

```python
try:
    # Endpoint logic
    return {"message": "Success"}
except ValueError as e:
    raise HTTPException(status_code=400, detail=f"Validation error: {e}")
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error: {e}")
```

With the validation wrapper, this is handled automatically.

### Authentication

Admin endpoints use the `get_current_admin_user` dependency:

```python
from src.api.auth import get_current_admin_user

@router.patch("/endpoint")
async def protected_endpoint(
    current_user: dict = Depends(get_current_admin_user)
):
    # Only authenticated admins can access
    pass
```

### Response Models

All endpoints define Pydantic response models:

```python
from pydantic import BaseModel

class ConfigResponse(BaseModel):
    discord_configured: bool
    channels: List[str]
    # ...

@router.get("/", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    return ConfigResponse(...)
```

## Testing

Run API tests with:

```bash
# Test all API modules
pytest tests/test_api*.py -v

# Test specific module
pytest tests/test_api_utils.py -v

# With coverage
pytest tests/test_api*.py --cov=src.api --cov-report=html
```

## Documentation

- **Detailed Guide**: See `docs/api_utils_guide.md` for comprehensive documentation
- **API Docs**: Visit `/docs` when server is running for interactive Swagger UI
- **ReDoc**: Visit `/redoc` for alternative API documentation

## Router Registration

Routers are registered in `app.py`:

```python
from src.api import auth, bot, config

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(config.router, prefix="/api/config", tags=["Configuration"])
app.include_router(bot.router, prefix="/api/bot", tags=["Bot Management"])
```

## Security

- All sensitive endpoints require authentication
- Secrets are masked in responses
- Credentials stored in encrypted vault
- CORS configured for production

## Future Improvements

- [ ] Rate limiting for endpoints
- [ ] Request/response logging middleware
- [ ] Webhook support for configuration changes
- [ ] WebSocket endpoints for real-time updates
- [ ] API versioning (v1, v2)
