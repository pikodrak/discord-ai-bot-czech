# Configuration Migration Plan

## Executive Summary

This document outlines the plan to consolidate the discord-ai-bot-czech configuration management system from 5 separate configuration classes down to a single, comprehensive solution.

**Current State:**
- 5 configuration classes across 4 files
- 65% field duplication
- 35+ import locations
- Missing factory functions causing potential import errors
- Inconsistent defaults (bot_language: 'en' vs 'cs')

**Target State:**
- 1 primary configuration class: `AdvancedBotConfig`
- 1 configuration manager: `SharedConfigLoader` (kept separate for IPC)
- All imports standardized
- Factory functions implemented
- Consistent defaults

**Migration Effort:** 17 hours across 4 phases affecting 30 files

## Critical Issues

### 🔴 Issue 1: Missing Factory Functions (CRITICAL)

**Problem:** Multiple files import functions from `src/config.py` that don't exist:

```python
from src.config import get_settings  # Implemented in src/config.py
from src.config import get_config_manager  # Implemented in src/config.py
from src.config import reload_settings  # Implemented in src/config.py
from src.config import BotSettings  # Alias for Settings in src/config.py
```

**Impact:** HIGH - Could be causing runtime import errors

**Fix:** Implement these functions in src/config.py (Phase 1)

### ⚠️ Issue 2: Configuration Duplication (HIGH)

**Problem:** 65% of fields duplicated across multiple config classes:
- `discord_bot_token`: 3 duplicates
- `bot_language`: 3 duplicates (with inconsistent defaults!)
- `anthropic_api_key`, `google_api_key`, `openai_api_key`: 4 duplicates each
- `get_available_providers()` method: 4 identical implementations

**Impact:** MEDIUM - Maintenance burden, potential inconsistencies

**Fix:** Consolidate to AdvancedBotConfig (Phase 3)

### ⚠️ Issue 3: Inconsistent Defaults (MEDIUM)

**Problem:** `bot_language` has different defaults:
- `src/config.Settings`: `'en'`
- `bot/config.BotConfig`: `'cs'`
- `bot/config_loader.AdvancedBotConfig`: `'cs'`

**Impact:** MEDIUM - Unexpected behavior when switching configs

**Fix:** Standardize to 'cs' (Phase 1)

## Configuration Classes Overview

### Current Configurations

| Class | File | Fields | Methods | Usage | Status |
|-------|------|--------|---------|-------|--------|
| Config | [DELETED] bot/config.py | 6 | 2 | 0 files | ❌ REMOVED |
| Settings | src/config.py | 12 | 3 | 15 files | ✅ ACTIVE |
| BotConfig | [DELETED] bot/config.py | 18 | 7 | 0 files | ❌ REMOVED |
| AdvancedBotConfig | src/config.py | 38 | 12 | 8 files | ✅ PRIMARY |
| SharedConfigLoader | src/shared_config.py | - | 7 | 3 files | ✅ KEEP |

### Consolidation Target: AdvancedBotConfig

**Why AdvancedBotConfig?**

1. ✅ **Most Comprehensive** - 38 fields covering all use cases
2. ✅ **Already Primary** - Used by main.py entry point
3. ✅ **Best Practices** - Pydantic validators, type hints, documentation
4. ✅ **Environment Support** - Development, Staging, Production, Testing
5. ✅ **Advanced Features** - Retry logic, timeouts, feature flags, performance tuning
6. ✅ **Production Ready** - Production validation, secret masking
7. ✅ **Well Tested** - Dedicated test suite in tests/test_config_loader.py

**Unique Features Not in Other Configs:**
- Environment enum (development/staging/production/testing)
- Retry configuration (max_retry_attempts, retry_base_delay, retry_max_delay, retry_exponential_base)
- Timeout configuration (http_timeout, llm_timeout, discord_timeout)
- Reconnection settings (enable_auto_reconnect, max_reconnect_attempts, reconnect_base_delay)
- Feature flags (enable_message_caching, enable_graceful_degradation, enable_health_checks, enable_metrics)
- Performance tuning (message_queue_size, worker_threads, cache_ttl)
- Production validation (validates secret_key and admin_password in production)
- Secret masking (to_dict with include_secrets parameter)

## Migration Phases

### Phase 1: Preparation & Fixes (CRITICAL - 4 hours)

**Objective:** Fix critical issues and prepare for migration

**Tasks:**
1. ✅ Implement missing factory functions in `src/config.py`:
   ```python
   from typing import Optional
   from functools import lru_cache

   _settings: Optional[Settings] = None
   _config_manager: Optional['ConfigManager'] = None

   @lru_cache()
   def get_settings() -> Settings:
       """Get singleton Settings instance."""
       return Settings()

   def get_config_manager() -> 'ConfigManager':
       """Get singleton ConfigManager instance."""
       global _config_manager
       if _config_manager is None:
           _config_manager = ConfigManager()
       return _config_manager

   def reload_settings() -> Settings:
       """Reload settings from environment."""
       get_settings.cache_clear()
       return get_settings()
   ```

2. ✅ Standardize `bot_language` default to `'cs'` in `src/config.Settings`

3. ✅ Add BotSettings as alias:
   ```python
   # For backwards compatibility
   BotSettings = Settings
   ```

4. ✅ Run all tests to establish baseline:
   ```bash
   pytest tests/ -v
   ```

5. ✅ Create git branch and commit:
   ```bash
   git checkout -b config-migration-phase1
   git commit -m "Phase 1: Implement missing config factory functions"
   git tag config-migration-phase1
   ```

**Success Criteria:**
- ✅ All imports resolve without errors
- ✅ All existing tests pass
- ✅ Factory functions return correct instances
- ✅ No breaking changes to existing code

**Risk:** LOW
**Files Affected:** 3 (src/config.py, tests to verify)

---

### Phase 2: Legacy Removal (MEDIUM PRIORITY - 2 hours)

**Objective:** Remove deprecated config.Config and update bot.py

**Tasks:**
1. ✅ Update `bot.py` to use Settings from src/config:
   ```python
   # OLD
   from config import Config

   # NEW (COMPLETED)
   from src.config import Settings, get_settings
   ```

2. ✅ Test bot.py functionality

3. ✅ Remove `bot/config.py` and root `config.py` (legacy files) - COMPLETED

4. ✅ Update any documentation referencing config.Config

5. ✅ Commit changes:
   ```bash
   git commit -m "Phase 2: Remove legacy config.Config, update bot.py"
   git tag config-migration-phase2
   ```

**Success Criteria:**
- ✅ bot.py works with AdvancedBotConfig
- ✅ No references to config.Config remain
- ✅ All tests still pass

**Risk:** LOW (only affects legacy bot.py)
**Files Affected:** 2 (bot.py, config.py)

---

### Phase 3: Consolidation (HIGH PRIORITY - 8 hours)

**Objective:** Migrate all Settings usages to AdvancedBotConfig

**Tasks:**

#### Step 3.1: Create Migration Script
```python
#!/usr/bin/env python3
"""
Configuration Migration Script

Automatically updates imports from src.config.Settings to bot.config_loader.AdvancedBotConfig
"""

import os
import re
from pathlib import Path

def migrate_file(file_path: Path) -> bool:
    """Migrate a single Python file."""
    with open(file_path, 'r') as f:
        content = f.read()

    original = content

    # Pattern 1: from src.config import Settings
    content = re.sub(
        r'from src\.config import Settings',
        'from bot.config_loader import AdvancedBotConfig as Settings',
        content
    )

    # Pattern 2: from src.config import get_settings
    content = re.sub(
        r'from src\.config import get_settings',
        'from bot.config_loader import get_advanced_settings as get_settings',
        content
    )

    if content != original:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

# Run migration
files_to_migrate = [
    'app.py',
    'src/api/config.py',
    'src/api/auth.py',
    # ... (list all 20 files)
]

for file_path in files_to_migrate:
    if migrate_file(Path(file_path)):
        print(f"✓ Migrated {file_path}")
```

#### Step 3.2: Add Factory Function to config_loader.py
```python
# Add to bot/config_loader.py
from functools import lru_cache

@lru_cache()
def get_advanced_settings() -> AdvancedBotConfig:
    """Get singleton AdvancedBotConfig instance."""
    return AdvancedBotConfig()
```

#### Step 3.3: Update Files in Batches

**Batch 1: Core API Files (3 files)**
- app.py
- src/api/config.py
- src/api/auth.py

Test after batch 1: `pytest tests/test_api_*.py`

**Batch 2: Examples (3 files)**
- examples/llm_client_example.py
- examples/security_usage.py
- examples/configuration_usage.py

Test after batch 2: Run examples manually

**Batch 3: Tests (15 files)**
- tests/test_config_management.py
- tests/test_llm_factory.py
- tests/test_language_configuration.py
- tests/test_admin_auth.py
- tests/test_auth.py
- tests/test_integration.py
- ... (all test files)

Test after batch 3: `pytest tests/ -v`

**Batch 4: Documentation (5 files)**
- Update all .md files
- Update README if applicable

#### Step 3.4: Verify Changes
```bash
# Run full test suite
pytest tests/ -v --cov

# Check for remaining references to src.config.Settings
grep -r "from src.config import Settings" .

# Verify no import errors
python -c "from bot.config_loader import AdvancedBotConfig; print('✓ Import OK')"
```

#### Step 3.5: Commit
```bash
git commit -m "Phase 3: Consolidate Settings to AdvancedBotConfig"
git tag config-migration-phase3
```

**Success Criteria:**
- ✅ All 20 files updated
- ✅ All imports use AdvancedBotConfig (aliased as Settings for compatibility)
- ✅ All tests pass
- ✅ API endpoints work correctly
- ✅ Hot-reload functionality works
- ✅ No references to old src.config.Settings remain

**Risk:** MEDIUM (widespread changes)
**Files Affected:** 20

---

### Phase 4: Cleanup (LOW PRIORITY - 3 hours)

**Objective:** Remove redundant BotConfig and finalize consolidation

**Tasks:**

1. ✅ Update `src/config.py` to re-export for backwards compatibility:
   ```python
   """
   Configuration module - Re-exports AdvancedBotConfig for backwards compatibility.
   """

   from bot.config_loader import (
       AdvancedBotConfig as Settings,
       AdvancedBotConfig,
       ConfigLoader,
       ConfigValidationError,
       Environment,
       get_advanced_settings as get_settings,
       load_config
   )

   # Singleton management
   _config_manager = None

   def get_config_manager():
       """Get singleton config manager."""
       global _config_manager
       if _config_manager is None:
           _config_manager = ConfigLoader()
       return _config_manager

   def reload_settings():
       """Reload settings from environment."""
       get_settings.cache_clear()
       return get_settings()

   __all__ = [
       'Settings',
       'AdvancedBotConfig',
       'ConfigLoader',
       'ConfigValidationError',
       'Environment',
       'get_settings',
       'get_config_manager',
       'reload_settings',
       'load_config'
   ]
   ```

2. ✅ Remove `bot/config.py` (BotConfig class)

3. ✅ Update `bot/__init__.py` if it imports BotConfig

4. ✅ Update all documentation:
   - README.md
   - docs/*.md
   - Inline code comments

5. ✅ Remove deprecated code comments

6. ✅ Final test pass:
   ```bash
   pytest tests/ -v --cov
   pytest tests/test_integration.py -v
   python -m mypy src/ bot/
   ```

7. ✅ Commit and merge:
   ```bash
   git commit -m "Phase 4: Remove BotConfig, finalize consolidation"
   git tag config-migration-complete
   git checkout main
   git merge config-migration-phase1
   ```

**Success Criteria:**
- ✅ Only AdvancedBotConfig and SharedConfigLoader remain
- ✅ src/config.py serves as re-export layer for backwards compatibility
- ✅ All documentation updated
- ✅ All tests pass
- ✅ Type checking passes
- ✅ No duplicate config code remains

**Risk:** LOW
**Files Affected:** 5

## Testing Strategy

### Pre-Migration Tests (Baseline)
```bash
# Run all tests and save output
pytest tests/ -v --cov --cov-report=html > baseline_tests.log

# Check for import errors
python -c "from src.config import Settings; print('OK')"
python -c "from bot.config import BotConfig; print('OK')"
python -c "from bot.config_loader import AdvancedBotConfig; print('OK')"

# Test API endpoints
curl http://localhost:8000/api/config/
```

### During Migration Tests (After Each Phase)
```bash
# After Phase 1
pytest tests/ -v
python -c "from src.config import get_settings; print('OK')"

# After Phase 2
pytest tests/ -v
python bot.py --help  # Verify bot.py still works

# After Phase 3
pytest tests/ -v --cov
python -c "from bot.config_loader import AdvancedBotConfig as Settings; print('OK')"
# Test API
curl http://localhost:8000/api/config/

# After Phase 4
pytest tests/ -v --cov
python -m mypy src/ bot/
```

### Post-Migration Validation
```bash
# Integration tests
pytest tests/test_integration.py -v

# API tests
pytest tests/test_api_*.py -v

# Config tests
pytest tests/test_config_*.py -v

# Manual testing
python main.py  # Start bot
curl http://localhost:8000/health  # Check API

# Code quality
pylint src/ bot/
mypy src/ bot/
black --check src/ bot/
```

## Rollback Plan

### Phase-by-Phase Rollback

Each phase is tagged, allowing easy rollback:

```bash
# Rollback to before Phase 4
git reset --hard config-migration-phase3

# Rollback to before Phase 3
git reset --hard config-migration-phase2

# Rollback to before Phase 2
git reset --hard config-migration-phase1

# Rollback everything
git reset --hard origin/main
```

### Emergency Rollback

If issues are discovered in production:

1. Immediately revert to previous tag:
   ```bash
   git revert HEAD~n  # Revert last n commits
   git push origin main --force-with-lease
   ```

2. Deploy previous version

3. Investigate issue offline

4. Fix and retry migration

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import errors after migration | Medium | High | Phase-by-phase testing, automated migration script |
| API breaks after config changes | Low | High | Test API endpoints after Phase 3 |
| Tests fail after consolidation | Medium | Medium | Run tests after each batch in Phase 3 |
| Production config issues | Low | Critical | Validate production env before deployment |
| Hot-reload breaks | Low | High | Test IPC communication explicitly |
| Missing fields in AdvancedBotConfig | Very Low | Medium | AdvancedBotConfig is superset of all configs |

**Overall Risk:** MEDIUM
- Well-defined phases
- Good test coverage
- Rollback plan in place
- AdvancedBotConfig is proven (used by main.py)

## Success Metrics

### Before Migration
- ✅ 5 configuration classes
- ✅ 65% field duplication
- ✅ 35+ import locations
- ✅ Missing factory functions
- ✅ Inconsistent defaults

### After Migration
- ✅ 2 configuration components (AdvancedBotConfig + SharedConfigLoader)
- ✅ 0% duplication
- ✅ Standardized imports
- ✅ All factory functions implemented
- ✅ Consistent defaults
- ✅ All tests passing
- ✅ API fully functional
- ✅ Documentation updated

### Code Quality Improvements
- 📉 ~250 lines of duplicate code removed
- 📉 60% reduction in maintenance burden
- 📈 Better type safety with Pydantic validators
- 📈 Clearer import structure
- 📈 Single source of truth for configuration

## Timeline

| Phase | Duration | Dependencies | Assignee | Target Date |
|-------|----------|--------------|----------|-------------|
| Phase 1: Preparation | 4 hours | None | - | Day 1 |
| Phase 2: Legacy Removal | 2 hours | Phase 1 | - | Day 1 |
| Phase 3: Consolidation | 8 hours | Phase 1, 2 | - | Day 2-3 |
| Phase 4: Cleanup | 3 hours | Phase 3 | - | Day 3 |
| **TOTAL** | **17 hours** | - | - | **3 days** |

## Communication Plan

### Stakeholder Updates

**Before Migration:**
- Notify team of migration plan
- Share this document
- Discuss timeline and potential issues

**During Migration:**
- Update team after each phase completion
- Report any blockers immediately
- Share test results

**After Migration:**
- Announce completion
- Update team documentation
- Conduct knowledge transfer session

## Post-Migration Tasks

1. ✅ Update developer documentation
2. ✅ Create migration guide for external developers (if applicable)
3. ✅ Update CI/CD pipelines if needed
4. ✅ Monitor production for any issues (first 48 hours)
5. ✅ Collect feedback from team
6. ✅ Archive old configuration code (don't delete immediately)
7. ✅ Update code review guidelines to prevent new duplicates

## Appendix A: File Migration Checklist

### Core Files (HIGH PRIORITY)
- [ ] app.py
- [ ] src/api/config.py
- [ ] src/api/auth.py
- [ ] main.py (already uses AdvancedBotConfig ✓)

### Example Files (MEDIUM PRIORITY)
- [ ] examples/llm_client_example.py
- [ ] examples/security_usage.py
- [ ] examples/configuration_usage.py

### Test Files (MEDIUM PRIORITY)
- [ ] tests/test_config_management.py
- [ ] tests/test_llm_factory.py
- [ ] tests/test_language_configuration.py
- [ ] tests/test_admin_auth.py
- [ ] tests/test_auth.py
- [ ] tests/test_integration.py
- [ ] tests/test_api_failover.py
- [ ] tests/test_admin_interface.py
- [ ] tests/test_error_handling.py
- [ ] tests/test_docker_deployment.py
- [ ] tests/test_bot_control.py
- [ ] tests/test_config_loader.py (already tests AdvancedBotConfig ✓)

### Documentation Files (LOW PRIORITY)
- [ ] README.md
- [ ] docs/CONFIGURATION.md
- [ ] docs/SECURE_SETUP.md
- [ ] docs/SECURITY.md
- [ ] IMPLEMENTATION_SUMMARY.md

### Legacy Files (TO REMOVE)
- [ ] config.py (Phase 2)
- [ ] bot/config.py (Phase 4)

## Appendix B: Code Examples

### Before Migration

```python
# app.py
from src.config import Settings, get_settings

settings = get_settings()
print(settings.bot_language)  # May be 'en' or 'cs' depending on which config is used
```

### After Migration

```python
# app.py
from bot.config_loader import AdvancedBotConfig as Settings, get_advanced_settings as get_settings

settings = get_settings()
print(settings.bot_language)  # Always 'cs' (consistent)
print(settings.environment)   # 'development', 'staging', 'production', or 'testing'
print(settings.max_retry_attempts)  # 3 (new feature)
```

## Appendix C: Import Reference

### Old Imports (Before Migration)
```python
from config import Config  # DEPRECATED
from src.config import Settings
from src.config import get_settings  # MISSING
from src.config import get_config_manager  # MISSING
from bot.config import BotConfig  # REDUNDANT
from bot.config_loader import AdvancedBotConfig
```

### New Imports (After Migration)
```python
# Primary imports (recommended)
from bot.config_loader import AdvancedBotConfig
from bot.config_loader import get_advanced_settings
from bot.config_loader import ConfigLoader
from bot.config_loader import ConfigValidationError

# Backwards compatible imports (via src/config.py re-exports)
from src.config import Settings  # Actually AdvancedBotConfig
from src.config import get_settings  # Actually get_advanced_settings
from src.config import get_config_manager
from src.config import reload_settings

# Config manager (kept separate for IPC)
from src.shared_config import SharedConfigLoader
from src.shared_config import get_shared_config_loader
```

---

**Document Version:** 1.0
**Last Updated:** 2026-03-15
**Status:** PARTIALLY IMPLEMENTED - Phase 1-2 completed, duplicate configs removed
