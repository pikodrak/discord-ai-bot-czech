"""
Example usage of unified configuration management system.

This example demonstrates:
- Loading configuration from multiple sources (shared config, env, YAML)
- Using SharedConfigLoader for thread-safe hot-reload support
- Using AdvancedBotConfig for bot-specific configuration with validation
- API configuration management for web interface
- Best practices for configuration in different contexts
"""

import asyncio
from pathlib import Path
from typing import Optional

# Import unified configuration management
from src.shared_config import (
    SharedConfigLoader,
    get_shared_config_loader,
    load_bot_config_from_shared
)
from bot.config_loader import (
    AdvancedBotConfig,
    ConfigLoader,
    load_config,
    Environment,
    ConfigValidationError
)
from src.config import get_settings, get_config_manager, reload_settings



async def example_shared_config_loader():
    """Example: Using SharedConfigLoader for thread-safe configuration."""
    print("\n=== SharedConfigLoader Example ===\n")

    # Get or create a shared config loader for the project
    project_root = Path.cwd()
    loader = get_shared_config_loader(project_root)

    # Load configuration from all sources
    # Priority: shared_config.json > YAML > env > .env
    config = loader.load_config()
    print(f"Configuration loaded from multiple sources")
    print(f"Environment: {config.get('environment', 'development')}")
    print(f"Log Level: {config.get('log_level', 'INFO')}")
    print(f"Bot Language: {config.get('bot_language', 'cs')}")

    # Update a configuration value (persisted to shared_config.json)
    loader.set('bot_response_threshold', 0.75)
    print(f"\nUpdated bot_response_threshold to: {loader.get('bot_response_threshold')}")

    # Force reload from disk
    fresh_config = loader.load_config(force_reload=True)
    print(f"Reloaded configuration from all sources")


async def example_bot_config_loader():
    """Example: Using AdvancedBotConfig for bot configuration."""
    print("\n=== AdvancedBotConfig Example ===\n")

    try:
        # Load bot configuration with validation
        config = load_config()

        print(f"Bot configuration loaded successfully")
        print(f"Environment: {config.environment.value}")
        print(f"Language: {config.bot_language}")
        print(f"Max History: {config.bot_max_history}")
        print(f"Available Providers: {config.get_available_providers()}")
        print(f"Is Production: {config.is_production()}")
        print(f"Is Development: {config.is_development()}")

        # Access configuration safely
        channel_ids = config.get_channel_ids()
        print(f"Channel IDs: {channel_ids}")

        # Check AI provider availability
        if config.has_ai_provider("anthropic"):
            print("✓ Anthropic (Claude) provider is configured")
        if config.has_ai_provider("google"):
            print("✓ Google (Gemini) provider is configured")
        if config.has_ai_provider("openai"):
            print("✓ OpenAI provider is configured")

        # Export configuration (with/without secrets)
        safe_dict = config.to_dict(include_secrets=False)
        print(f"\nConfiguration keys: {list(safe_dict.keys())[:5]}...")

    except ConfigValidationError as e:
        print(f"Configuration validation failed: {e}")
        if e.errors:
            for error in e.errors:
                print(f"  - {error}")


async def example_api_settings():
    """Example: Using API settings from src.config."""
    print("\n=== API Settings Example ===\n")

    # Get settings (automatically loads from .env and config.{environment}.yaml)
    settings = get_settings()

    print(f"API Host: {settings.api_host}")
    print(f"API Port: {settings.api_port}")
    print(f"Discord Configured: {settings.has_discord_config()}")
    print(f"Available LLM Providers: {settings.get_available_llm_providers()}")
    print(f"Preferred AI Provider: {settings.get_preferred_ai_provider()}")

    # Get configuration manager for runtime updates
    config_manager = get_config_manager()

    # Update configuration at runtime
    config_manager.update(log_level="DEBUG", bot_language="en")
    print(f"\nUpdated log level to: {get_settings().log_level}")
    print(f"Updated bot language to: {get_settings().bot_language}")

    # Export safe configuration (masked secrets)
    safe_config = config_manager.get_safe_dict()
    print(f"Safe config contains {len(safe_config)} keys")

    # Reload configuration from disk
    reload_settings()
    print(f"Configuration reloaded from disk")




async def example_unified_configuration_best_practices():
    """Example: Best practices for using unified configuration."""
    print("\n=== Unified Configuration Best Practices ===\n")

    print("Best Practice 1: Use SharedConfigLoader for hot-reload scenarios")
    print("  - Admin API that needs to update configuration without restart")
    print("  - Shared configuration between bot and API processes")
    print("  - Thread-safe configuration access\n")

    print("Best Practice 2: Use AdvancedBotConfig for bot initialization")
    print("  - Strong validation and type checking with Pydantic")
    print("  - Environment-specific configuration (dev, staging, prod)")
    print("  - Automatic directory creation and setup\n")

    print("Best Practice 3: Use src.config Settings for API endpoints")
    print("  - FastAPI dependency injection compatible")
    print("  - Runtime configuration updates via ConfigManager")
    print("  - Built-in validation and safe export\n")

    print("Configuration Loading Priority:")
    print("  1. SharedConfigLoader: shared_config.json (highest)")
    print("  2. Environment-specific YAML (config.{environment}.yaml)")
    print("  3. Environment variables")
    print("  4. .env file (lowest)")


async def main():
    """Run all configuration examples."""
    try:
        print("\n" + "=" * 60)
        print("Unified Configuration Management Examples")
        print("=" * 60)

        # Run configuration examples
        await example_shared_config_loader()
        await example_bot_config_loader()
        await example_api_settings()
        await example_unified_configuration_best_practices()

        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nExample failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
