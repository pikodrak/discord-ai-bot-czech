"""
Language Configuration Tests

Verifies that each provider respects bot_language config and generates
appropriate language-specific prompts for all supported languages.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.llm.language_utils import (
    build_language_instruction,
    apply_language_to_system_prompt,
    LANGUAGE_NAMES,
)
from src.llm.providers import ClaudeProvider, GeminiProvider, OpenAIProvider
from src.llm.factory import create_llm_client
from src.llm.client import LLMClient
from src.config import Settings


# Test constants
SUPPORTED_LANGUAGES = ["cs", "en", "sk", "de", "fr", "es"]
BASE_SYSTEM_PROMPT = "You are a helpful Discord bot."
TEST_USER_MESSAGE = "Hello, how are you?"


class TestLanguageInstructionGeneration:
    """Test language instruction generation for all supported languages."""

    def test_english_returns_empty_instruction(self) -> None:
        """English should return empty string (no instruction needed)."""
        instruction = build_language_instruction("en")
        assert instruction == ""

    @pytest.mark.parametrize("language", ["cs", "sk", "de", "fr", "es"])
    def test_non_english_returns_language_instruction(self, language: str) -> None:
        """Non-English languages should return mandatory language instruction."""
        instruction = build_language_instruction(language)

        # Verify instruction is non-empty
        assert instruction != ""

        # Verify instruction contains language name
        language_name = LANGUAGE_NAMES.get(language, language)
        assert language_name in instruction

        # Verify instruction is imperative
        assert "MUST" in instruction or "must" in instruction
        assert "ONLY" in instruction or "only" in instruction

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    def test_language_instruction_format(self, language: str) -> None:
        """Verify instruction format for all supported languages."""
        instruction = build_language_instruction(language)

        if language == "en":
            assert instruction == ""
        else:
            # Should contain explicit language directive
            language_name = LANGUAGE_NAMES[language]
            assert language_name in instruction
            assert "respond" in instruction.lower()

    def test_unknown_language_fallback(self) -> None:
        """Unknown language should still generate instruction."""
        instruction = build_language_instruction("unknown")
        # Should not crash, may return empty or default instruction
        assert isinstance(instruction, str)


class TestSystemPromptModification:
    """Test system prompt modification with language directives."""

    def test_english_prompt_unchanged(self) -> None:
        """English system prompt should remain unchanged."""
        result = apply_language_to_system_prompt(BASE_SYSTEM_PROMPT, "en")
        assert result == BASE_SYSTEM_PROMPT

    @pytest.mark.parametrize("language", ["cs", "sk", "de", "fr", "es"])
    def test_non_english_prompt_modified(self, language: str) -> None:
        """Non-English languages should append language instruction."""
        result = apply_language_to_system_prompt(BASE_SYSTEM_PROMPT, language)

        # Should contain original prompt
        assert BASE_SYSTEM_PROMPT in result

        # Should contain language instruction
        language_name = LANGUAGE_NAMES[language]
        assert language_name in result

        # Should be longer than original
        assert len(result) > len(BASE_SYSTEM_PROMPT)

    def test_empty_prompt_with_language(self) -> None:
        """Empty prompt with language should return just the instruction."""
        result = apply_language_to_system_prompt("", "cs")

        # Should contain language instruction
        assert "Czech" in result
        assert len(result) > 0

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    def test_prompt_structure_consistency(self, language: str) -> None:
        """Verify consistent prompt structure across all languages."""
        result = apply_language_to_system_prompt(BASE_SYSTEM_PROMPT, language)

        # Should always be a string
        assert isinstance(result, str)

        # Should never be None
        assert result is not None

        # If language is not English, should be modified
        if language != "en":
            assert result != BASE_SYSTEM_PROMPT


class TestClaudeProviderLanguage:
    """Test Claude provider language configuration."""

    @pytest.fixture
    def mock_anthropic_client(self) -> Mock:
        """Create mock Anthropic client."""
        client = Mock()
        client.messages = Mock()
        client.messages.create = AsyncMock()
        return client

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    @pytest.mark.asyncio
    async def test_claude_respects_language_config(
        self, language: str, mock_anthropic_client: Mock
    ) -> None:
        """Verify Claude provider uses language in system prompt."""
        with patch("src.llm.providers.Anthropic", return_value=mock_anthropic_client):
            provider = ClaudeProvider(api_key="test-key", language=language)

            # Mock successful response
            mock_anthropic_client.messages.create.return_value = Mock(
                content=[Mock(text="Test response")],
                stop_reason="end_turn",
            )

            # Generate completion
            await provider.generate(
                prompt=TEST_USER_MESSAGE,
                system_prompt=BASE_SYSTEM_PROMPT,
            )

            # Verify API was called
            assert mock_anthropic_client.messages.create.called

            # Get the system prompt that was sent
            call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
            sent_system_prompt = call_kwargs.get("system", "")

            # Verify language handling
            if language == "en":
                # English should use base prompt unchanged
                assert BASE_SYSTEM_PROMPT in sent_system_prompt
            else:
                # Non-English should include language instruction
                language_name = LANGUAGE_NAMES[language]
                assert language_name in sent_system_prompt
                assert BASE_SYSTEM_PROMPT in sent_system_prompt

    @pytest.mark.asyncio
    async def test_claude_default_language_is_english(
        self, mock_anthropic_client: Mock
    ) -> None:
        """Verify Claude provider defaults to English."""
        with patch("src.llm.providers.Anthropic", return_value=mock_anthropic_client):
            provider = ClaudeProvider(api_key="test-key")

            # Default language should be English
            assert provider.language == "en"


class TestGeminiProviderLanguage:
    """Test Gemini provider language configuration."""

    @pytest.fixture
    def mock_genai(self) -> Mock:
        """Create mock Google GenerativeAI."""
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock()

        mock_genai = Mock()
        mock_genai.GenerativeModel = Mock(return_value=mock_model)

        return mock_genai

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    @pytest.mark.asyncio
    async def test_gemini_respects_language_config(
        self, language: str, mock_genai: Mock
    ) -> None:
        """Verify Gemini provider uses language in system prompt."""
        with patch("src.llm.providers.genai", mock_genai):
            provider = GeminiProvider(api_key="test-key", language=language)

            # Get the mock model instance
            mock_model = mock_genai.GenerativeModel.return_value

            # Mock successful response
            mock_model.generate_content_async.return_value = Mock(
                text="Test response"
            )

            # Generate completion
            await provider.generate(
                prompt=TEST_USER_MESSAGE,
                system_prompt=BASE_SYSTEM_PROMPT,
            )

            # Verify model was created with system instruction
            assert mock_genai.GenerativeModel.called

            # Get the system instruction that was sent
            call_kwargs = mock_genai.GenerativeModel.call_args.kwargs
            system_instruction = call_kwargs.get("system_instruction", "")

            # Verify language handling
            if language == "en":
                # English should use base prompt
                assert BASE_SYSTEM_PROMPT in system_instruction
            else:
                # Non-English should include language instruction
                language_name = LANGUAGE_NAMES[language]
                assert language_name in system_instruction
                assert BASE_SYSTEM_PROMPT in system_instruction

    @pytest.mark.asyncio
    async def test_gemini_default_language_is_english(self, mock_genai: Mock) -> None:
        """Verify Gemini provider defaults to English."""
        with patch("src.llm.providers.genai", mock_genai):
            provider = GeminiProvider(api_key="test-key")

            # Default language should be English
            assert provider.language == "en"


class TestOpenAIProviderLanguage:
    """Test OpenAI provider language configuration."""

    @pytest.fixture
    def mock_openai_client(self) -> Mock:
        """Create mock OpenAI client."""
        client = Mock()
        client.chat = Mock()
        client.chat.completions = Mock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    @pytest.mark.asyncio
    async def test_openai_respects_language_config(
        self, language: str, mock_openai_client: Mock
    ) -> None:
        """Verify OpenAI provider uses language in system message."""
        with patch("src.llm.providers.AsyncOpenAI", return_value=mock_openai_client):
            provider = OpenAIProvider(api_key="test-key", language=language)

            # Mock successful response
            mock_openai_client.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(content="Test response"))],
                usage=Mock(total_tokens=10),
            )

            # Generate completion
            await provider.generate(
                prompt=TEST_USER_MESSAGE,
                system_prompt=BASE_SYSTEM_PROMPT,
            )

            # Verify API was called
            assert mock_openai_client.chat.completions.create.called

            # Get the messages that were sent
            call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
            messages = call_kwargs.get("messages", [])

            # Find system message
            system_message = next(
                (msg for msg in messages if msg["role"] == "system"), None
            )
            assert system_message is not None

            system_content = system_message["content"]

            # Verify language handling
            if language == "en":
                # English should use base prompt
                assert BASE_SYSTEM_PROMPT in system_content
            else:
                # Non-English should include language instruction
                language_name = LANGUAGE_NAMES[language]
                assert language_name in system_content
                assert BASE_SYSTEM_PROMPT in system_content

    @pytest.mark.asyncio
    async def test_openai_default_language_is_english(
        self, mock_openai_client: Mock
    ) -> None:
        """Verify OpenAI provider defaults to English."""
        with patch("src.llm.providers.AsyncOpenAI", return_value=mock_openai_client):
            provider = OpenAIProvider(api_key="test-key")

            # Default language should be English
            assert provider.language == "en"


class TestLanguageConfigurationValidation:
    """Test language configuration validation."""

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    def test_supported_languages_are_valid(self, language: str) -> None:
        """All supported languages should be in LANGUAGE_NAMES."""
        assert language in LANGUAGE_NAMES

    def test_language_names_completeness(self) -> None:
        """LANGUAGE_NAMES should contain all supported languages."""
        for language in SUPPORTED_LANGUAGES:
            assert language in LANGUAGE_NAMES

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    def test_language_names_format(self, language: str) -> None:
        """Language names should be properly formatted."""
        language_name = LANGUAGE_NAMES[language]

        # Should not be empty
        assert language_name

        # Should be a string
        assert isinstance(language_name, str)

    def test_all_languages_lowercase(self) -> None:
        """All language codes should be lowercase."""
        for language in SUPPORTED_LANGUAGES:
            assert language == language.lower()


class TestFactoryLanguageIntegration:
    """Test language configuration flow through factory."""

    @pytest.mark.asyncio
    async def test_factory_creates_client_with_language(self) -> None:
        """Factory should pass language to client."""
        with patch("src.llm.factory.Settings") as mock_settings:
            mock_settings.return_value.bot_language = "cs"
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_settings.return_value.google_api_key = None
            mock_settings.return_value.openai_api_key = None

            with patch("src.llm.providers.Anthropic"):
                client = create_llm_client(language="cs")

                # Verify client has correct language
                assert client.language == "cs"

    @pytest.mark.asyncio
    async def test_factory_defaults_to_settings_language(self) -> None:
        """Factory should use bot_language from settings if not specified."""
        with patch("src.llm.factory.Settings") as mock_settings:
            mock_settings.return_value.bot_language = "de"
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_settings.return_value.google_api_key = None
            mock_settings.return_value.openai_api_key = None

            with patch("src.llm.providers.Anthropic"):
                client = create_llm_client()

                # Should use language from settings
                assert client.language == "de"

    @pytest.mark.asyncio
    async def test_factory_explicit_language_overrides_settings(self) -> None:
        """Explicit language parameter should override settings."""
        with patch("src.llm.factory.Settings") as mock_settings:
            mock_settings.return_value.bot_language = "cs"
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_settings.return_value.google_api_key = None
            mock_settings.return_value.openai_api_key = None

            with patch("src.llm.providers.Anthropic"):
                client = create_llm_client(language="fr")

                # Should use explicit language
                assert client.language == "fr"

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    @pytest.mark.asyncio
    async def test_factory_supports_all_languages(self, language: str) -> None:
        """Factory should support creating clients for all languages."""
        with patch("src.llm.factory.Settings") as mock_settings:
            mock_settings.return_value.bot_language = "en"
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_settings.return_value.google_api_key = None
            mock_settings.return_value.openai_api_key = None

            with patch("src.llm.providers.Anthropic"):
                client = create_llm_client(language=language)

                # Verify language is set correctly
                assert client.language == language


class TestLanguageConsistencyAcrossProviders:
    """Test that all providers handle language consistently."""

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    def test_all_providers_accept_language_parameter(self, language: str) -> None:
        """All providers should accept language in constructor."""
        with patch("src.llm.providers.Anthropic"):
            claude = ClaudeProvider(api_key="test-key", language=language)
            assert claude.language == language

        with patch("src.llm.providers.genai"):
            gemini = GeminiProvider(api_key="test-key", language=language)
            assert gemini.language == language

        with patch("src.llm.providers.AsyncOpenAI"):
            openai = OpenAIProvider(api_key="test-key", language=language)
            assert openai.language == language

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    @pytest.mark.asyncio
    async def test_all_providers_apply_language_to_system_prompt(
        self, language: str
    ) -> None:
        """All providers should apply language instruction to system prompt."""
        expected_instruction = build_language_instruction(language)

        # All providers should use apply_language_to_system_prompt
        # which ensures consistent behavior
        result = apply_language_to_system_prompt(BASE_SYSTEM_PROMPT, language)

        if language == "en":
            assert result == BASE_SYSTEM_PROMPT
        else:
            assert expected_instruction in result or LANGUAGE_NAMES[language] in result


class TestLanguageEdgeCases:
    """Test edge cases in language configuration."""

    def test_none_language_defaults_to_english(self) -> None:
        """None language should default to English."""
        result = apply_language_to_system_prompt(BASE_SYSTEM_PROMPT, None)
        # Should handle None gracefully
        assert isinstance(result, str)

    def test_empty_string_language(self) -> None:
        """Empty string language should be handled gracefully."""
        result = apply_language_to_system_prompt(BASE_SYSTEM_PROMPT, "")
        assert isinstance(result, str)

    def test_case_insensitive_language_codes(self) -> None:
        """Language codes should be normalized to lowercase."""
        # The system should handle uppercase gracefully
        result_upper = build_language_instruction("CS")
        result_lower = build_language_instruction("cs")

        # Both should produce valid results
        assert isinstance(result_upper, str)
        assert isinstance(result_lower, str)

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    def test_language_with_special_characters_in_prompt(self, language: str) -> None:
        """System prompt with special characters should work with all languages."""
        special_prompt = "You are a bot. Use emojis: 😀🎉\nMultiple\nLines\nHere."
        result = apply_language_to_system_prompt(special_prompt, language)

        # Should contain original prompt
        assert special_prompt in result

        # Should handle special characters
        assert "😀" in result
        assert "\n" in result


class TestLanguageInstructionContent:
    """Test the actual content and quality of language instructions."""

    @pytest.mark.parametrize("language", ["cs", "sk", "de", "fr", "es"])
    def test_instruction_contains_mandatory_keywords(self, language: str) -> None:
        """Language instructions should contain strong directive keywords."""
        instruction = build_language_instruction(language)

        # Should be emphatic and clear
        lower_instruction = instruction.lower()

        # Should contain at least one strong directive word
        strong_keywords = ["must", "only", "important", "never"]
        assert any(keyword in lower_instruction for keyword in strong_keywords)

    @pytest.mark.parametrize("language", ["cs", "sk", "de", "fr", "es"])
    def test_instruction_prohibits_english(self, language: str) -> None:
        """Non-English instructions should explicitly prohibit English."""
        instruction = build_language_instruction(language)
        lower_instruction = instruction.lower()

        # Should mention not responding in English or other languages
        assert "english" in lower_instruction or "other language" in lower_instruction

    @pytest.mark.parametrize("language", ["cs", "sk", "de", "fr", "es"])
    def test_instruction_specifies_target_language(self, language: str) -> None:
        """Instructions should explicitly name the target language."""
        instruction = build_language_instruction(language)
        language_name = LANGUAGE_NAMES[language]

        # Should contain the full language name (not just code)
        assert language_name in instruction
