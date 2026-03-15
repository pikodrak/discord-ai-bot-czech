# Import Structure Test Report

**Date:** 2026-03-15
**Project:** discord-ai-bot-czech
**Python Version:** 3.9.2
**Test Script:** test_imports.py

## Executive Summary

Tested 50 modules across the `src/` and `bot/` packages. **21 passed** (42%) and **29 failed** (58%).

### Critical Issues Identified

1. **Python 3.10+ Type Hint Syntax** (19 modules)
2. **Placeholder Files** (8 modules)
3. **Missing Dependencies** (6 modules)
4. **Missing Packages** (4 modules)

---

## Test Results

### ✅ Passing Modules (21/50)

#### src/ package (10 modules)
- `src.retry_strategy`
- `src.logger`
- `src.client_enhanced`
- `src.providers`
- `src.exceptions`
- `src.health`
- `src.interest_filter`
- `src.shared_config`
- `src.utils`

#### bot/ package (11 modules)
- `bot` (package init)
- `bot.config_loader`
- `bot.health`
- `bot.interest_filter`
- `bot.lifecycle`
- `bot.errors`
- `bot.graceful_degradation`
- `bot.context_manager`
- `bot.cogs.admin`
- `bot.utils` (package init)
- `bot.utils.logger`
- `bot.utils.message_filter`

---

## ❌ Failing Modules by Category

### Category 1: Python 3.10+ Type Hint Syntax (19 modules)

**Issue:** Using `type | None` syntax which requires Python 3.10+, but system runs Python 3.9.2

**Error:** `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`

**Affected Modules:**
- `src.llm` (package init)
- `src.llm.retry_strategy`
- `src.llm.client_enhanced`
- `src.llm.providers`
- `src.llm.exceptions`
- `src.llm.client`
- `src.llm.language_utils`
- `src.llm.factory`
- `src.llm.base`
- `src.llm.circuit_breaker`
- `bot.cogs.ai_chat` (imports src.llm modules)

**Examples Found in src/llm/base.py:**
```python
# Line 25: tokens_used: int | None = None
# Line 26: metadata: dict[str, Any] | None = None
# Line 33: model: str | None = None
```

**Fix Required:** Replace `X | None` with `Optional[X]` from `typing` module

---

### Category 2: Placeholder Files (8 modules)

**Issue:** Files contain text descriptions instead of valid Python code

**Error:** `SyntaxError: invalid syntax (file.py, line 1)`

**Affected Modules:**

1. **src.config**
   - Content: "Already using src.config properly"
   - Actual implementation likely exists elsewhere

2. **src.errors**
   - Content: "Already implemented - see file at workspace/projects/discord-ai-bot-czech/bot/errors.py"
   - Points to: `bot/errors.py` ✅ (exists and works)

3. **src.secrets_manager**
   - Content: "Already implemented - AES-256-GCM encryption module..."
   - Actual implementation location unknown

4. **src.lifecycle**
   - Content: "Already implemented - see file at workspace/projects/discord-ai-bot-czech/bot/lifecycle.py"
   - Points to: `bot/lifecycle.py` ✅ (exists and works)

5. **src.graceful_degradation**
   - Content: Placeholder text
   - Points to: `bot/graceful_degradation.py` ✅ (exists and works)

6. **src.context_manager**
   - Content: Placeholder text
   - Points to: `bot/context_manager.py` ✅ (exists and works)

7. **src.credential_vault**
   - Content: Placeholder text

8. **src.credential_loader**
   - Content: Placeholder text

**Fix Required:** Either:
- Delete placeholder files and update imports to use `bot/` versions
- Implement actual functionality in `src/` versions
- Create proper stub files that re-export from `bot/`

---

### Category 3: Missing Dependencies (6 modules)

**Issue:** Required Python packages not installed

**src.auth package (6 modules):**
- `src.auth`
- `src.auth.security`
- `src.auth.database`
- `src.auth.middleware`
- `src.auth.routes`
- `src.auth.models`

**Error:** `ImportError: email-validator is not installed, run 'pip install pydantic[email]'`

**Fix Required:**
```bash
pip install pydantic[email]
```

---

### Category 4: Missing Package - jose (4 modules)

**Issue:** Python-jose package not installed

**src.api package (4 modules):**
- `src.api`
- `src.api.bot`
- `src.api.config`
- `src.api.auth`

**Error:** `ModuleNotFoundError: No module named 'jose'`

**Fix Required:**
```bash
pip install python-jose[cryptography]
```

---

## Import Structure Analysis

### Current Structure

```
discord-ai-bot-czech/
├── bot/                    # New modular structure ✅
│   ├── __init__.py        # Working
│   ├── cogs/
│   │   ├── ai_chat.py     # ❌ (depends on src.llm)
│   │   └── admin.py       # ✅
│   ├── utils/             # ✅ All working
│   ├── config_loader.py   # ✅
│   ├── context_manager.py # ✅
│   ├── errors.py          # ✅
│   ├── graceful_degradation.py # ✅
│   ├── health.py          # ✅
│   ├── interest_filter.py # ✅
│   └── lifecycle.py       # ✅
│
└── src/                    # Legacy structure with issues
    ├── llm/               # ❌ All fail (Python 3.10+ syntax)
    ├── auth/              # ❌ All fail (missing dependencies)
    ├── api/               # ❌ All fail (missing jose)
    └── [8 placeholder files] # ❌ Not valid Python
```

### Import Dependencies

**bot.cogs.ai_chat** → **src.llm** modules
- This creates a dependency chain that fails due to Python 3.10+ syntax in src.llm

---

## Recommendations

### Priority 1: Fix Python Version Compatibility

**Option A: Upgrade Python** (Recommended if possible)
```bash
# Upgrade to Python 3.10 or higher
# Update shebang lines and environment
```

**Option B: Fix Type Hints** (If Python 3.9 required)
- Replace all `X | None` with `Optional[X]`
- Replace all `dict[K, V]` with `Dict[K, V]`
- Add: `from typing import Optional, Dict, List, Union`

**Affected files:**
- `src/llm/base.py`
- `src/llm/circuit_breaker.py`
- `src/llm/providers.py`
- `src/llm/client.py`
- `src/llm/factory.py`
- And all other llm/ modules

### Priority 2: Clean Up Placeholder Files

**Decision needed:** Keep src/ or fully migrate to bot/?

**Option A: Remove placeholders, use bot/ implementations**
```bash
rm src/config.py src/errors.py src/lifecycle.py src/graceful_degradation.py \
   src/context_manager.py src/secrets_manager.py src/credential_vault.py \
   src/credential_loader.py
```
Update all imports to use `bot.*` instead of `src.*`

**Option B: Implement proper stub re-exports**
```python
# src/errors.py
"""Re-export from bot.errors for backwards compatibility."""
from bot.errors import *  # noqa
```

### Priority 3: Install Missing Dependencies

```bash
pip install pydantic[email] python-jose[cryptography]
```

Update `requirements.txt`:
```
pydantic[email]>=2.0.0
python-jose[cryptography]>=3.3.0
```

### Priority 4: Update Module Structure

**Recommended structure:**
```
discord-ai-bot-czech/
├── bot/                    # Core bot functionality
│   ├── cogs/              # Discord command handlers
│   ├── utils/             # Bot-specific utilities
│   └── ...
│
├── src/
│   ├── llm/               # LLM client library (standalone)
│   ├── auth/              # Authentication (for API)
│   └── api/               # FastAPI endpoints
│
└── tests/                 # Test suite
```

This separates:
- **bot/**: Discord bot-specific code
- **src/llm/**: Reusable LLM client (can be standalone library)
- **src/auth/ & src/api/**: Web API components

---

## Testing Command Reference

### Run all import tests:
```bash
python3 test_imports.py
```

### Test specific module:
```bash
python3 -c "import src.llm.base; print('OK')"
```

### Test with detailed error:
```bash
python3 -c "
import traceback
try:
    import src.llm.base
    print('✓ Import successful')
except Exception as e:
    traceback.print_exc()
"
```

### Test from bot context:
```bash
python3 -c "from bot.cogs.ai_chat import AIChatCog; print('OK')"
```

---

## Next Steps

1. **Decide on Python version strategy**
   - Upgrade to 3.10+ OR fix type hints for 3.9 compatibility

2. **Clean up placeholder files**
   - Remove or implement proper re-exports

3. **Install missing dependencies**
   - Add to requirements.txt
   - Document in setup instructions

4. **Re-run import tests**
   - Verify all modules can be imported
   - Update test suite

5. **Document import structure**
   - Create import guidelines
   - Add to developer documentation

---

## Files Generated

- `test_imports.py` - Comprehensive import testing script
- `IMPORT_STRUCTURE_TEST_REPORT.md` - This report

## Test Script Usage

```bash
# Run all tests
python3 test_imports.py

# Check exit code
echo $?  # 0 = all passed, 1 = some failed
```

The test script:
- Tests 50 modules systematically
- Shows pass/fail status for each
- Provides detailed error messages
- Returns appropriate exit codes for CI/CD
