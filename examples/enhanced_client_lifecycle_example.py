"""
Example demonstrating proper lifecycle management of EnhancedLLMClient.

This script shows how to use the EnhancedLLMClient with async context managers
for proper resource initialization and cleanup.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.client_enhanced import EnhancedLLMClient
from src.llm.base import LLMMessage
from src.llm.exceptions import LLMAllProvidersFailedError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def basic_context_manager_example():
    """
    Basic example using async context manager.

    This is the recommended way to use EnhancedLLMClient as it ensures
    proper resource initialization and cleanup.
    """
    print("\n=== Basic Context Manager Example ===\n")

    # Get API keys from environment
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not any([anthropic_key, google_key, openai_key]):
        print("Error: No API keys configured!")
        return

    # Use async context manager for proper lifecycle management
    async with EnhancedLLMClient(
        anthropic_api_key=anthropic_key,
        google_api_key=google_key,
        openai_api_key=openai_key,
        language="en",
        enable_circuit_breaker=True,
        max_retries=3,
    ) as client:
        print(f"Initialized providers: {client.get_available_providers()}")

        # Simple message
        try:
            response = await client.generate_simple_response(
                "Hello! Can you introduce yourself?"
            )
            print(f"\nResponse: {response}\n")
        except LLMAllProvidersFailedError as e:
            print(f"Error: All providers failed - {e.errors}")

    # Resources are automatically cleaned up when exiting the context
    print("Resources cleaned up automatically")


async def conversation_with_context_manager():
    """
    Example of multi-turn conversation with context manager.
    """
    print("\n=== Conversation with Context Manager ===\n")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")

    if not any([anthropic_key, google_key]):
        print("Error: No API keys configured!")
        return

    async with EnhancedLLMClient(
        anthropic_api_key=anthropic_key,
        google_api_key=google_key,
        language="en",
    ) as client:
        # Build conversation
        messages = [
            LLMMessage(role="user", content="What is Python?"),
        ]

        try:
            # First response
            response1 = await client.generate_response(messages)
            print(f"User: {messages[0].content}")
            print(f"Assistant: {response1.content}")
            print(f"Provider: {response1.provider}\n")

            # Continue conversation
            messages.append(LLMMessage(role="assistant", content=response1.content))
            messages.append(
                LLMMessage(role="user", content="Can you give me a simple code example?")
            )

            response2 = await client.generate_response(messages)
            print(f"User: {messages[2].content}")
            print(f"Assistant: {response2.content}")
            print(f"Provider: {response2.provider}\n")

        except LLMAllProvidersFailedError as e:
            print(f"Error: {e}")


async def health_check_example():
    """
    Example demonstrating health check functionality.
    """
    print("\n=== Health Check Example ===\n")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not any([anthropic_key, google_key, openai_key]):
        print("Error: No API keys configured!")
        return

    async with EnhancedLLMClient(
        anthropic_api_key=anthropic_key,
        google_api_key=google_key,
        openai_api_key=openai_key,
        enable_circuit_breaker=True,
    ) as client:
        # Perform health check
        health = await client.health_check()

        print("Health Check Results:")
        print(f"  Overall healthy: {health['healthy']}")
        print(f"  Total providers: {health['total_providers']}")
        print(f"  Healthy providers: {health['healthy_providers']}")
        print(f"  Initialized: {health['initialized']}")
        print(f"  Circuit breaker enabled: {health['circuit_breaker_enabled']}")

        print("\nProvider Availability:")
        for provider, available in health['provider_availability'].items():
            status = "✓ Available" if available else "✗ Unavailable"
            print(f"  {provider}: {status}")

        print("\nRetry Configuration:")
        retry_cfg = health['retry_config']
        print(f"  Max attempts: {retry_cfg['max_attempts']}")
        print(f"  Strategy: {retry_cfg['strategy']}")
        print(f"  Base delay: {retry_cfg['base_delay']}s")
        print()


async def circuit_breaker_example():
    """
    Example demonstrating circuit breaker functionality.
    """
    print("\n=== Circuit Breaker Example ===\n")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not anthropic_key:
        print("Error: ANTHROPIC_API_KEY not configured!")
        return

    async with EnhancedLLMClient(
        anthropic_api_key=anthropic_key,
        enable_circuit_breaker=True,
        circuit_failure_threshold=3,
        circuit_timeout=30.0,
    ) as client:
        # Check circuit breaker stats
        circuit_stats = await client.get_circuit_stats()

        print("Circuit Breaker Statistics:")
        if circuit_stats:
            for name, stats in circuit_stats.items():
                print(f"  {name}:")
                print(f"    State: {stats.get('state', 'unknown')}")
                print(f"    Failures: {stats.get('failure_count', 0)}")
                print(f"    Successes: {stats.get('success_count', 0)}")
        else:
            print("  No circuit breaker statistics available")
        print()


async def without_context_manager_example():
    """
    Example showing manual initialization (not recommended).

    This demonstrates that the client requires explicit initialization
    when not using the context manager pattern.
    """
    print("\n=== Manual Initialization Example (Not Recommended) ===\n")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not anthropic_key:
        print("Error: ANTHROPIC_API_KEY not configured!")
        return

    # Create client without context manager
    client = EnhancedLLMClient(
        anthropic_api_key=anthropic_key,
        language="en",
    )

    try:
        # This will fail because providers are not initialized
        response = await client.generate_simple_response("Hello!")
        print(f"Response: {response}")
    except RuntimeError as e:
        print(f"Expected error (providers not initialized): {e}\n")

    # Manual initialization
    await client._initialize_providers()

    try:
        response = await client.generate_simple_response("Hello!")
        print(f"Response after manual initialization: {response[:100]}...\n")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Manual cleanup
        await client._cleanup_providers()
        print("Manually cleaned up resources")


async def multiple_clients_example():
    """
    Example demonstrating multiple clients with different configurations.
    """
    print("\n=== Multiple Clients Example ===\n")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")

    if not all([anthropic_key, google_key]):
        print("Error: ANTHROPIC_API_KEY and GOOGLE_API_KEY required!")
        return

    # Create two clients with different configurations
    async with EnhancedLLMClient(
        anthropic_api_key=anthropic_key,
        language="en",
        temperature=0.3,  # More focused
    ) as client1, EnhancedLLMClient(
        google_api_key=google_key,
        language="en",
        temperature=0.9,  # More creative
    ) as client2:
        question = "What is the capital of France?"

        # Get response from first client (focused)
        response1 = await client1.generate_simple_response(question)
        print(f"Focused client response: {response1}\n")

        # Get response from second client (creative)
        response2 = await client2.generate_simple_response(question)
        print(f"Creative client response: {response2}\n")


async def main():
    """Run all examples."""
    print("=" * 70)
    print("EnhancedLLMClient Lifecycle Management Examples")
    print("=" * 70)

    # Check for API keys
    has_keys = any([
        os.getenv("ANTHROPIC_API_KEY"),
        os.getenv("GOOGLE_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
    ])

    if not has_keys:
        print("\nError: No API keys configured!")
        print("Please set at least one of these environment variables:")
        print("  - ANTHROPIC_API_KEY")
        print("  - GOOGLE_API_KEY")
        print("  - OPENAI_API_KEY")
        return

    # Run examples
    await basic_context_manager_example()
    await conversation_with_context_manager()
    await health_check_example()
    await circuit_breaker_example()
    await without_context_manager_example()

    # This example requires both Anthropic and Google keys
    if os.getenv("ANTHROPIC_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        await multiple_clients_example()

    print("=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
