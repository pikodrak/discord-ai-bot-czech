#!/usr/bin/env python3
"""
FastAPI Setup Verification Script

This script tests that the FastAPI application structure is properly set up
and all imports work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        from src.config import Settings, get_settings, reload_settings
        print("✓ Config module imports successfully")
    except ImportError as e:
        print(f"✗ Config module import failed: {e}")
        return False

    try:
        from src.api import auth, bot, config
        print("✓ API routers import successfully")
    except ImportError as e:
        print(f"✗ API routers import failed: {e}")
        return False

    try:
        import app
        print("✓ Main app module imports successfully")
    except ImportError as e:
        print(f"✗ Main app import failed: {e}")
        return False

    return True


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")

    try:
        from src.config import get_settings
        settings = get_settings()
        print(f"✓ Settings loaded: {settings}")
        print(f"  - API Host: {settings.api_host}")
        print(f"  - API Port: {settings.api_port}")
        print(f"  - Log Level: {settings.log_level}")
        print(f"  - Bot Language: {settings.bot_language}")
        return True
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False


def test_app_creation():
    """Test FastAPI app creation."""
    print("\nTesting FastAPI app creation...")

    try:
        import app
        if hasattr(app, 'app'):
            print("✓ FastAPI app instance created")
            print(f"  - Title: {app.app.title}")
            print(f"  - Version: {app.app.version}")
            print(f"  - Routes: {len(app.app.routes)} registered")
            return True
        else:
            print("✗ FastAPI app instance not found")
            return False
    except Exception as e:
        print(f"✗ FastAPI app creation failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("FastAPI Setup Verification")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("App Creation", test_app_creation()))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All tests passed! FastAPI setup is complete.")
        print("\nNext steps:")
        print("  1. Configure .env file with your settings")
        print("  2. Run: python run_api.py")
        print("  3. Visit: http://localhost:8000/docs")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
