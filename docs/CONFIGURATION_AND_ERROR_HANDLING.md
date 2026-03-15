# Configuration Management and Error Handling

This document describes the advanced configuration management, error handling, graceful degradation, and lifecycle management features implemented in the Discord AI Bot.

## Table of Contents

1. [Configuration Management](#configuration-management)
2. [Error Handling](#error-handling)
3. [Graceful Degradation](#graceful-degradation)
4. [Lifecycle Management](#lifecycle-management)
5. [Health Checks](#health-checks)
6. [Best Practices](#best-practices)

---

## Configuration Management

### Environment-Based Configuration

The bot supports multiple environments with automatic configuration loading:

- **development**: Local development with debug logging
- **staging**: Pre-production testing environment
- **production**: Production deployment with strict validation
- **testing**: Automated testing environment

#### Setting Environment

```bash
# In .env file
ENVIRONMENT=production
```

### Configuration Loading

The bot uses a multi-layer configuration system:

1. **Environment Variables**: Highest priority
2. **`.env` Files**: Environment-specific files (`.env`, `.env.production`, etc.)
3. **YAML Config Files**: Optional `config.{environment}.yaml` files
4. **Default Values**: Fallback defaults

#### Example Configuration Files

**`.env`:**
```bash
ENVIRONMENT=production
DISCORD_BOT_TOKEN=your_token_here
ANTHROPIC_API_KEY=your_api_key
LOG_LEVEL=INFO
ENABLE_GRACEFUL_DEGRADATION=true
```

**`config.production.yaml`:**
```yaml
max_retry_attempts: 5
retry_base_delay: 2.0
enable_health_checks: true
enable_metrics: true
```

### Configuration Validation

All configuration is validated at startup:

```python
from bot.config_loader import load_config, ConfigValidationError

try:
    config = load_config()
except ConfigValidationError as e:
    print(f"Configuration error: {e}")
    for error in e.errors:
        print(f"  - {error}")
```

### Configuration Features

#### Retry Configuration

Control automatic retry behavior for failed operations:

```bash
# Maximum retry attempts (1-10)
MAX_RETRY_ATTEMPTS=3

# Base delay between retries in seconds
RETRY_BASE_DELAY=1.0

# Maximum delay (exponential backoff cap)
RETRY_MAX_DELAY=30.0

# Exponential backoff multiplier
RETRY_EXPONENTIAL_BASE=2.0
```

#### Timeout Configuration

Set timeouts for various operations:

```bash
# HTTP requests (1.0-300.0 seconds)
HTTP_TIMEOUT=30.0

# LLM API calls (5.0-300.0 seconds)
LLM_TIMEOUT=60.0

# Discord API (5.0-120.0 seconds)
DISCORD_TIMEOUT=30.0
```

#### Reconnection Configuration

Configure automatic reconnection behavior:

```bash
# Enable/disable auto-reconnect
ENABLE_AUTO_RECONNECT=true

# Maximum reconnection attempts
MAX_RECONNECT_ATTEMPTS=5

# Base delay between reconnection attempts
RECONNECT_BASE_DELAY=5.0
```

#### Feature Flags

Enable/disable specific features:

```bash
# Message context caching
ENABLE_MESSAGE_CACHING=true

# Graceful degradation
ENABLE_GRACEFUL_DEGRADATION=true

# Health check endpoints
ENABLE_HEALTH_CHECKS=true

# Metrics collection
ENABLE_METRICS=false
```

#### Performance Tuning

Optimize bot performance:

```bash
# Message queue size (10-1000)
MESSAGE_QUEUE_SIZE=100

# Worker threads (1-32)
WORKER_THREADS=4

# Cache TTL in seconds (60-86400)
CACHE_TTL=3600
```

### Production Configuration Validation

In production environment, additional validations are enforced:

- ✅ `SECRET_KEY` must be changed from default
- ✅ `ADMIN_PASSWORD` must be changed from default
- ⚠️ `DEBUG` log level triggers warning

---

## Error Handling

### Error Hierarchy

The bot implements a comprehensive error hierarchy:

```
BotError (base)
├── ConfigurationError
│   └── MissingConfigurationError
├── DiscordError
│   ├── DiscordConnectionError
│   ├── DiscordAuthenticationError
│   └── DiscordRateLimitError
├── LLMError
│   ├── LLMProviderUnavailableError
│   ├── LLMAllProvidersUnavailableError
│   └── LLMTimeoutError
├── NetworkError
│   └── ConnectionTimeoutError
├── DatabaseError
│   └── DatabaseConnectionError
└── ValidationError
```

### Error Severity Levels

Errors are classified by severity:

- **LOW**: Minor issues, operation continues
- **MEDIUM**: Significant issues, degraded functionality
- **HIGH**: Critical issues, major feature unavailable
- **CRITICAL**: Fatal issues, bot cannot operate

### Error Categories

Errors are categorized for better tracking:

- `configuration`: Configuration-related errors
- `authentication`: Authentication failures
- `api`: External API errors
- `network`: Network connectivity issues
- `database`: Database errors
- `discord`: Discord-specific errors
- `llm`: LLM provider errors
- `validation`: Data validation errors
- `internal`: Internal bot errors
- `rate_limit`: Rate limiting errors
- `timeout`: Timeout errors

### Using Error Handler

```python
from bot.errors import error_handler, BotError

try:
    # Some operation
    result = await risky_operation()
except Exception as e:
    # Convert to BotError and handle
    bot_error = error_handler.handle_error(e, {
        "context": "additional info",
        "user_id": user.id
    })

    # Send user-friendly message
    await ctx.send(bot_error.user_message)
```

### Custom Error Creation

```python
from bot.errors import LLMError, ErrorSeverity, ErrorCategory

raise LLMError(
    message="Claude API returned 500",
    provider="anthropic",
    severity=ErrorSeverity.HIGH,
    category=ErrorCategory.API,
    user_message="AI služba je dočasně nedostupná.",
    details={"status_code": 500}
)
```

### Error Logging

All errors are automatically logged with appropriate levels:

- **LOW** → WARNING
- **MEDIUM** → ERROR
- **HIGH** → ERROR
- **CRITICAL** → CRITICAL

### Retry Logic

The error handler includes intelligent retry logic:

```python
# Check if operation should be retried
should_retry = error_handler.should_retry(
    error=bot_error,
    attempt=current_attempt,
    max_attempts=config.max_retry_attempts
)

# Errors NOT retried:
# - CRITICAL severity
# - AUTHENTICATION category
# - VALIDATION category
```

### Error Statistics

Track error occurrences:

```python
# Get error statistics
stats = error_handler.get_error_stats()
# Returns: {"llm:LLMTimeoutError": 5, "discord:DiscordConnectionError": 2}
```

---

## Graceful Degradation

### Service Health Tracking

The bot tracks service health to make intelligent degradation decisions:

```python
from bot.graceful_degradation import graceful_degradation

# Record service failure
graceful_degradation.health_tracker.record_failure("anthropic")

# Record service success
graceful_degradation.health_tracker.record_success("anthropic")

# Check service health
is_healthy = graceful_degradation.health_tracker.is_healthy("anthropic")
```

### Service Status Levels

- **OPERATIONAL**: Service working normally
- **DEGRADED**: Service experiencing issues
- **PARTIAL_OUTAGE**: Service partially unavailable
- **MAJOR_OUTAGE**: Service completely unavailable

### Fallback Strategies

#### CACHE Strategy

Use cached responses when service fails:

```python
result = await graceful_degradation.with_fallback(
    service_name="anthropic",
    operation=generate_response,
    fallback_strategy=FallbackStrategy.CACHE,
    cache_key="user_123_question_abc",
    message="Hello"
)
```

#### SKIP Strategy

Skip operation gracefully:

```python
result = await graceful_degradation.with_fallback(
    service_name="analytics",
    operation=track_event,
    fallback_strategy=FallbackStrategy.SKIP,
    event_data=data
)
# Returns None if operation fails
```

#### SIMPLIFIED Strategy

Use simplified functionality:

```python
result = await graceful_degradation.with_fallback(
    service_name="image_generation",
    operation=generate_image,
    fallback_strategy=FallbackStrategy.SIMPLIFIED,
    fallback_value="[Image temporarily unavailable]",
    prompt="sunset"
)
```

### Response Caching

Automatic caching of successful responses:

```python
# Cache is automatically populated on successful operations
# Manual cache access:
cached_value = graceful_degradation.response_cache.get("key")
graceful_degradation.response_cache.set("key", value)
graceful_degradation.response_cache.clear()
```

### Fallback Messages

Pre-configured user-friendly messages:

```python
# Get fallback message for error type
message = graceful_degradation.get_fallback_message("llm_unavailable")
# Returns: "Omlouváme se, AI služby jsou momentálně nedostupné."
```

### Health Report

Get comprehensive health report:

```python
report = graceful_degradation.get_health_report()
# Returns:
# {
#     "service_statuses": {"anthropic": "operational", "google": "degraded"},
#     "cache_stats": {"size": 42, "max_size": 100, "ttl": 3600},
#     "degraded_services": ["google"]
# }
```

---

## Lifecycle Management

### Bot States

The bot progresses through these states:

- **INITIALIZING**: Bot is initializing
- **STARTING**: Bot is starting up
- **RUNNING**: Bot is running normally
- **RECONNECTING**: Bot is reconnecting to Discord
- **SHUTTING_DOWN**: Bot is shutting down
- **STOPPED**: Bot has stopped
- **ERROR**: Bot encountered a fatal error

### Lifecycle Events

- **STARTUP**: Bot is starting (before connection)
- **READY**: Bot is ready (after connection)
- **SHUTDOWN**: Bot is shutting down
- **RECONNECT**: Bot is reconnecting
- **DISCONNECT**: Bot disconnected

### Lifecycle Hooks

Register hooks for lifecycle events:

```python
async def my_startup_hook():
    """Called during startup."""
    print("Bot is starting...")

async def my_shutdown_hook():
    """Called during shutdown."""
    print("Bot is shutting down...")

# Register hooks
bot.lifecycle.register_startup_hook(my_startup_hook)
bot.lifecycle.register_shutdown_hook(my_shutdown_hook)
bot.lifecycle.register_ready_hook(my_ready_hook)
```

### Automatic Reconnection

The bot automatically reconnects on disconnect:

1. **Detect Disconnect**: Disconnect event triggers reconnection
2. **Exponential Backoff**: Delay increases with each attempt
3. **Max Attempts**: Give up after configured max attempts
4. **Success**: Reset counters on successful reconnection

```python
# Reconnection attempt calculation:
delay = min(
    base_delay * (exponential_base ** (attempt - 1)),
    max_delay
)

# Example with defaults (base=5s, exponential=2, max=30s):
# Attempt 1: 5s
# Attempt 2: 10s
# Attempt 3: 20s
# Attempt 4: 30s (capped)
# Attempt 5: 30s (capped)
```

### Graceful Shutdown

Proper cleanup on shutdown:

```python
# Shutdown is triggered by:
# - Keyboard interrupt (Ctrl+C)
# - SIGTERM signal
# - SIGINT signal
# - Fatal error

# Shutdown sequence:
# 1. Set shutdown flag
# 2. Run shutdown hooks
# 3. Close bot connection
# 4. Log completion
```

### Lifecycle Status

Get current lifecycle status:

```python
status = bot.lifecycle.get_status()
# Returns:
# {
#     "state": "running",
#     "uptime_seconds": 3600.5,
#     "reconnect_attempts": 0,
#     "shutdown_requested": false,
#     "startup_time": "2026-03-14T10:00:00"
# }
```

### Signal Handling

The bot handles system signals gracefully:

- **SIGINT** (Ctrl+C): Graceful shutdown
- **SIGTERM**: Graceful shutdown

Both Unix and Windows platforms are supported.

---

## Health Checks

### Running Health Checks

```python
from bot.health import HealthCheck

health_check = HealthCheck(bot, config)

# Run all checks
checks = await health_check.run_all_checks()

# Individual checks
discord_status = await health_check.check_discord_connection()
llm_status = await health_check.check_llm_providers()
system_status = await health_check.check_system_resources()
db_status = await health_check.check_database()
```

### Readiness Probe

Check if bot is ready to handle requests:

```python
is_ready, details = await health_check.get_readiness_probe()

# Bot is ready if:
# - Discord connection is healthy
# - At least one LLM provider is available
```

### Liveness Probe

Check if bot is alive (not crashed/deadlocked):

```python
is_alive, details = await health_check.get_liveness_probe()

# Bot is alive if:
# - Can execute the probe function
# - Lifecycle state is not 'error' or 'stopped'
```

### Metrics

Get current bot metrics:

```python
metrics = health_check.get_metrics()

# Returns comprehensive metrics:
# {
#     "timestamp": "2026-03-14T10:30:00",
#     "bot": {
#         "user": "MyBot#1234",
#         "guilds": 5,
#         "latency_ms": 45.2,
#         "is_ready": true
#     },
#     "system": {
#         "platform": "Linux",
#         "python_version": "3.11.0",
#         "cpu_percent": 25.5,
#         "memory_percent": 42.1
#     },
#     "lifecycle": {...},
#     "errors": {...},
#     "degradation": {...}
# }
```

### Discord Commands

Admin users can check health via Discord:

```
!health   - Show health status of all components
!metrics  - Show bot metrics and performance
```

---

## Best Practices

### Configuration

1. ✅ **Always use environment variables for secrets**
   ```bash
   DISCORD_BOT_TOKEN=your_token  # Good
   # Not hardcoded in code           # Bad
   ```

2. ✅ **Use different configs for different environments**
   ```bash
   # development.env
   LOG_LEVEL=DEBUG
   ENABLE_METRICS=false

   # production.env
   LOG_LEVEL=INFO
   ENABLE_METRICS=true
   ```

3. ✅ **Validate configuration at startup**
   - Let the bot fail fast if config is invalid
   - Provide clear error messages

4. ✅ **Document all configuration options**
   - Keep `.env.example` up to date
   - Include descriptions and valid ranges

### Error Handling

1. ✅ **Use specific error types**
   ```python
   # Good
   raise LLMProviderUnavailableError("anthropic")

   # Avoid
   raise Exception("LLM error")
   ```

2. ✅ **Include context in errors**
   ```python
   error_handler.handle_error(e, {
       "user_id": user.id,
       "channel_id": channel.id,
       "command": command_name
   })
   ```

3. ✅ **Provide user-friendly messages**
   ```python
   # Technical message for logs
   message="API returned 429 Too Many Requests"
   # User-friendly message
   user_message="Přílišná zátěž. Zkuste to za chvíli."
   ```

4. ✅ **Log errors appropriately**
   - Use correct severity levels
   - Include stack traces for debugging
   - Don't log sensitive data

### Graceful Degradation

1. ✅ **Always provide fallbacks for critical features**
   ```python
   # Critical: Always have a fallback
   response = await get_ai_response_with_fallback()

   # Non-critical: Can skip
   await track_analytics()  # OK if fails
   ```

2. ✅ **Cache successful responses**
   - Reduces API calls
   - Provides fallback data
   - Improves response time

3. ✅ **Monitor service health**
   - Track failure patterns
   - Adjust behavior based on health
   - Alert on prolonged outages

4. ✅ **Test degradation scenarios**
   - Simulate API failures
   - Verify fallbacks work
   - Ensure user experience remains acceptable

### Lifecycle Management

1. ✅ **Use lifecycle hooks for initialization**
   ```python
   # Good: Use startup hook
   bot.lifecycle.register_startup_hook(initialize_database)

   # Avoid: Initialize in __init__
   def __init__():
       initialize_database()  # Blocks initialization
   ```

2. ✅ **Clean up resources in shutdown hooks**
   ```python
   async def cleanup():
       await close_database()
       await close_http_client()

   bot.lifecycle.register_shutdown_hook(cleanup)
   ```

3. ✅ **Enable auto-reconnect in production**
   ```bash
   ENABLE_AUTO_RECONNECT=true
   MAX_RECONNECT_ATTEMPTS=5
   ```

4. ✅ **Monitor lifecycle state**
   - Log state transitions
   - Alert on error states
   - Track uptime metrics

### Health Checks

1. ✅ **Implement health checks for all critical services**
   - Discord connection
   - LLM providers
   - Database
   - System resources

2. ✅ **Use readiness probes for load balancers**
   - Don't route traffic until ready
   - Remove from rotation on unhealthy

3. ✅ **Use liveness probes for restart logic**
   - Detect deadlocks
   - Trigger restarts on failure
   - Prevent zombie processes

4. ✅ **Monitor metrics regularly**
   - Set up alerting
   - Track trends over time
   - Identify performance issues early

---

## Troubleshooting

### Bot won't start

1. Check configuration validation errors in logs
2. Verify all required environment variables are set
3. Check Discord token is valid
4. Ensure at least one AI API key is configured

### Frequent reconnections

1. Check network stability
2. Review Discord API status
3. Increase `MAX_RECONNECT_ATTEMPTS`
4. Check for rate limiting

### High error rates

1. Check error statistics: `error_handler.get_error_stats()`
2. Review degradation report: `graceful_degradation.get_health_report()`
3. Run health checks: `!health` command
4. Check LLM provider availability

### Performance issues

1. Check system metrics: `!metrics` command
2. Review cache statistics
3. Adjust performance settings (`WORKER_THREADS`, `MESSAGE_QUEUE_SIZE`)
4. Monitor CPU and memory usage

---

## Example: Complete Setup

```python
# main.py
import asyncio
from bot.config_loader import load_config
from bot.lifecycle import ManagedBot
from bot.errors import error_handler
from bot.graceful_degradation import graceful_degradation

async def main():
    # Load configuration
    config = load_config()

    # Create bot with lifecycle management
    bot = ManagedBot(
        config=config,
        error_handler=error_handler,
        degradation_manager=graceful_degradation,
        command_prefix="!",
        intents=intents
    )

    # Register hooks
    bot.lifecycle.register_startup_hook(initialize_services)
    bot.lifecycle.register_shutdown_hook(cleanup_services)

    # Start bot
    await bot.start_with_lifecycle(config.discord_bot_token)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Additional Resources

- [Error Handling Module](../bot/errors.py)
- [Configuration Loader](../bot/config_loader.py)
- [Graceful Degradation](../bot/graceful_degradation.py)
- [Lifecycle Management](../bot/lifecycle.py)
- [Health Checks](../bot/health.py)
