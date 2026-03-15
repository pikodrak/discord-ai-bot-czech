# Multi-LLM Client Module

This module provides a unified interface for interacting with multiple Large Language Model (LLM) providers with automatic fallback and retry logic.

## Features

- **Multi-Provider Support**: Claude (Anthropic), Gemini (Google), OpenAI
- **Automatic Fallback**: If one provider fails, automatically tries the next
- **Advanced Retry Logic**: Multiple strategies with exponential backoff and jitter
- **Circuit Breaker Pattern**: Prevents cascade failures and enables fast recovery
- **Czech Language Enforcement**: All responses automatically generated in Czech
- **Health Monitoring**: Comprehensive health checks and statistics
- **Type-Safe**: Full type hints and Pydantic integration
- **Error Handling**: Comprehensive exception hierarchy

## Client Types

### Standard Client (`LLMClient`)
- Basic multi-provider fallback
- Simple retry with exponential backoff
- Good for simple use cases

### Enhanced Client (`EnhancedLLMClient`) - **Recommended**
- All standard client features
- Circuit breaker pattern for each provider
- Advanced retry strategies (exponential, linear, fibonacci, fixed)
- Configurable jitter to prevent thundering herd
- Health monitoring and statistics
- Automatic recovery mechanisms

## Architecture

```
LLMClient (Main Client)
├── ClaudeProvider (Primary)
├── GeminiProvider (Fallback 1)
└── OpenAIProvider (Fallback 2)
```

## Quick Start

### Basic Usage (Enhanced Client - Recommended)

```python
from src.llm import EnhancedLLMClient, LLMMessage

# Create enhanced client with circuit breaker
client = EnhancedLLMClient(
    anthropic_api_key="your-api-key",
    google_api_key="your-api-key",
    openai_api_key="your-api-key",
    enable_circuit_breaker=True,
    max_retries=3
)

# Simple single message
response = await client.generate_simple_response("Ahoj, jak se máš?")
print(response)  # Response in Czech

# Conversation with history
messages = [
    LLMMessage(role="user", content="Jak se jmenuješ?"),
]
response = await client.generate_response(messages)
print(response.content)
print(f"Provider used: {response.provider}")
print(f"Tokens: {response.tokens_used}")

# Check health
health = await client.health_check()
print(f"Healthy: {health['healthy']}")
```

### Using Factory (Recommended)

```python
from src.llm import create_llm_client, LLMMessage
from src.config import get_settings

# Create enhanced client from settings (default)
settings = get_settings()
client = create_llm_client(
    settings,
    client_type="enhanced",  # default
    enable_circuit_breaker=True,
    max_retries=5
)

response = await client.generate_simple_response("Ahoj!")
print(response)
```

### Advanced Usage

```python
from src.llm import LLMClient, LLMMessage, get_default_system_prompt

# Manual initialization with specific API keys
client = LLMClient(
    anthropic_api_key="sk-ant-...",
    google_api_key="...",
    openai_api_key="sk-...",
    max_retries=3,
    retry_delay=1.0
)

# Custom system prompt
system_prompt = get_default_system_prompt(personality="friendly")
messages = [
    LLMMessage(role="user", content="Vysvětli mi kvantovou fyziku"),
]

response = await client.generate_response(
    messages=messages,
    system_prompt=system_prompt,
    temperature=0.7,
    max_tokens=2000
)

# Check provider availability
availability = await client.check_availability()
print(availability)  # {"claude": True, "gemini": True, "openai": False}
```

### Error Handling

```python
from src.llm import (
    LLMClient,
    LLMMessage,
    LLMAllProvidersFailedError,
    LLMProviderError,
)

try:
    response = await client.generate_response(messages)
except LLMAllProvidersFailedError as e:
    print(f"All providers failed: {e.errors}")
    # Handle fallback logic
except LLMProviderError as e:
    print(f"Provider {e.provider} failed: {e}")
```

## Provider Priority

The client tries providers in this order:

1. **Claude (Anthropic)** - Primary provider
   - Model: `claude-3-5-sonnet-20241022`
   - Best quality and instruction following

2. **Gemini (Google)** - Fallback 1
   - Model: `gemini-1.5-pro`
   - Good quality, fast responses

3. **OpenAI** - Fallback 2
   - Model: `gpt-4o`
   - Reliable fallback option

## Configuration

### Environment Variables

```bash
# Required: At least one API key
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENAI_API_KEY=sk-...

# Optional: Bot settings
BOT_LANGUAGE=cs
BOT_PERSONALITY=friendly
```

### Settings Integration

The module integrates with the existing `Settings` class:

```python
from src.config import Settings

settings = Settings()

# Check if AI is configured
if settings.has_any_ai_key():
    print(f"Preferred provider: {settings.get_preferred_ai_provider()}")
```

## Response Format

All provider responses are normalized to:

```python
@dataclass
class LLMResponse:
    content: str              # Generated text (in Czech)
    provider: str             # Provider name that generated this
    model: str                # Model name used
    tokens_used: int | None   # Total tokens used
    metadata: dict | None     # Provider-specific metadata
```

## Czech Language Enforcement

All providers automatically inject Czech language instructions:

```
IMPORTANT: You MUST respond ONLY in Czech language.
All responses must be in Czech (cs-CZ).
Never respond in English or any other language.
```

This ensures consistent Czech responses regardless of provider.

## Retry Logic

### Standard Client
- **Max Retries**: Configurable (default: 3)
- **Retry Delay**: Configurable (default: 1.0s)
- **Exponential Backoff**: For rate limit errors (2^attempt * base_delay)
- **No Retry Cases**: Authentication errors (skip to next provider)

### Enhanced Client
- **Multiple Strategies**:
  - Exponential backoff (default): 2^attempt * base_delay
  - Linear backoff: attempt * base_delay
  - Fibonacci backoff: fib(attempt) * base_delay
  - Fixed delay: constant base_delay
- **Jitter**: Random variance to prevent thundering herd (default: ±10%)
- **Max Delay Cap**: Configurable maximum delay (default: 60s)
- **Smart Retry**: Different strategies for different error types

## Circuit Breaker

The enhanced client includes circuit breaker pattern for each provider:

- **States**: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)
- **Failure Threshold**: Configurable failures before opening (default: 5)
- **Timeout**: How long to wait before testing recovery (default: 60s)
- **Success Threshold**: Successes needed in HALF_OPEN to close (default: 2)
- **Benefits**:
  - Fast failure when provider is down
  - Prevents resource exhaustion
  - Automatic recovery testing
  - Detailed statistics per provider

## Error Hierarchy

```
LLMError (Base)
├── LLMProviderError
│   ├── LLMRateLimitError
│   └── LLMAuthenticationError
└── LLMAllProvidersFailedError
```

## Testing

```python
# Check if providers are working
availability = await client.check_availability()
for provider, available in availability.items():
    print(f"{provider}: {'✓' if available else '✗'}")

# Get configured providers
providers = client.get_available_providers()
print(f"Available: {', '.join(providers)}")
```

## Integration Example

### Discord Bot Integration

```python
import discord
from src.llm import create_llm_client, LLMMessage, get_default_system_prompt
from src.config import get_settings

class DiscordBot(discord.Client):
    def __init__(self):
        super().__init__()
        settings = get_settings()
        self.llm_client = create_llm_client(settings)
        self.system_prompt = get_default_system_prompt(
            settings.bot_personality
        )

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Build conversation history
        messages = [
            LLMMessage(role="user", content=message.content)
        ]

        try:
            response = await self.llm_client.generate_response(
                messages=messages,
                system_prompt=self.system_prompt
            )
            await message.channel.send(response.content)
        except Exception as e:
            await message.channel.send(
                "Omlouváme se, došlo k chybě při generování odpovědi."
            )
```

## Additional Features

### Health Monitoring

```python
# Comprehensive health check
health = await client.health_check()
print(health)
# {
#   "healthy": True,
#   "total_providers": 3,
#   "healthy_providers": 2,
#   "provider_availability": {...},
#   "circuit_stats": {...},
#   "retry_config": {...}
# }

# Check specific provider availability
availability = await client.check_availability()
# {"claude": True, "gemini": True, "openai": False}

# Get circuit breaker statistics
stats = await client.get_circuit_stats()
for provider, provider_stats in stats.items():
    print(f"{provider}: {provider_stats['state']}")
    print(f"  Success rate: {provider_stats['success_rate']:.2%}")

# Reset all circuits
await client.reset_circuits()
```

### Error Handling (Enhanced)

```python
from src.llm import (
    EnhancedLLMClient,
    LLMAllProvidersFailedError,
    CircuitBreakerError,
)

try:
    response = await client.generate_response(messages)
except CircuitBreakerError as e:
    # Circuit is open, provider is temporarily disabled
    print(f"Circuit breaker is open: {e}")
    await asyncio.sleep(60)  # Wait for recovery
except LLMAllProvidersFailedError as e:
    # All providers failed
    for provider, error in e.errors.items():
        print(f"{provider}: {error}")
```

## Best Practices

1. **Use Enhanced Client** for production deployments
2. **Always use `create_llm_client()`** from factory for standard setup
3. **Handle `LLMAllProvidersFailedError`** for graceful degradation
4. **Use conversation history** for context-aware responses
5. **Monitor provider availability** periodically with health checks
6. **Configure retry parameters** based on your use case and rate limits
7. **Use appropriate temperature** (0.7 for conversation, 0.3 for facts)
8. **Enable circuit breakers** to prevent cascade failures
9. **Review circuit stats** to identify problematic providers
10. **Set appropriate thresholds** based on your SLA requirements

## Documentation

- **Detailed Examples**: See [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md)
- **Demo Script**: Run `examples/llm_client_demo.py`
- **API Reference**: See inline documentation in code

## Performance Considerations

- **Provider Switching**: Minimal overhead, happens only on failure
- **Retry Delays**: Configure based on expected traffic patterns
- **Token Usage**: Monitor via `response.tokens_used`
- **Async First**: All operations are async for better performance

## License

Part of the Discord AI Bot Czech project.
