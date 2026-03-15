# Configuration Management Guide

This guide explains the unified configuration management system used in the Discord AI Bot project.

## Overview

The project uses three complementary configuration modules:

1. **SharedConfigLoader** (`src/shared_config.py`) - Thread-safe configuration with hot-reload support
2. **AdvancedBotConfig** (`bot/config_loader.py`) - Bot-specific configuration with validation
3. **Settings** (`src/config.py`) - API configuration for web interface

## Configuration Modules

### 1. SharedConfigLoader

**Purpose**: Thread-safe configuration management with hot-reload support for shared state between processes.

**Use Cases**:
- Admin API that needs to update configuration without restart
- Shared configuration between bot and API processes
- Hot-reload scenarios where configuration changes need to propagate immediately

**Features**:
- Thread-safe read/write operations with RLock
- Multi-source configuration loading with priority system
- Automatic persistence to JSON file
- Sensitive data filtering

**Configuration Priority** (highest to lowest):
1. Shared config JSON file (`data/shared_config.json`)
2. Environment-specific YAML files (`config.{environment}.yaml`)
3. Environment variables
4. .env file

**Example Usage**:

```python
from pathlib import Path
from src.shared_config import get_shared_config_loader

# Get shared config loader (singleton per project root)
project_root = Path.cwd()
loader = get_shared_config_loader(project_root)

# Load configuration
config = loader.load_config()

# Get specific value
bot_language = loader.get('bot_language', default='cs')

# Update configuration (persisted to shared_config.json)
loader.set('bot_response_threshold', 0.75)

# Force reload from all sources
fresh_config = loader.load_config(force_reload=True)
```

**Sensitive Keys** (not saved to shared_config.json):
- `discord_bot_token`
- `anthropic_api_key`
- `google_api_key`
- `openai_api_key`
- `secret_key`
- `admin_password`

---

### 2. AdvancedBotConfig

**Purpose**: Pydantic-based configuration for bot initialization with strong validation and type checking.

**Use Cases**:
- Bot process initialization
- Environment-specific configuration (development, staging, production)
- Configuration validation before bot startup

**Features**:
- Pydantic validation with type hints
- Environment-based configuration loading
- Automatic directory creation (logs, data)
- Production environment safety checks
- Feature flags and performance tuning

**Supported Environments**:
- `development` - Default, relaxed validation
- `staging` - Pre-production testing
- `production` - Strict validation, requires secure defaults
- `testing` - For test suites

**Example Usage**:

```python
from bot.config_loader import load_config, ConfigValidationError, Environment

try:
    # Load configuration with validation
    config = load_config()

    # Access configuration
    print(f"Environment: {config.environment.value}")
    print(f"Language: {config.bot_language}")
    print(f"Channel IDs: {config.get_channel_ids()}")

    # Check AI provider availability
    if config.has_ai_provider("anthropic"):
        print("Claude is available")

    # Get list of available providers
    providers = config.get_available_providers()  # ['anthropic', 'google', ...]

    # Environment checks
    if config.is_production():
        print("Running in production mode")

    # Export configuration (with/without secrets)
    safe_dict = config.to_dict(include_secrets=False)

except ConfigValidationError as e:
    print(f"Configuration validation failed: {e}")
    for error in e.errors:
        print(f"  - {error}")
```

**Production Requirements**:
- `SECRET_KEY` must not be the default value
- `ADMIN_PASSWORD` must not be "admin"
- Debug logging triggers a warning

**Key Configuration Fields**:

```python
# Discord
discord_bot_token: str               # Required
discord_guild_id: Optional[int]
discord_channel_ids: Optional[str]   # Comma-separated

# AI Providers
anthropic_api_key: Optional[str]
google_api_key: Optional[str]
openai_api_key: Optional[str]

# Bot Behavior
bot_response_threshold: float = 0.6  # 0.0 to 1.0
bot_max_history: int = 50            # 1 to 200
bot_language: str = "cs"             # cs, en, sk, de, es, fr
bot_personality: str = "friendly"

# Retry Configuration
max_retry_attempts: int = 3          # 1 to 10
retry_base_delay: float = 1.0        # 0.1 to 60.0
retry_max_delay: float = 30.0        # 1.0 to 300.0

# Timeouts
http_timeout: float = 30.0           # 1.0 to 300.0
llm_timeout: float = 60.0            # 5.0 to 300.0
discord_timeout: float = 30.0        # 5.0 to 120.0

# Feature Flags
enable_auto_reconnect: bool = True
enable_message_caching: bool = True
enable_graceful_degradation: bool = True
enable_health_checks: bool = True
enable_metrics: bool = False

# Performance
message_queue_size: int = 100        # 10 to 1000
worker_threads: int = 4              # 1 to 32
cache_ttl: int = 3600                # 60 to 86400
```

---

### 3. Settings (API Configuration)

**Purpose**: FastAPI-compatible settings for web interface and API endpoints.

**Use Cases**:
- API server initialization
- FastAPI dependency injection
- Runtime configuration updates via ConfigManager
- Web dashboard configuration

**Features**:
- FastAPI Depends() compatible
- Runtime configuration updates
- Safe export with masked secrets
- Configuration validation

**Example Usage**:

```python
from src.config import get_settings, get_config_manager, reload_settings

# Get current settings (cached)
settings = get_settings()

print(f"API Host: {settings.api_host}")
print(f"API Port: {settings.api_port}")
print(f"Has Discord Config: {settings.has_discord_config()}")
print(f"Available Providers: {settings.get_available_llm_providers()}")
print(f"Preferred Provider: {settings.get_preferred_ai_provider()}")

# Get configuration manager for updates
config_manager = get_config_manager()

# Update configuration at runtime
config_manager.update(
    log_level="DEBUG",
    bot_language="en",
    bot_response_threshold=0.8
)

# Export safe configuration (masked secrets)
safe_config = config_manager.get_safe_dict()

# Reload from disk
reload_settings()
```

**In FastAPI Routes**:

```python
from fastapi import APIRouter, Depends
from src.config import Settings, get_settings

router = APIRouter()

@router.get("/config")
async def get_config(settings: Settings = Depends(get_settings)):
    return {
        "environment": settings.environment,
        "language": settings.bot_language,
        "providers": settings.get_available_llm_providers()
    }
```

---

## Configuration Files

### .env File

Primary source for environment variables. Should never be committed to git.

**Example**:

```bash
# Discord Configuration
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=123456789
DISCORD_CHANNEL_IDS=111111111,222222222,333333333

# AI Provider API Keys
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
OPENAI_API_KEY=sk-...

# Bot Behavior
BOT_RESPONSE_THRESHOLD=0.7
BOT_MAX_HISTORY=50
BOT_LANGUAGE=cs
BOT_PERSONALITY=friendly

# Database
DATABASE_URL=sqlite:///./data/bot_data.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password

# Environment
ENVIRONMENT=development
```

### config.{environment}.yaml

Environment-specific configuration files. Can be committed to git (don't include secrets).

**Example - config.development.yaml**:

```yaml
# Development environment configuration

# Bot Behavior
bot_language: cs
bot_personality: friendly
bot_response_threshold: 0.6
bot_max_history: 50

# Logging
log_level: DEBUG
log_file: logs/bot.log

# Feature Flags
enable_auto_reconnect: true
enable_message_caching: true
enable_graceful_degradation: true
enable_health_checks: true
enable_metrics: false

# Performance
message_queue_size: 100
worker_threads: 4
cache_ttl: 3600

# Retry Configuration
max_retry_attempts: 3
retry_base_delay: 1.0
retry_max_delay: 30.0

# Timeouts
http_timeout: 30.0
llm_timeout: 60.0
discord_timeout: 30.0
```

**Example - config.production.yaml**:

```yaml
# Production environment configuration

# Bot Behavior
bot_language: cs
bot_personality: professional
bot_response_threshold: 0.8
bot_max_history: 100

# Logging
log_level: INFO
log_file: logs/bot.log

# Feature Flags
enable_auto_reconnect: true
enable_message_caching: true
enable_graceful_degradation: true
enable_health_checks: true
enable_metrics: true

# Performance
message_queue_size: 500
worker_threads: 8
cache_ttl: 7200

# Retry Configuration
max_retry_attempts: 5
retry_base_delay: 2.0
retry_max_delay: 60.0

# Timeouts
http_timeout: 45.0
llm_timeout: 90.0
discord_timeout: 45.0
```

### data/shared_config.json

Runtime-updated configuration, automatically managed by SharedConfigLoader.

**Example**:

```json
{
  "bot_language": "cs",
  "bot_response_threshold": 0.75,
  "bot_max_history": 50,
  "log_level": "INFO",
  "environment": "development"
}
```

**Note**: Sensitive keys are automatically excluded from this file.

---

## Best Practices

### 1. Choose the Right Configuration Module

| Scenario | Use | Reason |
|----------|-----|--------|
| Bot initialization | `AdvancedBotConfig` | Strong validation, environment support |
| API endpoints | `Settings` | FastAPI compatible, dependency injection |
| Hot-reload from admin | `SharedConfigLoader` | Thread-safe, persistent updates |
| Multi-process shared state | `SharedConfigLoader` | Cross-process communication |

### 2. Configuration Loading Priority

When the same key is defined in multiple sources, the priority is:

1. **SharedConfigLoader**: `shared_config.json` (highest)
2. **Environment-specific YAML**: `config.{environment}.yaml`
3. **Environment variables**: From shell or container
4. **.env file**: Local development (lowest)

### 3. Sensitive Data Handling

**Never commit secrets to git**:
- Add `.env` to `.gitignore`
- Use environment variables in production
- Use secrets management services (AWS Secrets Manager, HashiCorp Vault)

**Safe export**:
```python
# AdvancedBotConfig
config.to_dict(include_secrets=False)  # Masks secrets with ***REDACTED***

# Settings / ConfigManager
config_manager.get_safe_dict()  # Automatically masks sensitive keys
```

### 4. Environment-Specific Configuration

```bash
# Development
export ENVIRONMENT=development

# Staging
export ENVIRONMENT=staging

# Production
export ENVIRONMENT=production
```

This automatically loads the correct `config.{environment}.yaml` file.

### 5. Configuration Validation

Always handle validation errors:

```python
from bot.config_loader import load_config, ConfigValidationError

try:
    config = load_config()
except ConfigValidationError as e:
    logger.error(f"Configuration validation failed: {e}")
    for error in e.errors:
        logger.error(f"  {error['loc']}: {error['msg']}")
    sys.exit(1)
```

### 6. Hot-Reload Pattern

For the admin API to update bot configuration without restart:

```python
from src.shared_config import get_shared_config_loader
from src.ipc import send_reload_command

# 1. Update shared configuration
loader = get_shared_config_loader(project_root)
loader.set('bot_language', 'en')

# 2. Notify bot process to reload
await send_reload_command()
```

The bot process should listen for reload signals:

```python
# In bot process
async def handle_reload_signal():
    loader = get_shared_config_loader(project_root)
    config = loader.load_config(force_reload=True)
    # Apply new configuration
    await bot.update_config(config)
```

---

## Testing Configuration

### Unit Tests

```python
import pytest
from bot.config_loader import AdvancedBotConfig
from pydantic import ValidationError

def test_valid_config():
    config = AdvancedBotConfig(
        discord_bot_token="test_token",
        bot_language="cs"
    )
    assert config.bot_language == "cs"

def test_invalid_language():
    with pytest.raises(ValidationError):
        AdvancedBotConfig(
            discord_bot_token="test_token",
            bot_language="invalid"
        )
```

### Integration Tests

```python
from src.shared_config import SharedConfigLoader
from pathlib import Path
import tempfile

def test_shared_config_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = SharedConfigLoader(Path(tmpdir))

        # Set value
        loader.set('test_key', 'test_value')

        # Create new loader instance
        loader2 = SharedConfigLoader(Path(tmpdir))
        config = loader2.load_config()

        # Should persist
        assert config['test_key'] == 'test_value'
```

---

## Troubleshooting

### Configuration Not Loading

**Problem**: Configuration values are not being applied.

**Solutions**:
1. Check file paths and ensure files exist
2. Verify environment variable names (use UPPERCASE)
3. Check configuration priority - higher priority sources override lower
4. Enable DEBUG logging to see configuration loading process

### Validation Errors

**Problem**: `ConfigValidationError` when loading configuration.

**Solutions**:
1. Check the error message for specific field issues
2. Verify value types (int, float, string, bool)
3. Check range constraints (e.g., `bot_response_threshold` must be 0.0-1.0)
4. Ensure required fields are provided

### Production Environment Errors

**Problem**: Bot fails to start in production with security errors.

**Solutions**:
1. Change `SECRET_KEY` from default value
2. Change `ADMIN_PASSWORD` from "admin"
3. Set `ENVIRONMENT=production` explicitly
4. Provide all required API keys

### Hot-Reload Not Working

**Problem**: Configuration updates don't take effect.

**Solutions**:
1. Ensure `SharedConfigLoader` is used for updates
2. Verify IPC communication between API and bot processes
3. Check that bot has reload signal handler implemented
4. Verify file permissions on `data/shared_config.json`

---

## API Reference

See the following files for detailed API documentation:

- **SharedConfigLoader**: `src/shared_config.py`
- **AdvancedBotConfig**: `bot/config_loader.py`
- **Settings**: `src/config.py`

## Examples

Complete working examples can be found in:

- `examples/configuration_usage.py` - Unified configuration examples
- `examples/config_error_handling_example.py` - Error handling with configuration
- `examples/test_config_api.py` - API endpoint testing

---

## Migration Guide

### From Old Configuration System

If you're migrating from a single-file configuration system:

1. **Identify your use case**:
   - Bot initialization → Use `AdvancedBotConfig`
   - API endpoints → Use `Settings`
   - Hot-reload/shared state → Use `SharedConfigLoader`

2. **Update imports**:
   ```python
   # Old
   from config import Config

   # New - for bot
   from bot.config_loader import load_config

   # New - for API
   from src.config import get_settings

   # New - for shared/hot-reload
   from src.shared_config import get_shared_config_loader
   ```

3. **Update configuration loading**:
   ```python
   # Old
   config = Config.load()

   # New - bot
   config = load_config()

   # New - API
   settings = get_settings()

   # New - shared
   loader = get_shared_config_loader(project_root)
   config = loader.load_config()
   ```

4. **Update tests**: See `tests/test_config_loader.py` and `tests/test_config_management.py` for examples.

---

## Changelog

### Version 2.0 - Unified Configuration System
- Added `SharedConfigLoader` for thread-safe hot-reload
- Added `AdvancedBotConfig` with Pydantic validation
- Maintained `Settings` for API compatibility
- Multi-source configuration with priority system
- Environment-specific YAML support
- Comprehensive test coverage

### Version 1.0 - Initial Configuration
- Basic configuration loading from .env
- Simple settings class
- No validation or environment support
