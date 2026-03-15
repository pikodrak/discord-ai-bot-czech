"""
Unified Configuration Management and Error Handling Example

This example demonstrates how to use the unified configuration management system:
- SharedConfigLoader for thread-safe hot-reload configuration
- AdvancedBotConfig for bot-specific configuration with validation
- API Settings for web interface configuration
- Error handling with graceful degradation
"""

import asyncio
import logging
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config_loader import load_config, ConfigValidationError, Environment
from src.shared_config import get_shared_config_loader
from src.config import get_settings
from bot.errors import (
    error_handler,
    BotError,
    LLMError,
    DiscordConnectionError,
    ErrorSeverity,
    ErrorCategory,
)
from bot.graceful_degradation import (
    graceful_degradation,
    FallbackStrategy,
    ServiceStatus,
)
from bot.lifecycle import LifecycleManager, BotState


async def example_configuration_loading():
    """Example: Loading and validating configuration."""
    print("\n" + "=" * 60)
    print("Example 1: Configuration Loading")
    print("=" * 60)

    try:
        # Load configuration with environment-based settings
        config = load_config()
        
        print(f"✓ Configuration loaded successfully")
        print(f"  Environment: {config.environment.value}")
        print(f"  Log Level: {config.log_level}")
        print(f"  Available Providers: {config.get_available_providers()}")
        print(f"  Graceful Degradation: {config.enable_graceful_degradation}")
        print(f"  Auto Reconnect: {config.enable_auto_reconnect}")
        print(f"  Max Retry Attempts: {config.max_retry_attempts}")
        
        # Access configuration safely
        if config.has_ai_provider("anthropic"):
            print(f"✓ Anthropic provider configured")
        
        # Get configuration as dictionary (without secrets)
        config_dict = config.to_dict(include_secrets=False)
        print(f"  Config keys: {list(config_dict.keys())[:5]}...")
        
    except ConfigValidationError as e:
        print(f"✗ Configuration validation failed: {e}")
        if e.errors:
            for error in e.errors:
                print(f"  - {error}")


async def example_error_handling():
    """Example: Using the error handler."""
    print("\n" + "=" * 60)
    print("Example 2: Error Handling")
    print("=" * 60)

    # Example 1: Creating custom errors
    try:
        # Simulate an LLM error
        raise LLMError(
            message="Anthropic API returned 429 Too Many Requests",
            provider="anthropic",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.RATE_LIMIT,
            user_message="AI služba je přetížená. Zkuste to za chvíli.",
            details={"status_code": 429, "retry_after": 60}
        )
    except BotError as e:
        # Handle bot error
        e.log()  # Automatically logs with correct level
        print(f"✓ Error handled:")
        print(f"  Technical: {e.message}")
        print(f"  User Message: {e.user_message}")
        print(f"  Severity: {e.severity.value}")
        print(f"  Category: {e.category.value}")
        print(f"  Details: {e.details}")

    # Example 2: Converting generic exceptions
    try:
        # Simulate a generic error
        raise TimeoutError("Connection timed out after 30s")
    except Exception as e:
        bot_error = error_handler.handle_error(e, {
            "service": "discord",
            "operation": "send_message"
        })
        print(f"\n✓ Generic exception converted:")
        print(f"  Type: {type(bot_error).__name__}")
        print(f"  Message: {bot_error.user_message}")

    # Example 3: Retry logic
    print(f"\n✓ Retry logic example:")
    max_attempts = 5
    
    for attempt in range(1, max_attempts + 1):
        mock_error = LLMError(
            message="API temporarily unavailable",
            provider="test",
            severity=ErrorSeverity.MEDIUM
        )
        
        should_retry = error_handler.should_retry(
            error=mock_error,
            attempt=attempt,
            max_attempts=max_attempts
        )
        
        print(f"  Attempt {attempt}/{max_attempts}: Retry = {should_retry}")

    # Example 4: Error statistics
    stats = error_handler.get_error_stats()
    print(f"\n✓ Error statistics: {stats}")


async def example_graceful_degradation():
    """Example: Using graceful degradation."""
    print("\n" + "=" * 60)
    print("Example 3: Graceful Degradation")
    print("=" * 60)

    # Example 1: Service health tracking
    print("✓ Service health tracking:")
    
    # Simulate service failures
    for i in range(3):
        graceful_degradation.health_tracker.record_failure("anthropic")
        status = graceful_degradation.health_tracker.get_status("anthropic")
        print(f"  After {i+1} failure(s): {status.value}")
    
    # Simulate service recovery
    for i in range(2):
        graceful_degradation.health_tracker.record_success("anthropic")
        status = graceful_degradation.health_tracker.get_status("anthropic")
        print(f"  After {i+1} success(es): {status.value}")

    # Example 2: Fallback with caching
    print(f"\n✓ Fallback with caching:")
    
    async def mock_llm_call(text: str) -> str:
        """Mock LLM call that may fail."""
        import random
        if random.random() < 0.3:  # 30% failure rate
            raise Exception("API temporarily unavailable")
        return f"Response to: {text}"
    
    # Try with fallback
    result = await graceful_degradation.with_fallback(
        service_name="llm",
        operation=mock_llm_call,
        fallback_strategy=FallbackStrategy.CACHE,
        cache_key="question_1",
        text="Hello"
    )
    
    if result:
        print(f"  Result: {result}")
    else:
        print(f"  No result (would use fallback)")

    # Example 3: Fallback messages
    print(f"\n✓ Fallback messages:")
    for error_type in ["llm_unavailable", "api_error", "timeout"]:
        message = graceful_degradation.get_fallback_message(error_type)
        print(f"  {error_type}: {message}")

    # Example 4: Health report
    print(f"\n✓ Health report:")
    report = graceful_degradation.get_health_report()
    print(f"  Service statuses: {report['service_statuses']}")
    print(f"  Cache stats: {report['cache_stats']}")
    print(f"  Degraded services: {report['degraded_services']}")


async def example_lifecycle_management():
    """Example: Using lifecycle management (simulated)."""
    print("\n" + "=" * 60)
    print("Example 4: Lifecycle Management")
    print("=" * 60)

    # This is a simplified example showing the lifecycle API
    # In real usage, this is integrated with the Discord bot
    
    print("✓ Lifecycle states:")
    for state in BotState:
        print(f"  - {state.value}")
    
    print(f"\n✓ Lifecycle hooks:")
    print(f"  - startup: Called during bot initialization")
    print(f"  - ready: Called when bot connects to Discord")
    print(f"  - shutdown: Called during graceful shutdown")
    
    print(f"\n✓ Reconnection logic:")
    base_delay = 5.0
    exponential_base = 2.0
    max_delay = 30.0
    max_attempts = 5
    
    print(f"  Base delay: {base_delay}s")
    print(f"  Exponential base: {exponential_base}")
    print(f"  Max delay: {max_delay}s")
    print(f"  Attempts:")
    
    for attempt in range(1, max_attempts + 1):
        delay = min(
            base_delay * (exponential_base ** (attempt - 1)),
            max_delay
        )
        print(f"    Attempt {attempt}: {delay:.1f}s delay")


async def example_integration():
    """Example: Putting it all together."""
    print("\n" + "=" * 60)
    print("Example 5: Complete Integration")
    print("=" * 60)

    # 1. Load configuration
    try:
        config = load_config()
        print(f"✓ Configuration loaded: {config.environment.value}")
    except ConfigValidationError as e:
        print(f"✗ Configuration failed: {e}")
        return

    # 2. Setup error handling with graceful degradation
    print(f"✓ Error handler initialized")
    print(f"✓ Graceful degradation: {config.enable_graceful_degradation}")

    # 3. Simulate bot operation with error handling
    async def risky_operation():
        """Simulate an operation that might fail."""
        import random
        if random.random() < 0.3:
            raise Exception("Random failure")
        return "Success!"

    print(f"\n✓ Running operations with error handling:")
    for i in range(5):
        try:
            result = await graceful_degradation.with_fallback(
                service_name="test_service",
                operation=risky_operation,
                fallback_strategy=FallbackStrategy.CACHE,
                cache_key=f"op_{i}",
            )
            
            if result:
                print(f"  Operation {i+1}: {result}")
            else:
                print(f"  Operation {i+1}: Failed (using fallback)")
                
        except Exception as e:
            bot_error = error_handler.handle_error(e, {"operation": i})
            print(f"  Operation {i+1}: Error - {bot_error.user_message}")

    # 4. Show final statistics
    print(f"\n✓ Session summary:")
    print(f"  Errors: {error_handler.get_error_stats()}")
    print(f"  Health: {graceful_degradation.health_tracker.get_all_statuses()}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Configuration Management and Error Handling Examples")
    print("=" * 60)

    await example_configuration_loading()
    await example_error_handling()
    await example_graceful_degradation()
    await example_lifecycle_management()
    await example_integration()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Setup basic logging to see the examples
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    
    asyncio.run(main())
