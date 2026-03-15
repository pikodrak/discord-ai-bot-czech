"""
Demo script for testing the multi-LLM client with fallback logic.

This script demonstrates the usage of both standard and enhanced LLM clients
with various features including circuit breaker, retry logic, and health monitoring.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm import (
    EnhancedLLMClient,
    LLMClient,
    LLMMessage,
    LLMAllProvidersFailedError,
    CircuitBreakerError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def demo_basic_usage():
    """Demonstrate basic client usage."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Usage")
    print("="*60)

    # Create client with API keys from environment
    client = EnhancedLLMClient(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        language="cs",  # Czech language
    )

    # Simple question
    question = "Jaké je hlavní město České republiky?"
    print(f"\nQuestion: {question}")

    try:
        response = await client.generate_simple_response(question)
        print(f"Answer: {response}\n")
    except Exception as e:
        print(f"Error: {e}\n")


async def demo_conversation():
    """Demonstrate conversation with context."""
    print("\n" + "="*60)
    print("DEMO 2: Conversation with Context")
    print("="*60)

    client = EnhancedLLMClient(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Build a conversation
    messages = [
        LLMMessage(role="user", content="Ahoj! Jak se jmenuješ?"),
    ]

    print("\nUser: Ahoj! Jak se jmenuješ?")

    try:
        response = await client.generate_response(
            messages=messages,
            system_prompt="Jsi přátelský AI asistent v českém Discord serveru.",
            temperature=0.8,
            max_tokens=500
        )

        print(f"Assistant: {response.content}")
        print(f"(Provider: {response.provider}, Model: {response.model})")

        # Continue conversation
        messages.append(LLMMessage(role="assistant", content=response.content))
        messages.append(LLMMessage(role="user", content="Můžeš mi pomoci s programováním?"))

        print("\nUser: Můžeš mi pomoci s programováním?")

        response = await client.generate_response(
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        print(f"Assistant: {response.content}\n")

    except Exception as e:
        print(f"Error: {e}\n")


async def demo_provider_fallback():
    """Demonstrate provider fallback mechanism."""
    print("\n" + "="*60)
    print("DEMO 3: Provider Fallback")
    print("="*60)

    # Create client with potentially invalid first provider
    client = EnhancedLLMClient(
        anthropic_api_key="invalid-key-to-test-fallback",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        max_retries=2,
        retry_delay=0.5
    )

    print("\nTesting fallback with invalid Claude API key...")
    print("Should automatically fallback to Gemini or OpenAI\n")

    try:
        response = await client.generate_simple_response(
            "Řekni mi vtip o programování."
        )
        print(f"Successfully got response from fallback provider!")
        print(f"Response: {response}\n")
    except LLMAllProvidersFailedError as e:
        print(f"All providers failed: {e}\n")


async def demo_health_monitoring():
    """Demonstrate health monitoring features."""
    print("\n" + "="*60)
    print("DEMO 4: Health Monitoring")
    print("="*60)

    client = EnhancedLLMClient(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Check provider availability
    print("\nChecking provider availability...")
    availability = await client.check_availability()

    for provider, is_available in availability.items():
        status = "✓ Available" if is_available else "✗ Unavailable"
        print(f"  {provider}: {status}")

    # Full health check
    print("\nPerforming full health check...")
    health = await client.health_check()

    print(f"\nHealth Status:")
    print(f"  Overall healthy: {health['healthy']}")
    print(f"  Healthy providers: {health['healthy_providers']}/{health['total_providers']}")
    print(f"  Circuit breaker enabled: {health['circuit_breaker_enabled']}")
    print(f"  Retry config: {health['retry_config']}")


async def demo_circuit_breaker():
    """Demonstrate circuit breaker functionality."""
    print("\n" + "="*60)
    print("DEMO 5: Circuit Breaker")
    print("="*60)

    client = EnhancedLLMClient(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        enable_circuit_breaker=True,
        circuit_failure_threshold=3,  # Open circuit after 3 failures
        circuit_timeout=10.0,  # Try recovery after 10 seconds
    )

    print("\nCircuit breaker is enabled with:")
    print("  - Failure threshold: 3")
    print("  - Timeout: 10 seconds")
    print("  - Success threshold for recovery: 2")

    # Make a successful call
    print("\nMaking a successful call...")
    try:
        response = await client.generate_simple_response("Ahoj!")
        print(f"✓ Success: {response[:50]}...")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Check circuit stats
    print("\nCircuit breaker statistics:")
    stats = await client.get_circuit_stats()

    for provider, provider_stats in stats.items():
        print(f"\n  {provider}:")
        print(f"    State: {provider_stats['state']}")
        print(f"    Total calls: {provider_stats['total_calls']}")
        print(f"    Success rate: {provider_stats['success_rate']:.2%}")


async def demo_error_handling():
    """Demonstrate proper error handling."""
    print("\n" + "="*60)
    print("DEMO 6: Error Handling")
    print("="*60)

    # Create client with invalid keys
    client = EnhancedLLMClient(
        anthropic_api_key="invalid-key",
        google_api_key="invalid-key",
        openai_api_key="invalid-key",
        max_retries=1,
        retry_delay=0.5
    )

    print("\nAttempting to call with all invalid API keys...")
    print("Demonstrating comprehensive error handling...\n")

    try:
        response = await client.generate_simple_response("Test")
        print(f"Response: {response}")

    except CircuitBreakerError as e:
        print(f"Circuit breaker error: {e}")

    except LLMAllProvidersFailedError as e:
        print("All providers failed with the following errors:")
        for provider, error in e.errors.items():
            print(f"  {provider}: {type(error).__name__}")

    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")


async def demo_comparison():
    """Compare standard vs enhanced client."""
    print("\n" + "="*60)
    print("DEMO 7: Standard vs Enhanced Client Comparison")
    print("="*60)

    # Standard client
    print("\nStandard Client Features:")
    print("  - Multi-provider fallback")
    print("  - Basic retry with exponential backoff")
    print("  - Simple error handling")

    standard_client = LLMClient(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_retries=3,
        retry_delay=1.0
    )

    # Enhanced client
    print("\nEnhanced Client Features:")
    print("  - All standard features")
    print("  - Circuit breaker pattern")
    print("  - Advanced retry strategies")
    print("  - Health monitoring")
    print("  - Detailed statistics")

    enhanced_client = EnhancedLLMClient(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_retries=3,
        retry_delay=1.0,
        enable_circuit_breaker=True
    )

    # Test both
    test_message = "Pozdrav!"

    print(f"\nTesting both clients with: '{test_message}'")

    try:
        print("\nStandard client response:")
        response = await standard_client.generate_simple_response(test_message)
        print(f"  {response[:100]}...")

        print("\nEnhanced client response:")
        response = await enhanced_client.generate_simple_response(test_message)
        print(f"  {response[:100]}...")

    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("Multi-LLM Client Demo")
    print("="*60)

    # Check for API keys
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    has_google = bool(os.getenv("GOOGLE_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))

    print("\nAPI Keys Configuration:")
    print(f"  Anthropic (Claude): {'✓' if has_anthropic else '✗'}")
    print(f"  Google (Gemini): {'✓' if has_google else '✗'}")
    print(f"  OpenAI: {'✓' if has_openai else '✗'}")

    if not any([has_anthropic, has_google, has_openai]):
        print("\nWarning: No API keys found in environment variables!")
        print("Please set at least one of: ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY")
        print("\nSome demos will be skipped or may fail.\n")

    # Run demos
    demos = [
        ("Basic Usage", demo_basic_usage, has_anthropic or has_google or has_openai),
        ("Conversation", demo_conversation, has_anthropic or has_google or has_openai),
        ("Provider Fallback", demo_provider_fallback, has_google or has_openai),
        ("Health Monitoring", demo_health_monitoring, has_anthropic or has_google or has_openai),
        ("Circuit Breaker", demo_circuit_breaker, has_anthropic or has_google or has_openai),
        ("Error Handling", demo_error_handling, True),  # Always run
        ("Comparison", demo_comparison, has_anthropic or has_google or has_openai),
    ]

    for name, demo_func, should_run in demos:
        if should_run:
            try:
                await demo_func()
            except Exception as e:
                print(f"\nDemo '{name}' failed with error: {e}\n")
        else:
            print(f"\n{'='*60}")
            print(f"DEMO: {name}")
            print(f"{'='*60}")
            print("Skipped (no API keys configured)\n")

        # Small delay between demos
        await asyncio.sleep(1)

    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)
    print("\nFor more examples, see: src/llm/USAGE_EXAMPLES.md\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        sys.exit(1)
