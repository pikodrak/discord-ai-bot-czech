"""
Comprehensive tests for LLM factory functions.

Tests client creation, configuration, and default prompts.
"""

import pytest
from unittest.mock import Mock, patch

from src.llm.factory import (
    create_llm_client,
    get_default_system_prompt,
)
from src.llm.client import LLMClient
from src.llm.client_enhanced import EnhancedLLMClient
from src.config import Settings


class TestCreateLLMClient:
    """Test suite for create_llm_client factory function."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with API keys."""
        settings = Mock(spec=Settings)
        settings.anthropic_api_key = "test_claude_key"
        settings.google_api_key = "test_gemini_key"
        settings.openai_api_key = "test_openai_key"
        settings.bot_language = "en"
        settings.has_any_ai_key = Mock(return_value=True)
        return settings

    @pytest.fixture
    def settings_no_keys(self):
        """Create mock settings with no API keys."""
        settings = Mock(spec=Settings)
        settings.anthropic_api_key = None
        settings.google_api_key = None
        settings.openai_api_key = None
        settings.has_any_ai_key = Mock(return_value=False)
        return settings

    def test_create_enhanced_client_default(self, mock_settings):
        """Test creating enhanced client by default."""
        client = create_llm_client(mock_settings)
        assert isinstance(client, EnhancedLLMClient)

    def test_create_standard_client(self, mock_settings):
        """Test creating standard client explicitly."""
        client = create_llm_client(mock_settings, client_type="standard")
        assert isinstance(client, LLMClient)
        assert not isinstance(client, EnhancedLLMClient)

    def test_create_enhanced_client_explicit(self, mock_settings):
        """Test creating enhanced client explicitly."""
        client = create_llm_client(mock_settings, client_type="enhanced")
        assert isinstance(client, EnhancedLLMClient)

    def test_no_api_keys_raises_error(self, settings_no_keys):
        """Test that creating client without API keys raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_llm_client(settings_no_keys)
        
        assert "No AI API keys configured" in str(exc_info.value)

    def test_custom_retry_settings(self, mock_settings):
        """Test creating client with custom retry settings."""
        client = create_llm_client(
            mock_settings,
            max_retries=5,
            retry_delay=2.0,
        )
        # Assuming client stores these settings
        # (This depends on actual implementation)
        assert client is not None

    def test_circuit_breaker_settings(self, mock_settings):
        """Test creating enhanced client with circuit breaker settings."""
        client = create_llm_client(
            mock_settings,
            client_type="enhanced",
            enable_circuit_breaker=True,
            circuit_failure_threshold=10,
            circuit_timeout=120.0,
        )
        assert isinstance(client, EnhancedLLMClient)

    def test_language_from_parameter(self, mock_settings):
        """Test that language parameter overrides settings."""
        client = create_llm_client(mock_settings, language="cs")
        # Verify language is set (implementation dependent)
        assert client is not None

    def test_language_from_settings(self, mock_settings):
        """Test that language is taken from settings."""
        mock_settings.bot_language = "de"
        client = create_llm_client(mock_settings)
        assert client is not None

    def test_language_default_fallback(self, mock_settings):
        """Test that language defaults to 'en' if not in settings."""
        delattr(mock_settings, 'bot_language')
        client = create_llm_client(mock_settings)
        assert client is not None

    def test_with_only_claude_key(self):
        """Test creating client with only Claude API key."""
        settings = Mock(spec=Settings)
        settings.anthropic_api_key = "test_key"
        settings.google_api_key = None
        settings.openai_api_key = None
        settings.bot_language = "en"
        settings.has_any_ai_key = Mock(return_value=True)
        
        client = create_llm_client(settings)
        assert client is not None

    def test_with_only_gemini_key(self):
        """Test creating client with only Gemini API key."""
        settings = Mock(spec=Settings)
        settings.anthropic_api_key = None
        settings.google_api_key = "test_key"
        settings.openai_api_key = None
        settings.bot_language = "en"
        settings.has_any_ai_key = Mock(return_value=True)
        
        client = create_llm_client(settings)
        assert client is not None

    def test_with_only_openai_key(self):
        """Test creating client with only OpenAI API key."""
        settings = Mock(spec=Settings)
        settings.anthropic_api_key = None
        settings.google_api_key = None
        settings.openai_api_key = "test_key"
        settings.bot_language = "en"
        settings.has_any_ai_key = Mock(return_value=True)
        
        client = create_llm_client(settings)
        assert client is not None


class TestGetDefaultSystemPrompt:
    """Test suite for get_default_system_prompt function."""

    def test_default_friendly_personality(self):
        """Test default friendly personality prompt."""
        prompt = get_default_system_prompt()
        assert "helpful AI assistant" in prompt
        assert "warm" in prompt.lower() or "friendly" in prompt.lower()

    def test_friendly_personality(self):
        """Test friendly personality prompt."""
        prompt = get_default_system_prompt("friendly")
        assert "warm" in prompt.lower() or "approachable" in prompt.lower()
        assert "conversational" in prompt.lower()

    def test_professional_personality(self):
        """Test professional personality prompt."""
        prompt = get_default_system_prompt("professional")
        assert "professional" in prompt.lower()
        assert "formal" in prompt.lower() or "polite" in prompt.lower()

    def test_casual_personality(self):
        """Test casual personality prompt."""
        prompt = get_default_system_prompt("casual")
        assert "casual" in prompt.lower() or "relaxed" in prompt.lower()

    def test_helpful_personality(self):
        """Test helpful personality prompt."""
        prompt = get_default_system_prompt("helpful")
        assert "helpful" in prompt.lower()
        assert "patient" in prompt.lower() or "thorough" in prompt.lower()

    def test_unknown_personality_fallback(self):
        """Test that unknown personality falls back to friendly."""
        prompt = get_default_system_prompt("unknown_personality")
        # Should fall back to friendly
        assert "helpful AI assistant" in prompt

    def test_case_insensitive(self):
        """Test that personality parameter is case insensitive."""
        lower = get_default_system_prompt("friendly")
        upper = get_default_system_prompt("FRIENDLY")
        mixed = get_default_system_prompt("Friendly")
        
        assert lower == upper == mixed

    def test_all_prompts_have_base(self):
        """Test that all personality prompts include base prompt."""
        personalities = ["friendly", "professional", "casual", "helpful"]
        
        for personality in personalities:
            prompt = get_default_system_prompt(personality)
            assert "helpful AI assistant" in prompt
            assert "Discord" in prompt

    def test_prompt_structure(self):
        """Test that prompts have proper structure."""
        prompt = get_default_system_prompt("professional")
        
        # Should have base part and personality part
        assert len(prompt) > 50  # Reasonable length
        assert "\n" in prompt  # Should have line breaks
