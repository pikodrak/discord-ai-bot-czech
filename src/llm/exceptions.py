"""
Custom exceptions for LLM client operations.
"""
from typing import Optional, Dict


class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    pass


class LLMProviderError(LLMError):
    """Exception raised when a specific LLM provider fails."""

    def __init__(self, provider: str, message: str, original_error: Optional[Exception] = None):
        """
        Initialize LLM provider error.

        Args:
            provider: Name of the LLM provider that failed
            message: Error message
            original_error: Original exception that caused this error
        """
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")


class LLMRateLimitError(LLMProviderError):
    """Exception raised when rate limit is exceeded."""

    pass


class LLMAuthenticationError(LLMProviderError):
    """Exception raised when authentication fails."""

    pass


class LLMAllProvidersFailedError(LLMError):
    """Exception raised when all LLM providers have failed."""

    def __init__(self, errors: Dict[str, Exception]):
        """
        Initialize all providers failed error.

        Args:
            errors: Dictionary mapping provider names to their errors
        """
        self.errors = errors
        error_summary = "; ".join([f"{provider}: {str(error)}" for provider, error in errors.items()])
        super().__init__(f"All LLM providers failed: {error_summary}")
