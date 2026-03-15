# Error Handling Guide

This guide explains the comprehensive error handling system in the Discord AI Bot.

## Overview

The bot includes a multi-layered error handling system:

1. **Custom Error Classes** - Structured error hierarchy
2. **Error Handler** - Centralized error processing
3. **Graceful Degradation** - Fallback mechanisms
4. **User-Friendly Messages** - Translated Czech error messages

## Error Hierarchy

### Base Error: `BotError`

All bot errors inherit from `BotError`:

```python
from bot.errors import BotError, ErrorSeverity, ErrorCategory

error = BotError(
    message="Technical error description",
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.INTERNAL,
    user_message="Chyba při zpracování požadavku.",
    details={"context": "additional info"},
    original_error=original_exception
)
```

### Error Severity Levels

- `LOW` - Minor issues, can continue operation
- `MEDIUM` - Significant issues, degraded functionality
- `HIGH` - Critical issues, major feature unavailable
- `CRITICAL` - Fatal issues, bot cannot operate

### Error Categories

- `CONFIGURATION` - Configuration errors
- `AUTHENTICATION` - Auth failures
- `API` - API errors
- `NETWORK` - Network issues
- `DATABASE` - Database errors
- `DISCORD` - Discord-specific errors
- `LLM` - LLM provider errors
- `VALIDATION` - Data validation errors
- `INTERNAL` - Internal bot errors
- `RATE_LIMIT` - Rate limiting
- `TIMEOUT` - Timeout errors

## Error Classes

### Configuration Errors

```python
from bot.errors import ConfigurationError, MissingConfigurationError

# Generic configuration error
raise ConfigurationError(
    "Invalid configuration value",
    details={"key": "value"}
)

# Missing configuration
raise MissingConfigurationError("DISCORD_BOT_TOKEN")
```

### Discord Errors

```python
from bot.errors import (
    DiscordConnectionError,
    DiscordAuthenticationError,
    DiscordRateLimitError
)

# Connection failure
raise DiscordConnectionError("Failed to connect to gateway")

# Authentication failure
raise DiscordAuthenticationError("Invalid bot token")

# Rate limit
raise DiscordRateLimitError(retry_after=30.0)
```

### LLM Errors

```python
from bot.errors import (
    LLMProviderUnavailableError,
    LLMAllProvidersUnavailableError,
    LLMTimeoutError
)

# Single provider unavailable
raise LLMProviderUnavailableError("anthropic")

# All providers unavailable
raise LLMAllProvidersUnavailableError({
    "anthropic": Exception("API key invalid"),
    "openai": Exception("Rate limit exceeded")
})

# Timeout
raise LLMTimeoutError("anthropic", timeout=60.0)
```

### Network Errors

```python
from bot.errors import NetworkError, ConnectionTimeoutError

# Generic network error
raise NetworkError("Connection refused")

# Timeout
raise ConnectionTimeoutError(
    url="https://api.example.com",
    timeout=30.0
)
```

## Error Handler

The `ErrorHandler` class provides centralized error processing:

```python
from bot.errors import ErrorHandler, error_handler

# Use global instance
handler = error_handler

# Handle an error
bot_error = handler.handle_error(
    exception,
    context={"operation": "generate_response"}
)

# Check if should retry
if handler.should_retry(bot_error, attempt=1, max_attempts=3):
    # Retry operation
    pass

# Get error statistics
stats = handler.get_error_stats()
print(f"Error counts: {stats}")
```

### Error Handling Features

- Automatic error conversion to `BotError`
- Error logging with appropriate severity
- Error tracking and statistics
- Retry decision logic

## Graceful Degradation

The graceful degradation system provides fallback mechanisms when services fail:

```python
from bot.graceful_degradation import graceful_degradation

# Execute with fallback
result = await graceful_degradation.with_fallback(
    service_name="llm_api",
    operation=generate_response,
    fallback_strategy=FallbackStrategy.CACHE,
    cache_key="response_key",
    fallback_value="Sorry, AI is unavailable",
    # Operation arguments
    messages=messages
)
```

### Fallback Strategies

1. **CACHE** - Use cached response
2. **SIMPLIFIED** - Use simplified functionality
3. **SKIP** - Skip operation gracefully
4. **MANUAL** - Custom fallback logic

### Service Health Tracking

The system tracks service health:

```python
# Record success
graceful_degradation.health_tracker.record_success("llm_api")

# Record failure
graceful_degradation.health_tracker.record_failure("llm_api")

# Check health
is_healthy = graceful_degradation.health_tracker.is_healthy("llm_api")

# Get status
status = graceful_degradation.health_tracker.get_status("llm_api")
# Returns: OPERATIONAL, DEGRADED, PARTIAL_OUTAGE, or MAJOR_OUTAGE
```

### Response Caching

Automatic response caching for fallback:

```python
# Cache is used automatically with CACHE strategy
cache = graceful_degradation.response_cache

# Manual cache operations
cache.set("key", value)
cached = cache.get("key")
cache.clear()

# Cache stats
stats = cache.get_stats()
```

## Error Handling in Practice

### In Commands

```python
@commands.command()
async def my_command(self, ctx: commands.Context):
    try:
        # Command logic
        result = await some_operation()
        await ctx.send(result)

    except BotError as e:
        # Handle bot errors
        e.log()
        await ctx.send(e.user_message)

    except Exception as e:
        # Handle unexpected errors
        bot_error = error_handler.handle_error(
            e,
            context={"command": "my_command"}
        )
        await ctx.send(bot_error.user_message)
```

### In Cogs

```python
class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.error_handler = bot.error_handler
        self.degradation = bot.degradation

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            # Use graceful degradation
            response = await self.degradation.with_fallback(
                service_name="ai_response",
                operation=self.generate_response,
                fallback_strategy=FallbackStrategy.CACHE,
                cache_key=f"response_{message.id}",
                message=message
            )

            if response:
                await message.reply(response)

        except Exception as e:
            self.error_handler.handle_error(e)
```

### Retry Logic

```python
async def operation_with_retry():
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            return await risky_operation()

        except Exception as e:
            bot_error = error_handler.handle_error(e)

            if not error_handler.should_retry(bot_error, attempt, max_attempts):
                raise

            # Exponential backoff
            delay = 2 ** attempt
            await asyncio.sleep(delay)

    raise Exception("Max retries exceeded")
```

## User-Friendly Error Messages

All errors include Czech user-friendly messages:

```python
error_messages = {
    "llm_unavailable": [
        "Omlouváme se, AI služby jsou momentálně nedostupné.",
        "Bohužel momentálně nemohu generovat odpovědi.",
    ],
    "api_error": [
        "Došlo k problému s externím API.",
    ],
    "timeout": [
        "Operace trvala příliš dlouho. Zkuste to prosím znovu.",
    ],
}

# Get fallback message
message = graceful_degradation.get_fallback_message("llm_unavailable")
```

## Error Logging

Errors are logged with appropriate severity:

- `LOW` → WARNING level
- `MEDIUM` → ERROR level
- `HIGH` → ERROR level
- `CRITICAL` → CRITICAL level

```python
# Error automatically logs when created
error = BotError(
    message="Something went wrong",
    severity=ErrorSeverity.HIGH
)
error.log()  # Logs at ERROR level
```

## Monitoring and Debugging

### Error Statistics

```python
# Get error counts
stats = error_handler.get_error_stats()

# Example output:
# {
#   "llm:LLMTimeoutError": 5,
#   "discord:DiscordRateLimitError": 2,
#   "network:ConnectionTimeoutError": 3
# }
```

### Health Report

```python
# Get comprehensive health report
report = graceful_degradation.get_health_report()

# Example output:
# {
#   "service_statuses": {
#     "llm_api": "operational",
#     "discord": "operational"
#   },
#   "cache_stats": {"size": 45, "max_size": 100},
#   "degraded_services": []
# }
```

## Best Practices

1. **Use Specific Error Classes** - Don't use generic `Exception`
2. **Include Context** - Add relevant details to errors
3. **Log Appropriately** - Use correct severity levels
4. **User-Friendly Messages** - Always provide Czech messages
5. **Enable Graceful Degradation** - Use fallback mechanisms
6. **Monitor Error Rates** - Track error statistics
7. **Cache Strategically** - Cache expensive operations
8. **Retry Intelligently** - Don't retry auth/validation errors

## Testing Error Handling

```python
import pytest
from bot.errors import BotError, ErrorSeverity

def test_error_handling():
    error = BotError(
        message="Test error",
        severity=ErrorSeverity.LOW
    )

    assert error.severity == ErrorSeverity.LOW
    assert error.user_message is not None

def test_error_handler():
    handler = ErrorHandler()

    # Test error conversion
    generic_error = Exception("Something failed")
    bot_error = handler.handle_error(generic_error)

    assert isinstance(bot_error, BotError)
    assert bot_error.message is not None
```

## Troubleshooting

### Error Not Being Caught

Check:
1. Error hierarchy - Is the exception a `BotError`?
2. Try-except placement - Is it in the right scope?
3. Error propagation - Is the error being re-raised?

### Fallback Not Working

Check:
1. Fallback strategy - Is the correct strategy selected?
2. Cache key - Is a valid cache key provided?
3. Service name - Is the service name consistent?

### Too Many Retries

Adjust:
1. `MAX_RETRY_ATTEMPTS` - Lower the maximum attempts
2. `RETRY_BASE_DELAY` - Increase the delay
3. Retry logic - Check `should_retry` conditions
