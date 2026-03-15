# LLM Client Usage Examples

This document provides comprehensive examples of using the multi-LLM client wrapper with fallback logic.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Standard Client](#standard-client)
3. [Enhanced Client with Circuit Breaker](#enhanced-client-with-circuit-breaker)
4. [Factory Pattern](#factory-pattern)
5. [Error Handling](#error-handling)
6. [Health Monitoring](#health-monitoring)
7. [Retry Module Integration](#retry-module-integration)
8. [Advanced Configuration](#advanced-configuration)
   - [Retry Strategies](#retry-strategies)
   - [Custom Retry Logic](#custom-retry-logic)
   - [Czech Language Support](#czech-language-support)
   - [Discord Bot Integration](#discord-bot-integration)

## Basic Usage

### Simple Message Generation

```python
import asyncio
from src.llm import EnhancedLLMClient, LLMMessage

async def main():
    # Initialize client with API keys
    # Built-in retry logic with exponential backoff is automatically enabled
    client = EnhancedLLMClient(
        anthropic_api_key="your-claude-api-key",
        google_api_key="your-gemini-api-key",
        openai_api_key="your-openai-api-key"
    )

    # Generate a simple response
    # If a provider fails, automatic retry with exponential backoff occurs
    # If all retries fail, it falls back to the next provider
    response = await client.generate_simple_response(
        "Jaké je hlavní město České republiky?"
    )

    print(f"Response: {response}")
    # Output will be in Czech: "Hlavní město České republiky je Praha."

asyncio.run(main())
```

### Conversation with Context

```python
from src.llm import EnhancedLLMClient, LLMMessage

async def conversation_example():
    client = EnhancedLLMClient(
        anthropic_api_key="your-api-key"
    )

    # Create a conversation
    messages = [
        LLMMessage(role="user", content="Ahoj, jak se máš?"),
        LLMMessage(role="assistant", content="Ahoj! Mám se dobře, děkuji. Jak ti mohu pomoci?"),
        LLMMessage(role="user", content="Potřebuji pomoc s programováním v Pythonu.")
    ]

    # Generate response with system prompt
    response = await client.generate_response(
        messages=messages,
        system_prompt="Jsi užitečný Python programátorský asistent.",
        temperature=0.7,
        max_tokens=1000
    )

    print(f"Provider: {response.provider}")
    print(f"Model: {response.model}")
    print(f"Response: {response.content}")
    print(f"Tokens used: {response.tokens_used}")
```

## Standard Client

The standard client provides basic multi-provider fallback with retry logic.

```python
from src.llm import LLMClient, LLMMessage

async def standard_client_example():
    # Create standard client
    client = LLMClient(
        anthropic_api_key="your-claude-key",
        google_api_key="your-gemini-key",
        openai_api_key="your-openai-key",
        max_retries=3,
        retry_delay=1.0
    )

    # Check which providers are available
    providers = client.get_available_providers()
    print(f"Available providers: {providers}")

    # Generate response (will try providers in order: Claude -> Gemini -> OpenAI)
    messages = [LLMMessage(role="user", content="Pozdrav svět!")]
    response = await client.generate_response(messages)

    print(f"Used provider: {response.provider}")
    print(f"Response: {response.content}")
```

## Enhanced Client with Circuit Breaker

The enhanced client adds circuit breaker pattern and advanced retry strategies.

```python
from src.llm import EnhancedLLMClient, LLMMessage

async def enhanced_client_example():
    # Create enhanced client with circuit breaker
    client = EnhancedLLMClient(
        anthropic_api_key="your-claude-key",
        google_api_key="your-gemini-key",
        openai_api_key="your-openai-key",
        max_retries=3,
        retry_delay=1.0,
        enable_circuit_breaker=True,
        circuit_failure_threshold=5,  # Open circuit after 5 failures
        circuit_timeout=60.0  # Try recovery after 60 seconds
    )

    # Generate response
    messages = [LLMMessage(role="user", content="Vysvětli kvantovou fyziku.")]
    response = await client.generate_response(
        messages=messages,
        temperature=0.8,
        max_tokens=2000
    )

    print(f"Response: {response.content}")

    # Check circuit breaker stats
    stats = await client.get_circuit_stats()
    for provider, provider_stats in stats.items():
        print(f"\n{provider} circuit stats:")
        print(f"  State: {provider_stats['state']}")
        print(f"  Total calls: {provider_stats['total_calls']}")
        print(f"  Success rate: {provider_stats['success_rate']:.2%}")
```

## Factory Pattern

Use the factory to create clients from configuration.

```python
from src.llm import create_llm_client
from src.config import Settings

async def factory_example():
    # Load settings from environment
    settings = Settings()

    # Create enhanced client (default)
    client = create_llm_client(
        settings=settings,
        max_retries=5,
        retry_delay=2.0,
        client_type="enhanced",
        enable_circuit_breaker=True
    )

    # Or create standard client
    standard_client = create_llm_client(
        settings=settings,
        client_type="standard"
    )

    # Use the client
    response = await client.generate_simple_response("Ahoj!")
    print(response)
```

## Error Handling

Proper error handling for different failure scenarios.

```python
from src.llm import (
    EnhancedLLMClient,
    LLMMessage,
    LLMAllProvidersFailedError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMProviderError
)
from src.llm.circuit_breaker import CircuitBreakerError

async def error_handling_example():
    client = EnhancedLLMClient(anthropic_api_key="your-key")

    try:
        messages = [LLMMessage(role="user", content="Test")]
        response = await client.generate_response(messages)
        print(response.content)

    except CircuitBreakerError as e:
        print(f"Circuit breaker is open: {e}")
        # Wait and retry, or use fallback logic

    except LLMAuthenticationError as e:
        print(f"Authentication failed for {e.provider}: {e}")
        # Check API key configuration

    except LLMRateLimitError as e:
        print(f"Rate limit hit for {e.provider}: {e}")
        # Implement backoff or wait

    except LLMProviderError as e:
        print(f"Provider {e.provider} error: {e}")
        # Log error and notify

    except LLMAllProvidersFailedError as e:
        print("All providers failed:")
        for provider, error in e.errors.items():
            print(f"  {provider}: {error}")
        # Use fallback response or notify user
```

## Health Monitoring

Monitor the health of your LLM client.

```python
from src.llm import EnhancedLLMClient
import json

async def health_monitoring_example():
    client = EnhancedLLMClient(
        anthropic_api_key="your-claude-key",
        google_api_key="your-gemini-key",
        openai_api_key="your-openai-key"
    )

    # Perform health check
    health = await client.health_check()

    print("=== LLM Client Health Status ===")
    print(json.dumps(health, indent=2))

    # Check individual provider availability
    availability = await client.check_availability()
    print("\n=== Provider Availability ===")
    for provider, is_available in availability.items():
        status = "✓ Available" if is_available else "✗ Unavailable"
        print(f"{provider}: {status}")

    # Get circuit breaker statistics
    circuit_stats = await client.get_circuit_stats()
    print("\n=== Circuit Breaker Stats ===")
    for provider, stats in circuit_stats.items():
        print(f"\n{provider}:")
        print(f"  State: {stats['state']}")
        print(f"  Total calls: {stats['total_calls']}")
        print(f"  Total failures: {stats['total_failures']}")
        print(f"  Success rate: {stats['success_rate']:.2%}")

    # Reset circuits if needed
    if health['healthy_providers'] == 0:
        print("\nNo healthy providers, resetting circuits...")
        await client.reset_circuits()
```

## Advanced Configuration

### Retry Strategies

The LLM client uses a consolidated retry module with multiple backoff strategies.

#### Using Built-in Retry Handler

```python
from src.llm import (
    EnhancedLLMClient,
    RetryHandler,
    RetryConfig,
    RetryStrategy
)

async def custom_retry_example():
    # Enhanced client with custom retry configuration
    client = EnhancedLLMClient(
        anthropic_api_key="your-key",
        max_retries=5,
        retry_delay=2.0,  # Base delay of 2 seconds
        enable_circuit_breaker=True,
        circuit_failure_threshold=3,
        circuit_timeout=30.0
    )

    # The client internally uses exponential backoff:
    # Attempt 1: immediate
    # Attempt 2: ~2s delay (with jitter)
    # Attempt 3: ~4s delay (with jitter)
    # Attempt 4: ~8s delay (with jitter)
    # Attempt 5: ~16s delay (with jitter)

    response = await client.generate_simple_response("Test")
    print(response)
```

#### Available Retry Strategies

```python
from src.llm import RetryHandler, RetryConfig, RetryStrategy

# 1. Exponential Backoff (default)
# Delay doubles with each retry: 1s, 2s, 4s, 8s, 16s...
exponential_config = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    exponential_base=2.0,
    jitter=True,
    jitter_range=0.1  # ±10% jitter to prevent thundering herd
)

# 2. Linear Backoff
# Delay increases linearly: 1s, 2s, 3s, 4s, 5s...
linear_config = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    strategy=RetryStrategy.LINEAR_BACKOFF
)

# 3. Fibonacci Backoff
# Delay follows Fibonacci sequence: 1s, 1s, 2s, 3s, 5s, 8s...
fibonacci_config = RetryConfig(
    max_attempts=6,
    base_delay=1.0,
    strategy=RetryStrategy.FIBONACCI_BACKOFF
)

# 4. Fixed Delay
# Constant delay between retries: 2s, 2s, 2s, 2s...
fixed_config = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    strategy=RetryStrategy.FIXED_DELAY
)

# Create handler with chosen strategy
retry_handler = RetryHandler(exponential_config)
```

#### Custom Retry Logic

```python
from src.llm import RetryHandler, RetryConfig
from src.llm.exceptions import LLMRateLimitError

async def custom_operation_with_retry():
    """Example of using retry handler for custom operations."""

    # Configure retry behavior
    config = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True
    )

    retry_handler = RetryHandler(config)

    # Define your async operation
    async def risky_operation():
        # Your code that might fail
        response = await some_api_call()
        return response

    # Execute with retry logic
    try:
        result = await retry_handler.execute_with_retry(
            risky_operation,
            retryable_exceptions=(LLMRateLimitError, ConnectionError),
            do_not_retry_on=(ValueError, KeyError),
            on_retry=lambda exc, attempt: print(f"Retry {attempt + 1}: {exc}")
        )
        return result
    except Exception as e:
        print(f"Operation failed after all retries: {e}")
        raise
```

#### Retry with Custom Callbacks

```python
from src.llm import RetryHandler, RetryConfig, RetryStrategy

async def retry_with_callbacks():
    """Example of using retry callbacks for monitoring."""

    # Track retry attempts
    retry_count = 0

    def on_retry_callback(exception: Exception, attempt: int) -> None:
        """Called after each failed attempt."""
        nonlocal retry_count
        retry_count = attempt + 1
        print(f"Attempt {attempt + 1} failed: {type(exception).__name__}")

        # You can add custom logic here:
        # - Send metrics to monitoring system
        # - Log to external service
        # - Adjust retry strategy dynamically

    config = RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )

    handler = RetryHandler(config)

    result = await handler.execute_with_retry(
        your_async_function,
        arg1="value",
        arg2=42,
        on_retry=on_retry_callback
    )

    print(f"Total retries: {retry_count}")
    return result
```

#### Factory Function for Quick Setup

```python
from src.llm.retry_strategy import create_retry_handler, RetryStrategy

# Quick setup with sensible defaults
handler = create_retry_handler(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    jitter=True
)

# Use it immediately
result = await handler.execute_with_retry(my_operation)
```

### Czech Language Support

All providers are automatically configured to respond in Czech.

```python
from src.llm import EnhancedLLMClient, LLMMessage

async def czech_language_example():
    client = EnhancedLLMClient(anthropic_api_key="your-key")

    # All responses will be in Czech automatically
    questions = [
        "What is the capital of France?",  # English question
        "Kolik je 2 + 2?",  # Czech question
        "Explain quantum physics",  # English question
    ]

    for question in questions:
        response = await client.generate_simple_response(question)
        print(f"\nQ: {question}")
        print(f"A: {response}")
        # All answers will be in Czech regardless of question language
```

### Discord Bot Integration

```python
import discord
from discord.ext import commands
from src.llm import EnhancedLLMClient, LLMMessage

class AIBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.llm_client = EnhancedLLMClient(
            anthropic_api_key=bot.config.anthropic_api_key,
            google_api_key=bot.config.google_api_key,
            openai_api_key=bot.config.openai_api_key,
            enable_circuit_breaker=True
        )

        # Store conversation history per channel
        self.conversations = {}

    @commands.command(name="ask")
    async def ask(self, ctx, *, question: str):
        """Ask the AI a question."""
        channel_id = ctx.channel.id

        # Get or create conversation history
        if channel_id not in self.conversations:
            self.conversations[channel_id] = []

        # Add user message
        self.conversations[channel_id].append(
            LLMMessage(role="user", content=question)
        )

        # Keep only last 10 messages
        self.conversations[channel_id] = self.conversations[channel_id][-10:]

        try:
            async with ctx.typing():
                response = await self.llm_client.generate_response(
                    messages=self.conversations[channel_id],
                    system_prompt="Jsi přátelský Discord bot asistent.",
                    temperature=0.7,
                    max_tokens=1000
                )

                # Add assistant response to history
                self.conversations[channel_id].append(
                    LLMMessage(role="assistant", content=response.content)
                )

                await ctx.send(response.content)

        except Exception as e:
            await ctx.send(f"Omlouvám se, došlo k chybě: {str(e)}")

    @commands.command(name="reset")
    async def reset_conversation(self, ctx):
        """Reset conversation history."""
        channel_id = ctx.channel.id
        self.conversations[channel_id] = []
        await ctx.send("Konverzace byla resetována.")

    @commands.command(name="health")
    async def health_check(self, ctx):
        """Check LLM client health."""
        health = await self.llm_client.health_check()

        status_emoji = "✅" if health['healthy'] else "❌"
        message = f"{status_emoji} **LLM Client Status**\n"
        message += f"Zdravé providery: {health['healthy_providers']}/{health['total_providers']}\n\n"

        for provider, available in health['provider_availability'].items():
            emoji = "✓" if available else "✗"
            message += f"{emoji} {provider}\n"

        await ctx.send(message)

async def setup(bot):
    await bot.add_cog(AIBot(bot))
```

## Retry Module Integration

The LLM client uses a consolidated retry module (`src.llm.retry_strategy`) that provides:

- **Multiple backoff strategies**: Exponential, Linear, Fibonacci, Fixed delay
- **Jitter support**: Prevents thundering herd problem
- **Configurable retry conditions**: Control which exceptions trigger retries
- **Custom callbacks**: Monitor and respond to retry events
- **Type-safe configuration**: Validated retry parameters

### How Retry Works in LLM Client

The `EnhancedLLMClient` integrates retry logic at initialization:

```python
from src.llm import EnhancedLLMClient

client = EnhancedLLMClient(
    anthropic_api_key="your-key",
    max_retries=3,        # Passed to RetryConfig.max_attempts
    retry_delay=1.0,      # Passed to RetryConfig.base_delay
)

# Internally creates:
# RetryHandler(RetryConfig(
#     max_attempts=3,
#     base_delay=1.0,
#     max_delay=60.0,
#     strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
#     jitter=True,
#     jitter_range=0.1
# ))
```

The retry handler is used for each provider call and integrates seamlessly with the circuit breaker pattern.

### Retry Flow Diagram

```
User Request
    ↓
Enhanced LLM Client
    ↓
Try Provider 1 (e.g., Claude)
    ↓
Circuit Breaker Check
    ↓
Retry Handler (3 attempts with exponential backoff)
    ├─ Attempt 1: Immediate
    ├─ Attempt 2: ~1s delay + jitter
    └─ Attempt 3: ~2s delay + jitter
    ↓
If all attempts fail → Try Provider 2 (e.g., Gemini)
    ↓
Circuit Breaker Check
    ↓
Retry Handler (3 attempts)
    ↓
If all attempts fail → Try Provider 3 (e.g., OpenAI)
    ↓
If all providers fail → LLMAllProvidersFailedError
```

## Best Practices

1. **Always use environment variables for API keys**
   ```python
   import os
   from src.llm import EnhancedLLMClient

   client = EnhancedLLMClient(
       anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
       google_api_key=os.getenv("GOOGLE_API_KEY"),
       openai_api_key=os.getenv("OPENAI_API_KEY")
   )
   ```

2. **Implement proper error handling**
   - Always catch specific exceptions
   - Log errors for debugging
   - Provide user-friendly error messages

3. **Monitor health regularly**
   - Implement health check endpoints
   - Track circuit breaker statistics
   - Set up alerts for failures

4. **Use appropriate retry configurations**
   - Adjust based on your use case
   - Consider rate limits
   - Balance between reliability and latency

5. **Manage conversation context**
   - Limit message history to prevent token overflow
   - Clear old conversations periodically
   - Use appropriate max_tokens settings

## Environment Variables

Create a `.env` file with your API keys:

```env
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
OPENAI_API_KEY=sk-proj-...
```

Load them in your application:

```python
from dotenv import load_dotenv
import os

load_dotenv()

# Keys are now available via os.getenv()
```
