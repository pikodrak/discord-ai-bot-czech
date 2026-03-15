"""
Factory for creating LLM client instances from configuration.
"""

import logging
from typing import Optional, Literal

from src.config import Settings
from src.llm.client import LLMClient
from src.llm.client_enhanced import EnhancedLLMClient

logger = logging.getLogger(__name__)


def create_llm_client(
    settings: Settings,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    client_type: Literal["standard", "enhanced"] = "enhanced",
    enable_circuit_breaker: bool = True,
    circuit_failure_threshold: int = 5,
    circuit_timeout: float = 60.0,
    language: Optional[str] = None,
) -> LLMClient | EnhancedLLMClient:
    """
    Create an LLM client from application settings.

    Args:
        settings: Application settings containing API keys
        max_retries: Maximum retry attempts per provider
        retry_delay: Delay between retries in seconds
        client_type: Type of client to create ("standard" or "enhanced")
        enable_circuit_breaker: Whether to enable circuit breaker (enhanced only)
        circuit_failure_threshold: Failures before opening circuit (enhanced only)
        circuit_timeout: Seconds before attempting recovery (enhanced only)
        language: Language code for responses (defaults to settings.bot_language or 'en')

    Returns:
        Configured LLMClient or EnhancedLLMClient instance

    Raises:
        ValueError: If no API keys are configured
    """
    if not settings.has_any_ai_key():
        raise ValueError(
            "No AI API keys configured. Please set at least one of: "
            "ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY"
        )

    # Determine language from parameter, settings, or default to 'en'
    bot_language = language or getattr(settings, 'bot_language', 'en')

    if client_type == "enhanced":
        client = EnhancedLLMClient(
            anthropic_api_key=settings.anthropic_api_key,
            google_api_key=settings.google_api_key,
            openai_api_key=settings.openai_api_key,
            max_retries=max_retries,
            retry_delay=retry_delay,
            enable_circuit_breaker=enable_circuit_breaker,
            circuit_failure_threshold=circuit_failure_threshold,
            circuit_timeout=circuit_timeout,
            language=bot_language,
        )
    else:
        client = LLMClient(
            anthropic_api_key=settings.anthropic_api_key,
            google_api_key=settings.google_api_key,
            openai_api_key=settings.openai_api_key,
            max_retries=max_retries,
            retry_delay=retry_delay,
            language=bot_language,
        )

    available_providers = client.get_available_providers()
    logger.info(
        f"LLM client ({client_type}) initialized with providers: {', '.join(available_providers)}, language: {bot_language}"
    )

    return client


def get_default_system_prompt(personality: str = "friendly") -> str:
    """
    Get default system prompt based on personality type.

    Args:
        personality: Personality type (friendly, professional, casual, etc.)

    Returns:
        System prompt string
    """
    base_prompt = (
        "You are a helpful AI assistant in a Discord server. "
        "You engage in natural conversations and provide helpful responses."
    )

    personality_prompts = {
        "friendly": (
            "You are warm, approachable, and enthusiastic. "
            "You use a conversational tone and occasionally use emojis when appropriate."
        ),
        "professional": (
            "You are professional, precise, and informative. "
            "You maintain a polite and formal tone."
        ),
        "casual": (
            "You are relaxed, informal, and easy-going. "
            "You use casual language and internet slang when appropriate."
        ),
        "helpful": (
            "You are patient, thorough, and focused on being as helpful as possible. "
            "You provide detailed explanations when needed."
        ),
    }

    personality_addition = personality_prompts.get(
        personality.lower(),
        personality_prompts["friendly"]
    )

    return f"{base_prompt}\n\n{personality_addition}"
