"""
Example usage of the multi-LLM client.

This script demonstrates how to use the LLM client for generating
Czech language responses with automatic fallback between providers.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.llm import (
    create_llm_client,
    LLMMessage,
    get_default_system_prompt,
    LLMAllProvidersFailedError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def simple_example():
    """Simple single-message example."""
    print("\n=== Simple Example ===")

    settings = get_settings()
    client = create_llm_client(settings)

    try:
        response = await client.generate_simple_response(
            "Ahoj! Jak se máš? Můžeš mi říct něco o sobě?"
        )
        print(f"\nResponse: {response}\n")
    except LLMAllProvidersFailedError as e:
        print(f"Error: All providers failed - {e.errors}")


async def conversation_example():
    """Example with conversation history."""
    print("\n=== Conversation Example ===")

    settings = get_settings()
    client = create_llm_client(settings)

    # Simulate a conversation
    messages = [
        LLMMessage(role="user", content="Ahoj, jak se jmenuješ?"),
    ]

    try:
        response = await client.generate_response(messages)
        print(f"\nUser: {messages[0].content}")
        print(f"Assistant: {response.content}")
        print(f"Provider: {response.provider}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.tokens_used}\n")

        # Continue conversation
        messages.append(LLMMessage(role="assistant", content=response.content))
        messages.append(LLMMessage(role="user", content="Můžeš mi pomoci s programováním v Pythonu?"))

        response = await client.generate_response(messages)
        print(f"User: {messages[2].content}")
        print(f"Assistant: {response.content}")
        print(f"Provider: {response.provider}\n")

    except LLMAllProvidersFailedError as e:
        print(f"Error: {e}")


async def custom_system_prompt_example():
    """Example with custom system prompt."""
    print("\n=== Custom System Prompt Example ===")

    settings = get_settings()
    client = create_llm_client(settings)

    # Get friendly personality system prompt
    system_prompt = get_default_system_prompt(personality="friendly")

    messages = [
        LLMMessage(role="user", content="Vysvětli mi, co je to machine learning, ale jednoduše."),
    ]

    try:
        response = await client.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=500
        )
        print(f"\nUser: {messages[0].content}")
        print(f"Assistant: {response.content}")
        print(f"Provider: {response.provider}\n")

    except LLMAllProvidersFailedError as e:
        print(f"Error: {e}")


async def provider_availability_example():
    """Check provider availability."""
    print("\n=== Provider Availability Example ===")

    settings = get_settings()
    client = create_llm_client(settings)

    print(f"\nConfigured providers: {', '.join(client.get_available_providers())}")

    availability = await client.check_availability()
    print("\nProvider availability:")
    for provider, available in availability.items():
        status = "✓ Available" if available else "✗ Unavailable"
        print(f"  {provider}: {status}")
    print()


async def error_handling_example():
    """Demonstrate error handling."""
    print("\n=== Error Handling Example ===")

    # Create client with invalid API keys to trigger errors
    from src.llm import LLMClient

    client = LLMClient(
        anthropic_api_key="invalid_key",
        google_api_key="invalid_key",
        openai_api_key="invalid_key",
        max_retries=1,  # Reduced for faster demonstration
        retry_delay=0.5,
        language="cs"  # Czech language
    )

    messages = [LLMMessage(role="user", content="Test message")]

    try:
        response = await client.generate_response(messages)
        print(f"Response: {response.content}")
    except LLMAllProvidersFailedError as e:
        print("\nAll providers failed (as expected with invalid keys):")
        for provider, error in e.errors.items():
            print(f"  {provider}: {type(error).__name__} - {error}")
    print()


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Multi-LLM Client Examples")
    print("=" * 60)

    # Check if at least one API key is configured
    settings = get_settings()
    if not settings.has_any_ai_key():
        print("\nError: No API keys configured!")
        print("Please set at least one of these environment variables:")
        print("  - ANTHROPIC_API_KEY")
        print("  - GOOGLE_API_KEY")
        print("  - OPENAI_API_KEY")
        return

    print(f"\nPreferred provider: {settings.get_preferred_ai_provider()}")

    # Run examples
    await simple_example()
    await conversation_example()
    await custom_system_prompt_example()
    await provider_availability_example()

    # Uncomment to test error handling (will show errors)
    # await error_handling_example()

    print("=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
