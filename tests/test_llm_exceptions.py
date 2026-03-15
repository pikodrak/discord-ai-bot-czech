"""
Comprehensive tests for LLM exception classes.

Tests all custom exception types including error context and formatting.
"""

import pytest
from src.llm.exceptions import (
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMAllProvidersFailedError,
)


class TestLLMError:
    """Test suite for base LLMError exception."""

    def test_base_exception(self):
        """Test that LLMError is a base exception."""
        error = LLMError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_inheritance(self):
        """Test that LLMError inherits from Exception."""
        assert issubclass(LLMError, Exception)

    def test_raise_and_catch(self):
        """Test raising and catching LLMError."""
        with pytest.raises(LLMError) as exc_info:
            raise LLMError("Test error")
        
        assert "Test error" in str(exc_info.value)


class TestLLMProviderError:
    """Test suite for LLMProviderError exception."""

    def test_initialization(self):
        """Test LLMProviderError initialization."""
        error = LLMProviderError("claude", "API call failed")
        assert error.provider == "claude"
        assert error.original_error is None
        assert "[claude]" in str(error)
        assert "API call failed" in str(error)

    def test_initialization_with_original_error(self):
        """Test LLMProviderError with original error."""
        original = ValueError("Invalid parameter")
        error = LLMProviderError("gemini", "Request failed", original)
        
        assert error.provider == "gemini"
        assert error.original_error is original
        assert isinstance(error.original_error, ValueError)

    def test_inheritance(self):
        """Test that LLMProviderError inherits from LLMError."""
        error = LLMProviderError("openai", "Test")
        assert isinstance(error, LLMError)
        assert isinstance(error, Exception)

    def test_error_message_format(self):
        """Test error message formatting."""
        error = LLMProviderError("claude", "Connection timeout")
        error_str = str(error)
        
        assert error_str.startswith("[claude]")
        assert "Connection timeout" in error_str

    def test_multiple_providers(self):
        """Test errors from different providers."""
        claude_error = LLMProviderError("claude", "Error 1")
        gemini_error = LLMProviderError("gemini", "Error 2")
        openai_error = LLMProviderError("openai", "Error 3")
        
        assert "claude" in str(claude_error)
        assert "gemini" in str(gemini_error)
        assert "openai" in str(openai_error)


class TestLLMRateLimitError:
    """Test suite for LLMRateLimitError exception."""

    def test_initialization(self):
        """Test LLMRateLimitError initialization."""
        error = LLMRateLimitError("claude", "Rate limit exceeded")
        assert error.provider == "claude"
        assert "Rate limit exceeded" in str(error)

    def test_inheritance(self):
        """Test that LLMRateLimitError inherits from LLMProviderError."""
        error = LLMRateLimitError("openai", "Too many requests")
        assert isinstance(error, LLMProviderError)
        assert isinstance(error, LLMError)
        assert isinstance(error, Exception)

    def test_with_original_error(self):
        """Test LLMRateLimitError with original error."""
        original = Exception("429 Too Many Requests")
        error = LLMRateLimitError("gemini", "Quota exceeded", original)
        
        assert error.original_error is original


class TestLLMAuthenticationError:
    """Test suite for LLMAuthenticationError exception."""

    def test_initialization(self):
        """Test LLMAuthenticationError initialization."""
        error = LLMAuthenticationError("claude", "Invalid API key")
        assert error.provider == "claude"
        assert "Invalid API key" in str(error)

    def test_inheritance(self):
        """Test that LLMAuthenticationError inherits from LLMProviderError."""
        error = LLMAuthenticationError("openai", "Unauthorized")
        assert isinstance(error, LLMProviderError)
        assert isinstance(error, LLMError)
        assert isinstance(error, Exception)

    def test_with_original_error(self):
        """Test LLMAuthenticationError with original error."""
        original = Exception("401 Unauthorized")
        error = LLMAuthenticationError("gemini", "Auth failed", original)
        
        assert error.original_error is original


class TestLLMAllProvidersFailedError:
    """Test suite for LLMAllProvidersFailedError exception."""

    def test_initialization(self):
        """Test LLMAllProvidersFailedError initialization."""
        errors = {
            "claude": Exception("Claude error"),
            "gemini": Exception("Gemini error"),
            "openai": Exception("OpenAI error"),
        }
        error = LLMAllProvidersFailedError(errors)
        
        assert error.errors == errors
        assert "All LLM providers failed" in str(error)

    def test_inheritance(self):
        """Test that LLMAllProvidersFailedError inherits from LLMError."""
        errors = {"claude": Exception("Test")}
        error = LLMAllProvidersFailedError(errors)
        
        assert isinstance(error, LLMError)
        assert isinstance(error, Exception)

    def test_error_summary(self):
        """Test that error summary includes all providers."""
        errors = {
            "claude": Exception("Error 1"),
            "gemini": Exception("Error 2"),
        }
        error = LLMAllProvidersFailedError(errors)
        error_str = str(error)
        
        assert "claude" in error_str
        assert "gemini" in error_str
        assert "Error 1" in error_str
        assert "Error 2" in error_str

    def test_empty_errors_dict(self):
        """Test with empty errors dictionary."""
        errors = {}
        error = LLMAllProvidersFailedError(errors)
        assert error.errors == {}

    def test_single_provider_error(self):
        """Test with single provider error."""
        errors = {"claude": ValueError("Invalid parameter")}
        error = LLMAllProvidersFailedError(errors)
        
        assert len(error.errors) == 1
        assert "claude" in str(error)
        assert "Invalid parameter" in str(error)

    def test_preserves_error_types(self):
        """Test that original error types are preserved."""
        errors = {
            "claude": LLMRateLimitError("claude", "Rate limit"),
            "openai": LLMAuthenticationError("openai", "Auth failed"),
        }
        error = LLMAllProvidersFailedError(errors)
        
        assert isinstance(error.errors["claude"], LLMRateLimitError)
        assert isinstance(error.errors["openai"], LLMAuthenticationError)


class TestExceptionHierarchy:
    """Test suite for exception hierarchy and relationships."""

    def test_catch_base_exception(self):
        """Test catching all LLM errors with base exception."""
        # All LLM exceptions should be catchable with LLMError
        exceptions_to_test = [
            LLMError("Test"),
            LLMProviderError("claude", "Test"),
            LLMRateLimitError("claude", "Test"),
            LLMAuthenticationError("claude", "Test"),
            LLMAllProvidersFailedError({"claude": Exception("Test")}),
        ]
        
        for exc in exceptions_to_test:
            assert isinstance(exc, LLMError)

    def test_catch_provider_error(self):
        """Test catching provider-specific errors."""
        # Both rate limit and auth errors are provider errors
        rate_limit = LLMRateLimitError("claude", "Test")
        auth_error = LLMAuthenticationError("claude", "Test")
        
        assert isinstance(rate_limit, LLMProviderError)
        assert isinstance(auth_error, LLMProviderError)

    def test_exception_specificity(self):
        """Test that specific exceptions can be caught separately."""
        with pytest.raises(LLMRateLimitError):
            raise LLMRateLimitError("claude", "Rate limit")
        
        with pytest.raises(LLMAuthenticationError):
            raise LLMAuthenticationError("claude", "Auth failed")
        
        with pytest.raises(LLMAllProvidersFailedError):
            raise LLMAllProvidersFailedError({"claude": Exception("Test")})
