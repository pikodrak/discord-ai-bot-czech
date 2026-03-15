# Configuration Dependency Graph - Discord AI Bot Czech

## Overview
Analysis of configuration management across the discord-ai-bot-czech project, revealing critical issues with broken imports and overlapping functionality.

---

## Configuration Modules

### 1. `config.py` (Root Level) - REMOVED
```
Class: Config
Type: Simple class-based config with os.getenv
Status: DELETED - File removed during refactoring
```

**Fields:**
- (removed)

**Methods:**
- (removed)

**Used by:**
- None (file deleted)

---

### 2. `src/config.py` - ACTIVE ✅
```
Class: Settings (Pydantic BaseSettings)
Status: ACTIVE - Primary configuration module
```

**Fields:**
- Discord: discord_bot_token, discord_channel_id
- AI Keys: anthropic_api_key, claude_api_key, google_api_key, openai_api_key
- Behavior: bot_prefix, bot_language, log_level
- Admin: admin_username, admin_password, secret_key

**Implemented Methods:**
- `model_post_init()` - Pydantic hook
- `has_any_ai_key()` - Check if any AI key configured
- `get_available_providers()` - List available providers

**Available Functions:**
- ✅ `get_settings()` - Singleton factory
- ✅ `get_config_manager()` - Config manager factory
- ✅ `reload_settings()` - Reload configuration
- ✅ `BotSettings` - Alias for Settings class
- ❌ `reload_settings()` - Reload configuration
- ❌ `BotSettings` - Class or alias

**MISSING Methods (Called but not implemented):**
- ❌ `has_discord_config()` - Called by src/api/config.py
- ❌ `get_channel_ids_list()` - Called by src/api/config.py
- ❌ `get_available_llm_providers()` - Called by src/api/config.py, app.py
- ❌ `get_preferred_ai_provider()` - Called by src/api/config.py, app.py

**Used by:**
- ✅ `src/llm/factory.py` - Works (uses Settings directly)
- ❌ `src/api/config.py` - BROKEN (missing functions)
- ❌ `src/api/auth.py` - BROKEN (missing get_settings)
- ❌ `app.py` - BROKEN (missing get_settings)
- ❌ Tests - BROKEN

---

### 3. `bot/config.py` - REMOVED
```
Class: BotConfig (Pydantic BaseSettings)
Status: DELETED - File removed during refactoring
```

**Fields:**
- (removed)

**Methods:**
- (removed)

**Used by:**
- None (file deleted)

---

### 4. Configuration Loader Features - INTEGRATED INTO src/config.py ✅
```
Classes: AdvancedBotConfig, ConfigLoader, ConfigValidationError, Environment
Status: ACTIVE - Primary config for main bot application
```

**AdvancedBotConfig Fields:**
- All fields from BotConfig, plus:
- Environment: environment (enum: DEVELOPMENT, STAGING, PRODUCTION, TESTING)
- Retry: max_retry_attempts, retry_base_delay, retry_max_delay, retry_exponential_base
- Timeouts: http_timeout, llm_timeout, discord_timeout
- Reconnection: enable_auto_reconnect, max_reconnect_attempts, reconnect_base_delay
- Features: enable_message_caching, enable_graceful_degradation, enable_health_checks, enable_metrics
- Performance: message_queue_size, worker_threads, cache_ttl

**Methods:**
- `_validate_production_config()` - Production-specific checks
- `is_production()`, `is_development()` - Environment checks
- `to_dict(include_secrets=False)` - Export with secret masking
- All methods from BotConfig

**ConfigLoader:**
- `load(env_file)` - Load from .env and YAML
- `reload()` - Hot reload configuration
- `_load_yaml_config()` - Environment-specific YAML

**Used by:**
- ✅ `main.py` - Main bot entry point
- ✅ `main_enhanced.py` - Enhanced bot
- ✅ Examples and tests

---

### 5. `src/shared_config.py` - ACTIVE ✅
```
Class: SharedConfigLoader
Status: ACTIVE - Thread-safe hot-reload manager
```

**Features:**
- Thread-safe with RLock
- Multi-source loading (shared JSON, YAML, .env, env vars)
- Hot-reload support
- Sensitive key filtering on save

**Methods:**
- `load_config(force_reload=False)` - Load from all sources
- `save_config(config_dict)` - Save to shared JSON
- `get(key, default)`, `set(key, value)` - Runtime access

**Module Functions:**
- `get_shared_config_loader(project_root)` - Singleton factory
- `load_bot_config_from_shared(project_root)` - Convenience loader

**Used by:**
- ✅ `main.py` - Hot-reload functionality
- ✅ `src/api/config.py` - Config persistence

---

### 6. `src/api/config.py` - API Router
```
Type: FastAPI router with config management endpoints
Status: DEPENDS ON BROKEN src/config.py
```

**Pydantic Models:**
- ConfigDiscordUpdate, ConfigAIUpdate, ConfigBehaviorUpdate
- ConfigUpdate, ConfigResponse, ConfigSecretResponse, ValidationResult

**Endpoints:**
- `GET /` - Get current config
- `GET /secrets` - Get masked secrets (admin only)
- `PUT /` - Update config (admin only)
- `PATCH /discord`, `/ai`, `/behavior` - Partial updates
- `POST /reload` - Reload from disk
- `POST /hot-reload` - Trigger bot hot-reload via IPC
- `GET /validate` - Validate config
- `GET /export` - Export config

**Dependencies:**
- ❌ Imports from `src/config` (BROKEN)
- ✅ Imports from `src/shared_config` (OK)

---

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                     LEGACY CLUSTER (Isolated)                   │
│  ┌──────────┐                                                   │
│  │ bot.py   │──imports──▶ config.py (root)                     │
│  └──────────┘             [Config class]                        │
│     Status: OK            Status: LEGACY                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              FASTAPI CLUSTER (BROKEN ❌)                         │
│                                                                  │
│  ┌──────────┐    imports (BROKEN)    ┌──────────────────┐      │
│  │ app.py   │───────────────────────▶│ src/config.py    │      │
│  └──────────┘                         │   [Settings]     │      │
│       │                                └──────────────────┘      │
│       │ includes router                        ▲                │
│       ▼                                        │ imports        │
│  ┌─────────────────┐                          │ (BROKEN)       │
│  │ src/api/        │                          │                │
│  │  - config.py ───┼──────────────────────────┘                │
│  │  - auth.py ─────┼──────────────────────────┘                │
│  │  - bot.py       │                                            │
│  └─────────────────┘                                            │
│                                                                  │
│  Missing from src/config.py:                                    │
│   - get_settings()                                              │
│   - get_config_manager()                                        │
│   - reload_settings()                                           │
│   - Settings.has_discord_config()                               │
│   - Settings.get_channel_ids_list()                             │
│   - Settings.get_available_llm_providers()                      │
│   - Settings.get_preferred_ai_provider()                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              MAIN BOT CLUSTER (Working ✅)                       │
│                                                                  │
│  ┌──────────┐    imports    ┌──────────────────────────┐       │
│  │ main.py  │──────────────▶│ bot/config_loader.py     │       │
│  └──────────┘                │  [AdvancedBotConfig]     │       │
│       │                      │  [ConfigLoader]          │       │
│       │                      └──────────────────────────┘       │
│       │ imports                                                 │
│       ▼                                                         │
│  ┌──────────────────┐                                          │
│  │ src/shared_      │         also imported by                 │
│  │   config.py      │◀────────────────────┐                    │
│  │ [SharedConfig    │                     │                    │
│  │  Loader]         │                     │                    │
│  └──────────────────┘                     │                    │
│       ▲                                   │                    │
│       │                          ┌────────────────┐            │
│       └──────────────────────────│ src/api/       │            │
│          imported for hot-reload │   config.py    │            │
│                                  └────────────────┘            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 LLM INTEGRATION (Working ✅)                     │
│                                                                  │
│  ┌──────────────────┐    imports    ┌──────────────────┐       │
│  │ src/llm/         │──────────────▶│ src/config.py    │       │
│  │   factory.py     │                │   [Settings]     │       │
│  └──────────────────┘                └──────────────────┘       │
│                                                                  │
│  Usage: create_llm_client(settings: Settings)                   │
│  Status: OK - Uses Settings class directly                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Instantiation Patterns

### Pattern 1: Direct Instantiation
```python
# Works for all Pydantic configs
config = AdvancedBotConfig(discord_bot_token="token", ...)
config = Settings()
```
**Files:** tests/test_config_loader.py

---

### Pattern 2: Factory Function
```python
# Works - bot/config_loader.py
config = load_config(env_file=".env")

# Works - bot/config_loader.py
loader = ConfigLoader(config_dir)
config = loader.load(env_file)
```
**Files:** main.py, main_enhanced.py

---

### Pattern 3: Singleton Pattern
```python
# Works - src/shared_config.py
loader = get_shared_config_loader(project_root)
config_dict = loader.load_config(force_reload=True)
```
**Files:** main.py, src/api/config.py

---

### Pattern 4: Dependency Injection (BROKEN ❌)
```python
# BROKEN - get_settings() does not exist
from src.config import get_settings

def endpoint(settings: Settings = Depends(get_settings)):
    ...
```
**Files:** app.py, src/api/config.py, src/api/auth.py (ALL BROKEN)

---

### Pattern 5: Class-Level Access (LEGACY)
```python
# Works but legacy pattern
from config import Config

Config.DISCORD_TOKEN
Config.validate()
```
**Files:** bot.py

---

## Field Access Patterns

### Most Commonly Accessed Fields

1. **Discord Configuration:**
   - `discord_bot_token` / `DISCORD_TOKEN` (all configs)
   - `discord_channel_ids` / `discord_channel_id` (BotConfig, AdvancedBotConfig, Settings)
   - `discord_guild_id` (BotConfig, AdvancedBotConfig)

2. **AI Provider Keys:**
   - `anthropic_api_key` (all except root Config)
   - `google_api_key` (all configs)
   - `openai_api_key` (all configs)
   - `claude_api_key` (Settings only - alias for anthropic_api_key)

3. **Bot Behavior:**
   - `bot_language` (Settings, BotConfig, AdvancedBotConfig)
   - `bot_response_threshold` (BotConfig, AdvancedBotConfig)
   - `bot_max_history` (BotConfig, AdvancedBotConfig)

4. **Administrative:**
   - `admin_username`, `admin_password`, `secret_key` (Settings, BotConfig, AdvancedBotConfig)

5. **Advanced Features (AdvancedBotConfig only):**
   - Retry config, timeouts, reconnection settings
   - Feature flags (caching, graceful degradation, metrics)
   - Performance tuning (queue size, worker threads, cache TTL)

---

## Method Usage Patterns

### Validation Methods
```python
# Legacy
Config.validate() → bool

# Pydantic
has_any_ai_key() → bool
has_ai_provider(provider: str) → bool
get_available_providers() → list[str]
```

### Settings-Specific (MISSING ❌)
```python
# Called but NOT IMPLEMENTED
settings.has_discord_config() → bool  # ❌
settings.get_channel_ids_list() → list[str]  # ❌
settings.get_available_llm_providers() → list[str]  # ❌
settings.get_preferred_ai_provider() → str  # ❌
```

### AdvancedBotConfig-Specific
```python
config.is_production() → bool
config.is_development() → bool
config.to_dict(include_secrets=False) → dict
```

---

## Critical Issues Summary

### 🔴 CRITICAL - FastAPI App Cannot Start
```
Issue: Missing get_settings() function
Affected: app.py, src/api/config.py, src/api/auth.py
Impact: FastAPI app startup fails, all routes broken
```

### 🔴 CRITICAL - Runtime Errors in API Routes
```
Issue: Missing Settings methods
Methods: has_discord_config(), get_channel_ids_list(),
         get_available_llm_providers(), get_preferred_ai_provider()
Affected: src/api/config.py (lines 279, 281, 282, 283)
         app.py (line 211)
Impact: AttributeError when routes are called
```

### 🟡 HIGH - Overlapping Functionality
```
Issue: 5 different config classes with duplicate fields
Classes: Config, Settings, BotConfig, AdvancedBotConfig, SharedConfigLoader
Impact: Confusion, maintenance burden, inconsistent behavior
```

### 🟡 HIGH - Missing config reload in API
```
Issue: Missing reload_settings() function
Affected: src/api/config.py
Impact: POST /api/config/reload endpoint broken
```

---

## Migration Impact Analysis

### Files Requiring Changes

#### CRITICAL Priority (App Broken)
1. **src/config.py** - Implement missing functions and methods
2. **src/api/config.py** - Update imports or refactor dependency injection
3. **src/api/auth.py** - Update imports or refactor dependency injection
4. **app.py** - Update imports or refactor dependency injection

#### HIGH Priority (Functionality Broken)
5. **tests/test_config_management.py** - Update for new API
6. **tests/test_auth.py** - Update for new API

#### MEDIUM Priority (Consolidation)
7. **main.py** - Migrate to unified config
8. **bot/__init__.py** - Remove unused BotConfig export
9. **bot.py** - Migrate from legacy Config to unified config

#### LOW Priority (Cleanup)
10. **config.py (root)** - Deprecate after bot.py migration
11. **bot/config.py** - Deprecate if truly unused
12. Examples and other tests

---

## Recommended Migration Strategy

### Phase 1: CRITICAL FIXES (Immediate)
```python
# In src/config.py, add:

from functools import lru_cache
from typing import Optional

# Singleton instance
_settings: Optional[Settings] = None

@lru_cache()
def get_settings() -> Settings:
    """Get or create Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    get_settings.cache_clear()
    _settings = None
    return get_settings()

def get_config_manager() -> Settings:
    """Get config manager (Settings instance with update capability)."""
    return get_settings()

# Add missing methods to Settings class:
def has_discord_config(self) -> bool:
    return bool(self.discord_bot_token)

def get_channel_ids_list(self) -> list[str]:
    if not self.discord_channel_id:
        return []
    return [self.discord_channel_id]

def get_available_llm_providers(self) -> list[str]:
    return self.get_available_providers()

def get_preferred_ai_provider(self) -> Optional[str]:
    providers = self.get_available_providers()
    return providers[0] if providers else None
```

### Phase 2: CONSOLIDATION (High Priority)
1. Extend AdvancedBotConfig with all fields from Settings
2. Create ConfigManager wrapper class
3. Update all imports to use unified system
4. Migrate main.py to use unified config

### Phase 3: CLEANUP (COMPLETED)
1. ✅ Removed config.py (root) and bot/config.py
2. ✅ Updated bot.py to use src/config.Settings
3. ✅ Removed redundant config files
4. ⚠️ Documentation updates in progress

---

## Affected Modules by Category

| Category | Count | Files |
|----------|-------|-------|
| API Routes | 3 | src/api/{config,auth,bot}.py |
| Bot Core | 2 | bot.py, src/config.py |
| Tests | 6 | test_config_*.py, test_auth.py, etc. |
| Examples | 4 | *example.py |
| Support | 3 | src/llm/factory.py, src/shared_config.py, app.py |

**Total Affected:** 23 files out of 125 Python files (18.4%)

---

## Conclusion

The configuration system is **critically broken** due to missing functions in `src/config.py` that are imported and used by the FastAPI application. The immediate priority is implementing the missing functions and methods to restore functionality, followed by consolidating the overlapping configuration classes into a unified system based on `AdvancedBotConfig`.
