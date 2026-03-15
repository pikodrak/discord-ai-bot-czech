#!/usr/bin/env python3
"""
Import Structure Test Script

This script tests that all modules can be imported correctly from both
src/ and bot/ contexts to verify the import structure is working properly.
"""

import sys
import importlib
from pathlib import Path
from typing import List, Dict, Tuple

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_import(module_name: str) -> Tuple[bool, str]:
    """
    Test importing a single module.

    Args:
        module_name: Fully qualified module name (e.g., 'src.retry_strategy')

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        importlib.import_module(module_name)
        return (True, "")
    except Exception as e:
        return (False, f"{type(e).__name__}: {str(e)}")


def main() -> Dict[str, List[Dict[str, str]]]:
    """
    Test all module imports and return results.

    Returns:
        Dictionary with 'passed' and 'failed' lists of test results
    """
    # Modules to test from src/
    src_modules = [
        "src.retry_strategy",
        "src.logger",
        "src.client_enhanced",
        "src.secrets_manager",
        "src.providers",
        "src.exceptions",
        "src.config",
        "src.errors",
        "src.lifecycle",
        "src.graceful_degradation",
        "src.context_manager",
        "src.health",
        "src.interest_filter",
        "src.credential_vault",
        "src.credential_loader",
        "src.shared_config",
        # LLM subpackage
        "src.llm",
        "src.llm.retry_strategy",
        "src.llm.client_enhanced",
        "src.llm.providers",
        "src.llm.exceptions",
        "src.llm.client",
        "src.llm.language_utils",
        "src.llm.factory",
        "src.llm.base",
        "src.llm.circuit_breaker",
        # Auth subpackage
        "src.auth",
        "src.auth.security",
        "src.auth.database",
        "src.auth.middleware",
        "src.auth.routes",
        "src.auth.models",
        # API subpackage
        "src.api",
        "src.api.bot",
        "src.api.config",
        "src.api.auth",
        # Utils
        "src.utils",
    ]

    # Modules to test from bot/
    bot_modules = [
        "bot",
        "bot.config_loader",
        "bot.health",
        "bot.interest_filter",
        "bot.lifecycle",
        "bot.errors",
        "bot.graceful_degradation",
        "bot.context_manager",
        "bot.cogs.ai_chat",
        "bot.cogs.admin",
        "bot.utils",
        "bot.utils.logger",
        "bot.utils.message_filter",
    ]

    results = {
        "passed": [],
        "failed": []
    }

    all_modules = src_modules + bot_modules

    print("=" * 70)
    print("TESTING MODULE IMPORTS")
    print("=" * 70)
    print()

    for module_name in all_modules:
        success, error = test_import(module_name)

        result_entry = {
            "module": module_name,
            "error": error
        }

        if success:
            results["passed"].append(result_entry)
            print(f"✓ {module_name}")
        else:
            results["failed"].append(result_entry)
            print(f"✗ {module_name}")
            print(f"  Error: {error}")
            print()

    # Print summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total modules tested: {len(all_modules)}")
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    print()

    if results['failed']:
        print("FAILED MODULES:")
        for result in results['failed']:
            print(f"  - {result['module']}")
            print(f"    {result['error']}")
            print()

    return results


if __name__ == "__main__":
    results = main()

    # Exit with error code if any imports failed
    sys.exit(1 if results['failed'] else 0)
