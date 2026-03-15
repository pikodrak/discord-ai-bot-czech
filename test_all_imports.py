"""
Comprehensive import verification test.

Tests all critical imports across the refactored codebase to identify
any missing modules, broken import paths, or undefined classes/functions.
"""

import sys
from pathlib import Path
import traceback

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_import(module_path: str, items: list[str] = None) -> bool:
    """
    Test importing a module and optionally specific items from it.

    Args:
        module_path: The module to import (e.g., "src.config")
        items: Optional list of items to import from the module

    Returns:
        True if import succeeded, False otherwise
    """
    try:
        if items:
            exec(f"from {module_path} import {', '.join(items)}")
            print(f"✓ {module_path}: {', '.join(items)}")
        else:
            exec(f"import {module_path}")
            print(f"✓ {module_path}")
        return True
    except Exception as e:
        print(f"✗ {module_path}: {type(e).__name__}: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        return False

def main():
    """Run all import tests."""
    print("=" * 70)
    print("DISCORD AI BOT - IMPORT VERIFICATION TEST")
    print("=" * 70)
    print()

    results = []

    # Test main entry point imports (main.py)
    print("Testing main.py imports...")
    print("-" * 70)
    results.append(test_import("bot.config_loader", ["load_config", "ConfigValidationError"]))
    results.append(test_import("bot.errors", ["error_handler", "DiscordConnectionError",
                                               "DiscordAuthenticationError", "ConfigurationError"]))
    results.append(test_import("bot.graceful_degradation", ["GracefulDegradation"]))
    results.append(test_import("bot.lifecycle", ["ManagedBot", "LifecycleManager"]))
    results.append(test_import("bot.utils.logger", ["setup_logger"]))
    results.append(test_import("src.shared_config", ["get_shared_config_loader",
                                                      "load_bot_config_from_shared"]))
    results.append(test_import("src.ipc", ["get_ipc_channel", "IPCCommand", "IPCSignal"]))
    print()

    # Test app.py imports
    print("Testing app.py imports...")
    print("-" * 70)
    results.append(test_import("src.config", ["get_settings", "Settings"]))
    results.append(test_import("src.api.auth"))
    results.append(test_import("src.api.bot"))
    results.append(test_import("src.api.config"))
    print()

    # Test bot.py imports
    print("Testing bot.py imports...")
    print("-" * 70)
    results.append(test_import("src.config", ["Settings", "get_settings"]))
    print()

    # Test LLM imports (used in main.py)
    print("Testing LLM module imports...")
    print("-" * 70)
    results.append(test_import("src.llm.factory", ["create_llm_client"]))
    results.append(test_import("src.llm.client"))
    results.append(test_import("src.llm.base"))
    results.append(test_import("src.llm.providers"))
    print()

    # Test auth imports
    print("Testing auth module imports...")
    print("-" * 70)
    results.append(test_import("src.auth.security"))
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    failed = total - passed

    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    if failed > 0:
        print(f"❌ {failed} import(s) failed - application will NOT start correctly")
        return 1
    else:
        print("✅ All imports successful - application should start correctly")
        return 0

if __name__ == "__main__":
    sys.exit(main())
