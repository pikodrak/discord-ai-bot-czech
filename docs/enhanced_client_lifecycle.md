# EnhancedLLMClient Lifecycle Management

## Overview

The `EnhancedLLMClient` now supports proper resource lifecycle management through async context managers. This ensures that all provider resources (HTTP connections, client sessions, etc.) are properly initialized and cleaned up.

## Key Features

- **Async Context Manager Support**: Use `async with` for automatic resource management
- **Deferred Initialization**: Providers are only initialized when entering the context
- **Guaranteed Cleanup**: Resources are properly cleaned up even if errors occur
- **Multiple Provider Support**: Manages lifecycle for all configured providers (Claude, Gemini, OpenAI)
- **Error Resilience**: Continues cleanup even if some providers fail to close

## Usage Patterns

### Recommended: Async Context Manager

This is the **recommended** way to use `EnhancedLLMClient`:

```python
from src.llm.client_enhanced import EnhancedLLMClient
from src.llm.base import LLMMessage

async with EnhancedLLMClient(
    anthropic_api_key="your-key",
    google_api_key="your-key",
    language="en",
) as client:
    # Providers are automatically initialized here
    response = await client.generate_simple_response("Hello!")
    print(response)

# Providers are automatically cleaned up here
```

### Manual Management (Not Recommended)

If you need manual control over the lifecycle:

```python
client = EnhancedLLMClient(anthropic_api_key="your-key")

# Manual initialization
await client._initialize_providers()

try:
    response = await client.generate_simple_response("Hello!")
finally:
    # Manual cleanup
    await client._cleanup_providers()
```

**Note**: Manual management is not recommended as it's error-prone. Use the context manager pattern instead.

## Implementation Details

### Initialization Process

When entering the async context (`__aenter__`):

1. **Provider Creation**: Each provider (Claude, Gemini, OpenAI) is instantiated
2. **Context Manager Entry**: Each provider's `__aenter__` method is called to initialize resources
3. **Registration**: Successfully initialized providers are registered with the client
4. **Validation**: Ensures at least one provider was initialized successfully

### Cleanup Process

When exiting the async context (`__aexit__`):

1. **Graceful Shutdown**: Each provider's `__aexit__` method is called
2. **Error Handling**: Cleanup continues even if some providers fail to close
3. **Resource Clearing**: Provider list is cleared
4. **State Reset**: Client state is reset to uninitialized

### Provider Lifecycle

Each provider implements its own async context manager:

#### ClaudeProvider

```python
async with ClaudeProvider(api_key="...") as provider:
    # AsyncAnthropic client is created and pooled
    response = await provider.generate_response(messages)

# AsyncAnthropic client is properly closed
```

#### GeminiProvider

```python
async with GeminiProvider(api_key="...") as provider:
    # Gemini API is configured
    # Model cache is initialized
    response = await provider.generate_response(messages)

# Model cache is cleared
# Configuration is reset
```

#### OpenAIProvider

```python
async with OpenAIProvider(api_key="...") as provider:
    # AsyncOpenAI client is created and pooled
    response = await provider.generate_response(messages)

# AsyncOpenAI client is properly closed
```

## Error Handling

### Initialization Errors

If no providers can be initialized, the client raises `LLMAllProvidersFailedError`:

```python
try:
    async with EnhancedLLMClient(anthropic_api_key="invalid") as client:
        pass
except LLMAllProvidersFailedError as e:
    print(f"Failed to initialize: {e.errors}")
```

### Runtime Errors

If you try to use the client without proper initialization:

```python
client = EnhancedLLMClient(anthropic_api_key="...")

# This will raise RuntimeError
await client.generate_simple_response("Hello!")
# RuntimeError: EnhancedLLMClient not initialized...
```

### Cleanup Errors

Cleanup errors are logged but don't prevent other providers from being cleaned up:

```python
async with EnhancedLLMClient(...) as client:
    # Use client
    pass
# Even if one provider fails to cleanup, others will still be cleaned up
```

## Best Practices

### 1. Always Use Context Manager

```python
# Good
async with EnhancedLLMClient(...) as client:
    await client.generate_response(messages)

# Bad
client = EnhancedLLMClient(...)
await client.generate_response(messages)  # RuntimeError!
```

### 2. Handle Initialization Failures

```python
try:
    async with EnhancedLLMClient(...) as client:
        response = await client.generate_response(messages)
except LLMAllProvidersFailedError as e:
    logger.error(f"Failed to initialize client: {e}")
    # Fallback logic
```

### 3. Multiple Clients

Each client manages its own resources independently:

```python
async with EnhancedLLMClient(
    anthropic_api_key=key1
) as client1, EnhancedLLMClient(
    google_api_key=key2
) as client2:
    # Both clients properly managed
    r1 = await client1.generate_simple_response("Q1")
    r2 = await client2.generate_simple_response("Q2")
```

### 4. Long-Running Applications

For long-running applications (like Discord bots), create the client once at startup:

```python
class MyBot:
    async def setup(self):
        # Create client during bot setup
        self.llm_client = EnhancedLLMClient(...)
        await self.llm_client._initialize_providers()

    async def cleanup(self):
        # Cleanup during bot shutdown
        await self.llm_client._cleanup_providers()

    async def on_message(self, message):
        # Use client for each message
        response = await self.llm_client.generate_simple_response(message)
        return response
```

Or better yet, use the context manager at the application level:

```python
async def run_bot():
    async with EnhancedLLMClient(...) as llm_client:
        bot = MyBot(llm_client)
        await bot.run()
```

## Benefits

### Resource Efficiency

- **Connection Pooling**: HTTP clients are reused across requests
- **Proper Cleanup**: Connections are properly closed, preventing leaks
- **Memory Management**: Resources are released when no longer needed

### Reliability

- **Guaranteed Cleanup**: Context manager ensures cleanup even during exceptions
- **Error Isolation**: Cleanup errors don't cascade to other providers
- **State Validation**: Runtime checks ensure proper initialization

### Code Quality

- **Explicit Lifecycle**: Clear initialization and cleanup points
- **Type Safety**: Full type hints for better IDE support
- **Documentation**: Clear usage patterns and examples

## Migration Guide

If you're using the old pattern:

```python
# Old pattern
client = create_llm_client(settings)
response = await client.generate_response(messages)
```

Update to:

```python
# New pattern
async with EnhancedLLMClient(
    anthropic_api_key=settings.anthropic_api_key,
    google_api_key=settings.google_api_key,
    openai_api_key=settings.openai_api_key,
) as client:
    response = await client.generate_response(messages)
```

## Testing

The lifecycle management can be tested as follows:

```python
import pytest

@pytest.mark.asyncio
async def test_lifecycle():
    """Test proper lifecycle management."""
    async with EnhancedLLMClient(
        anthropic_api_key="test-key"
    ) as client:
        assert client._initialized is True
        assert len(client.providers) > 0

    # After exit, should be cleaned up
    assert client._initialized is False
    assert len(client.providers) == 0

@pytest.mark.asyncio
async def test_runtime_error_without_init():
    """Test that using client without init raises error."""
    client = EnhancedLLMClient(anthropic_api_key="test-key")

    with pytest.raises(RuntimeError):
        await client.generate_simple_response("test")
```

## Related Documentation

- [Provider Implementation](./providers.md)
- [Circuit Breaker Pattern](./circuit_breaker.md)
- [Retry Strategies](./retry_strategies.md)
- [Error Handling](./error_handling.md)
