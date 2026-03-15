"""
Language utilities for LLM providers.

Provides helper functions to build language-specific system prompts
based on configured language codes.
"""

from typing import Optional


# Language code to full name mapping
LANGUAGE_NAMES = {
    "en": "English",
    "cs": "Czech (cs-CZ)",
    "sk": "Slovak (sk-SK)",
    "de": "German (de-DE)",
    "es": "Spanish (es-ES)",
    "fr": "French (fr-FR)",
}


def build_language_instruction(language: str = "en") -> str:
    """
    Build a language instruction prompt for the given language code.

    Args:
        language: Language code (e.g., 'en', 'cs', 'sk', 'de', 'es', 'fr')

    Returns:
        System prompt instruction text for the specified language

    Examples:
        >>> build_language_instruction("cs")
        'IMPORTANT: You MUST respond ONLY in Czech (cs-CZ) language. ...'

        >>> build_language_instruction("en")
        ''  # No instruction needed for English (default)
    """
    language = language.lower().strip()

    # No instruction needed for English (default behavior)
    if language == "en":
        return ""

    # Get the full language name
    language_name = LANGUAGE_NAMES.get(language, language.upper())

    # Build the instruction
    instruction = (
        f"IMPORTANT: You MUST respond ONLY in {language_name} language. "
        f"All responses must be in {language_name}. "
        f"Never respond in English or any other language."
    )

    return instruction


def apply_language_to_system_prompt(
    system_prompt: Optional[str],
    language: str = "en"
) -> str:
    """
    Apply language instruction to a system prompt.

    Args:
        system_prompt: Original system prompt (can be None or empty)
        language: Language code (e.g., 'en', 'cs', 'sk', 'de', 'es', 'fr')

    Returns:
        System prompt with language instruction appended (if applicable)

    Examples:
        >>> apply_language_to_system_prompt("You are helpful.", "cs")
        'You are helpful.\\n\\nIMPORTANT: You MUST respond ONLY in Czech...'

        >>> apply_language_to_system_prompt(None, "cs")
        'IMPORTANT: You MUST respond ONLY in Czech...'

        >>> apply_language_to_system_prompt("You are helpful.", "en")
        'You are helpful.'
    """
    language_instruction = build_language_instruction(language)

    # If no language instruction needed, return original prompt
    if not language_instruction:
        return system_prompt or ""

    # Combine system prompt with language instruction
    if system_prompt:
        return f"{system_prompt}\n\n{language_instruction}"
    else:
        return language_instruction
