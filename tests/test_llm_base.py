"""
Comprehensive tests for LLM base classes and data structures.

Tests LLMMessage, LLMResponse, and LLMProvider base class.
"""

import pytest
from abc import ABC
from unittest.mock import AsyncMock, Mock

from src.llm.base import LLMMessage, LLMResponse, LLMProvider


class TestLLMMessage:
    """Test suite for LLMMessage dataclass."""

    def test_create_user_message(self):
        """Test creating a user message."""
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_create_assistant_message(self):
        """Test creating an assistant message."""
        msg = LLMMessage(role="assistant", content="Hi there")
        assert msg.role == "assistant"
        assert msg.content == "Hi there"

    def test_create_system_message(self):
        """Test creating a system message."""
        msg = LLMMessage(role="system", content="You are helpful")
        assert msg.role == "system"
        assert msg.content == "You are helpful"

    def test_empty_content(self):
        """Test message with empty content."""
        msg = LLMMessage(role="user", content="")
        assert msg.content == ""

    def test_multiline_content(self):
        """Test message with multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        msg = LLMMessage(role="user", content=content)
        assert msg.content == content
        assert "\n" in msg.content

    def test_equality(self):
        """Test message equality comparison."""
        msg1 = LLMMessage(role="user", content="Hello")
        msg2 = LLMMessage(role="user", content="Hello")
        msg3 = LLMMessage(role="user", content="Hi")
        
        assert msg1 == msg2
        assert msg1 != msg3


class TestLLMResponse:
    """Test suite for LLMResponse dataclass."""

    def test_create_basic_response(self):
        """Test creating a basic response."""
        response = LLMResponse(
            content="Response text",
            provider="claude",
            model="claude-3-5-sonnet-20241022"
        )
        assert response.content == "Response text"
        assert response.provider == "claude"
        assert response.model == "claude-3-5-sonnet-20241022"
        assert response.tokens_used is None
        assert response.metadata is None

    def test_create_response_with_tokens(self):
        """Test creating response with token count."""
        response = LLMResponse(
            content="Response",
            provider="openai",
            model="gpt-4o",
            tokens_used=150
        )
        assert response.tokens_used == 150

    def test_create_response_with_metadata(self):
        """Test creating response with metadata."""
        metadata = {
            "finish_reason": "stop",
            "prompt_tokens": 50,
            "completion_tokens": 100
        }
        response = LLMResponse(
            content="Response",
            provider="openai",
            model="gpt-4o",
            tokens_used=150,
            metadata=metadata
        )
        assert response.metadata == metadata
        assert response.metadata["finish_reason"] == "stop"

    def test_empty_content(self):
        """Test response with empty content."""
        response = LLMResponse(
            content="",
            provider="gemini",
            model="gemini-1.5-pro"
        )
        assert response.content == ""

    def test_metadata_optional(self):
        """Test that metadata is optional."""
        response = LLMResponse(
            content="Test",
            provider="claude",
            model="claude-3-5-sonnet-20241022"
        )
        assert response.metadata is None


class ConcreteLLMProvider(LLMProvider):
    """Concrete implementation of LLMProvider for testing."""

    def get_default_model(self) -> str:
        return "test-model"

    def get_provider_name(self) -> str:
        return "test-provider"

    async def generate_response(
        self,
        messages,
        system_prompt=None,
        temperature=0.7,
        max_tokens=2000,
    ):
        return LLMResponse(
            content="Test response",
            provider=self.get_provider_name(),
            model=self.model
        )

    async def is_available(self) -> bool:
        return True


class TestLLMProvider:
    """Test suite for LLMProvider base class."""

    def test_abstract_class(self):
        """Test that LLMProvider is abstract."""
        assert issubclass(LLMProvider, ABC)

    def test_initialization_with_defaults(self):
        """Test provider initialization with default values."""
        provider = ConcreteLLMProvider(api_key="test_key")
        assert provider.api_key == "test_key"
        assert provider.model == "test-model"  # Uses get_default_model()
        assert provider.language == "en"  # Default language

    def test_initialization_with_custom_model(self):
        """Test provider initialization with custom model."""
        provider = ConcreteLLMProvider(api_key="test_key", model="custom-model")
        assert provider.model == "custom-model"

    def test_initialization_with_language(self):
        """Test provider initialization with custom language."""
        provider = ConcreteLLMProvider(api_key="test_key", language="cs")
        assert provider.language == "cs"

    def test_abstract_methods_must_be_implemented(self):
        """Test that abstract methods must be implemented."""
        # This should raise TypeError if we try to instantiate
        # a class that doesn't implement all abstract methods
        class IncompleteProvider(LLMProvider):
            pass
        
        with pytest.raises(TypeError):
            IncompleteProvider(api_key="test")

    @pytest.mark.asyncio
    async def test_concrete_provider_methods(self):
        """Test that concrete provider implements all methods."""
        provider = ConcreteLLMProvider(api_key="test_key")
        
        # Test all required methods
        assert provider.get_default_model() == "test-model"
        assert provider.get_provider_name() == "test-provider"
        
        # Test generate_response
        messages = [LLMMessage(role="user", content="Test")]
        response = await provider.generate_response(messages)
        assert isinstance(response, LLMResponse)
        
        # Test is_available
        available = await provider.is_available()
        assert available is True
