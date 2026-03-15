# Configuration Module Dependency Graph

## Visual Dependency Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION ECOSYSTEM                          │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  [DELETED]       │
│  bot/config.py   │
│  config.py       │
│  [REMOVED]       │
└──────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  src/config.py                                                   │
│  [ACTIVE - INCOMPLETE]                                           │
│  • Settings                                                      │
│  • 12 fields (minimal set)                                       │
│  • Pydantic BaseSettings                                         │
│                                                                  │
│  EXPORTED FUNCTIONS (available):                                 │
│    - get_settings() → Settings                                   │
│    - get_config_manager() → ConfigManager                        │
│    - reload_settings() → Settings                                │
│    - BotSettings (alias for Settings)                            │
└──────────────────────────────────────────────────────────────────┘
         ▲                ▲                ▲                ▲
         │                │                │                │
         │                │                │                │
    ┌────────┐      ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ app.py │      │ src/api/ │    │  tests/  │    │examples/ │
    │        │      │ auth.py  │    │  *test*  │    │  *.py    │
    │FastAPI │      │ config.py│    │  15 files│    │  3 files │
    └────────┘      └──────────┘    └──────────┘    └──────────┘

┌──────────────────────────────────────────────────────────────────┐
│  [DELETED] bot/config.py                                         │
│  [REMOVED - Was redundant with Settings]                         │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  src/config.py (CANONICAL LOCATION)                              │
│  [PRIMARY CONFIG - COMPREHENSIVE]                                │
│  • Settings (comprehensive configuration class)                  │
│  • ConfigLoader (YAML support)                                   │
│  • ConfigValidationError                                         │
│  • Environment enum                                              │
│                                                                  │
│  Unique Features:                                                │
│    - Environment support (dev/staging/prod/test)                 │
│    - Retry configuration (4 fields)                              │
│    - Timeout configuration (3 fields)                            │
│    - Reconnection settings (3 fields)                            │
│    - Feature flags (4 fields)                                    │
│    - Performance tuning (3 fields)                               │
│    - Production validation                                       │
│    - Secret masking in to_dict()                                 │
└──────────────────────────────────────────────────────────────────┘
         ▲                ▲                ▲
         │                │                │
         │                │                │
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │ main.py │    │main_     │    │ tests/   │
    │ (3 uses)│    │enhanced  │    │test_     │
    │[PRIMARY]│    │  .py     │    │config_   │
    └─────────┘    └──────────┘    │loader.py │
                                   └──────────┘

┌──────────────────────────────────────────────────────────────────┐
│  src/shared_config.py                                            │
│  [ACTIVE - CONFIG MANAGER]                                       │
│  • SharedConfigLoader                                            │
│  • Thread-safe config operations                                 │
│  • Hot-reload support                                            │
│  • Multi-source loading (JSON + YAML + .env)                     │
│                                                                  │
│  Data Flow:                                                      │
│    1. .env file (base)                                           │
│    2. YAML config (environment-specific)                         │
│    3. Environment variables (overrides)                          │
│    4. Shared JSON file (hot-reload, highest priority)            │
│                                                                  │
│  Storage: data/shared_config.json                                │
└──────────────────────────────────────────────────────────────────┘
         ▲                           ▲
         │                           │
         │                           │
    ┌─────────┐               ┌──────────┐
    │ main.py │               │src/api/  │
    │(IPC     │               │config.py │
    │reload)  │               │(persist) │
    └─────────┘               └──────────┘

┌──────────────────────────────────────────────────────────────────┐
│  src/api/config.py                                               │
│  [FASTAPI ROUTER - CONFIG MANAGEMENT API]                        │
│  • 10 REST endpoints                                             │
│  • Request/Response models (6 Pydantic models)                   │
│                                                                  │
│  Endpoints:                                                      │
│    GET  /        - Get config (masked)                           │
│    GET  /secrets - Get secrets (masked, admin only)              │
│    PUT  /        - Update config (admin only)                    │
│    PATCH /discord   - Update Discord config                      │
│    PATCH /ai        - Update AI config                           │
│    PATCH /behavior  - Update bot behavior                        │
│    POST /reload     - Reload from disk                           │
│    POST /hot-reload - Trigger bot hot-reload (IPC)               │
│    GET  /validate   - Validate config                            │
│    GET  /export     - Export config                              │
│                                                                  │
│  Dependencies:                                                   │
│    → src.config (Settings, get_settings, etc.)                   │
│    → src.shared_config (SharedConfigLoader)                      │
│    → src.ipc (send_reload_command)                               │
└──────────────────────────────────────────────────────────────────┘
```

## Field Coverage Comparison

| Field Name | Config | Settings | BotConfig | AdvancedBotConfig |
|------------|--------|----------|-----------|-------------------|
| **Discord Settings** | | | | |
| discord_bot_token | ✓ | ✓ | ✓ | ✓ |
| discord_guild_id | ✗ | ✗ | ✓ | ✓ |
| discord_channel_id(s) | ✗ | ✓ | ✓ | ✓ |
| **AI Provider Keys** | | | | |
| anthropic_api_key | ✓ | ✓ | ✓ | ✓ |
| google_api_key | ✓ | ✓ | ✓ | ✓ |
| openai_api_key | ✓ | ✓ | ✓ | ✓ |
| claude_api_key | ✗ | ✓ | ✗ | ✗ |
| **Bot Behavior** | | | | |
| bot_prefix | ✗ | ✓ | ✗ | ✗ |
| bot_language | ✗ | ✓ | ✓ | ✓ |
| bot_personality | ✗ | ✗ | ✓ | ✓ |
| bot_response_threshold | ✗ | ✗ | ✓ | ✓ |
| bot_max_history | ✗ | ✗ | ✓ | ✓ |
| **Logging** | | | | |
| log_level | ✗ | ✓ | ✓ | ✓ |
| log_file | ✗ | ✗ | ✓ | ✓ |
| **API Settings** | | | | |
| api_host | ✗ | ✗ | ✓ | ✓ |
| api_port | ✗ | ✗ | ✓ | ✓ |
| **Admin Settings** | | | | |
| admin_username | ✗ | ✓ | ✓ | ✓ |
| admin_password | ✗ | ✓ | ✓ | ✓ |
| secret_key | ✗ | ✓ | ✓ | ✓ |
| **Database** | | | | |
| database_url | ✗ | ✗ | ✓ | ✓ |
| **Environment** | | | | |
| environment | ✗ | ✗ | ✗ | ✓ |
| **Retry/Timeout (14 fields)** | ✗ | ✗ | ✗ | ✓ |
| **Feature Flags (4 fields)** | ✗ | ✗ | ✗ | ✓ |
| **Performance (3 fields)** | ✗ | ✗ | ✗ | ✓ |
| **TOTAL FIELDS** | 6 | 12 | 18 | 38 |

## Method Coverage Comparison

| Method | Config | Settings | BotConfig | AdvancedBotConfig |
|--------|--------|----------|-----------|-------------------|
| get_available_providers() | ✓ | ✓ | ✓ | ✓ |
| has_any_ai_key() | ✗ | ✓ | ✗ | ✓ |
| has_ai_provider(provider) | ✗ | ✗ | ✓ | ✓ |
| get_channel_ids() | ✗ | ✗ | ✓ | ✓ |
| validate() | ✓ | ✗ | ✗ | ✗ |
| is_production() | ✗ | ✗ | ✗ | ✓ |
| is_development() | ✗ | ✗ | ✗ | ✓ |
| to_dict(include_secrets) | ✗ | ✗ | ✗ | ✓ |
| model_post_init() | ✗ | ✓ | ✓ | ✓ |
| _ensure_directories() | ✗ | ✗ | ✓ | ✓ |
| _validate_production_config() | ✗ | ✗ | ✗ | ✓ |
| **TOTAL METHODS** | 2 | 3 | 7 | 12 |

## Import Usage Map

```
main.py (PRIMARY ENTRY POINT)
├── from bot.config_loader import AdvancedBotConfig ✓ (3 usages)
├── from bot.config_loader import load_config ✓
├── from bot.config_loader import ConfigValidationError ✓
└── from src.shared_config import SharedConfigLoader ✓

app.py (FASTAPI APP)
├── from src.config import get_settings ✓
└── from src.config import Settings ✓

src/api/config.py (CONFIG API)
├── from src.config import Settings ✓
├── from src.config import BotSettings ✓
├── from src.config import get_settings ✓
├── from src.config import get_config_manager ✓
├── from src.config import reload_settings ✓
└── from src.shared_config import get_shared_config_loader ✓

src/api/auth.py
├── from src.config import Settings ✓
└── from src.config import get_settings ✓

bot.py (MAIN BOT ENTRY POINT)
├── from src.config import Settings ✓
└── from src.config import get_settings ✓

tests/* (15 FILES)
├── from src.config import Settings ✓
├── from src.config import get_settings ✓
└── from src.config import ConfigValidationError ✓

examples/* (3 FILES)
├── from src.config import get_settings ✓
└── from src.config import load_config ✓
```

Legend:
- ✓ Import exists and is valid
- ⚠ Import referenced but function/class not found in module
- ✗ Import is deprecated

## Duplication Hotspots

### Fields with 100% Duplication (appear in all 4 configs)
1. `anthropic_api_key`
2. `google_api_key`
3. `openai_api_key`

### Fields with 75% Duplication (appear in 3 configs)
1. `discord_bot_token`
2. `bot_language` (⚠ INCONSISTENT DEFAULTS: en vs cs)
3. `log_level`
4. `admin_username`
5. `admin_password`
6. `secret_key`

### Methods with 100% Duplication (same logic, 4 implementations)
1. `get_available_providers()` - Checks which AI providers have keys configured

### Methods with 75% Duplication (same logic, 3 implementations)
1. `has_any_ai_key()` - Returns bool if any AI key exists
2. `get_channel_ids()` - Parses comma-separated channel IDs (2 implementations)

## Critical Issues

### ✅ RESOLVED: Factory Functions Now Available
The following functions are now available in `src/config.py`:

```python
# Available in src/config.py
from src.config import get_settings  # ✅ AVAILABLE
from src.config import get_config_manager  # ✅ AVAILABLE
from src.config import reload_settings  # ✅ AVAILABLE
from src.config import BotSettings  # ✅ AVAILABLE (alias for Settings)
```

**Status:** All factory functions have been implemented.

**Recommended Fix:**
```python
# Add to src/config.py
_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    """Get or create singleton Settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings_instance
    _settings_instance = Settings()
    return _settings_instance
```

### ⚠️ WARNING: Inconsistent Defaults

| Field | Config | Settings | BotConfig | AdvancedBotConfig |
|-------|--------|----------|-----------|-------------------|
| bot_language | - | **en** | **cs** | **cs** |

This inconsistency could cause unexpected behavior when switching between configs.

## Migration Impact Assessment

### Phase 1: Preparation (Low Risk)
- **Files Affected:** 3
- **Users Impacted:** None (internal changes only)
- **Risk:** Low
- **Rollback:** Easy (git revert)

### Phase 2: Legacy Removal (Low Risk)
- **Files Affected:** 2 (bot.py, config.py)
- **Users Impacted:** Anyone using old bot.py
- **Risk:** Low (appears to be legacy code)
- **Rollback:** Easy

### Phase 3: Consolidation (Medium Risk)
- **Files Affected:** 20+
- **Users Impacted:** All API users, test suite
- **Risk:** Medium (widespread changes)
- **Rollback:** Moderate (requires coordinated revert)
- **Testing Required:** Full test suite, integration tests, API tests

### Phase 4: Cleanup (Low Risk)
- **Files Affected:** 5
- **Users Impacted:** None (removes duplicates)
- **Risk:** Low
- **Rollback:** Easy

## Recommended Consolidation Target

**✅ bot/config_loader.py::AdvancedBotConfig**

### Reasons:
1. **Most Comprehensive:** 38 fields vs 6-18 in others
2. **Already Primary:** Used by main.py (primary entry point)
3. **Best Practices:** Includes validators, environment support, production checks
4. **Feature Rich:** Retry, timeout, feature flags, performance tuning
5. **Well Tested:** Has dedicated test file (test_config_loader.py)
6. **Future Proof:** Designed for scalability with Environment enum

### Migration Path:
```
Phase 1: Fix src/config.py (add missing functions)
         ↓
Phase 2: Remove config.py, update bot.py
         ↓
Phase 3: Migrate Settings → AdvancedBotConfig (20 files)
         ↓
Phase 4: Remove BotConfig, re-export AdvancedBotConfig from src/config.py
```

## Files Requiring Updates (30 total)

### High Priority (Core Functionality)
1. `app.py` - FastAPI application
2. `src/api/config.py` - Config management API
3. `src/api/auth.py` - Authentication
4. `main.py` - Already uses AdvancedBotConfig ✓

### Medium Priority (Examples & Documentation)
5. `examples/llm_client_example.py`
6. `examples/security_usage.py`
7. `examples/configuration_usage.py`
8. `docs/**/*.md` - Documentation updates

### Low Priority (Tests)
9-23. `tests/*.py` - 15 test files

### Legacy (Remove)
24. `bot.py` - Legacy bot implementation
25. `config.py` - Legacy config class
26. `bot/config.py` - Redundant BotConfig

## Estimated Effort

| Phase | Hours | Files | Risk | Priority |
|-------|-------|-------|------|----------|
| Phase 1: Preparation | 4 | 3 | Low | CRITICAL |
| Phase 2: Legacy Removal | 2 | 2 | Low | Medium |
| Phase 3: Consolidation | 8 | 20 | Medium | High |
| Phase 4: Cleanup | 3 | 5 | Low | Low |
| **TOTAL** | **17** | **30** | - | - |
