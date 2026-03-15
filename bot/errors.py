"""
Comprehensive Error Handling Module

This module provides custom exception classes and error handling utilities
for the Discord AI bot, including:
- Custom exception hierarchy
- Error context and tracking
- User-friendly error messages
- Error recovery strategies
"""

import logging
import traceback
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"  # Minor issues, can continue operation
    MEDIUM = "medium"  # Significant issues, degraded functionality
    HIGH = "high"  # Critical issues, major feature unavailable
    CRITICAL = "critical"  # Fatal issues, bot cannot operate


class ErrorCategory(str, Enum):
    """Error categories for classification."""

    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    API = "api"
    NETWORK = "network"
    DATABASE = "database"
    DISCORD = "discord"
    LLM = "llm"
    VALIDATION = "validation"
    INTERNAL = "internal"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"


# Base Exceptions


class BotError(Exception):
    """
    Base exception for all bot-related errors.

    Provides error context, severity, and user-friendly messages.
    """

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize bot error.

        Args:
            message: Technical error message for logging
            severity: Error severity level
            category: Error category
            user_message: User-friendly error message (optional)
            details: Additional error context
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.user_message = user_message or self._generate_user_message()
        self.details = details or {}
        self.original_error = original_error

    def _generate_user_message(self) -> str:
        """Generate user-friendly error message."""
        return "Omlouváme se, došlo k neočekávané chybě. Zkuste to prosím později."

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary.

        Returns:
            Error information as dictionary
        """
        return {
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "details": self.details,
            "original_error": (
                str(self.original_error) if self.original_error else None
            ),
        }

    def log(self) -> None:
        """Log error with appropriate level based on severity."""
        log_methods = {
            ErrorSeverity.LOW: logger.warning,
            ErrorSeverity.MEDIUM: logger.error,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.CRITICAL: logger.critical,
        }

        log_method = log_methods[self.severity]
        log_method(
            f"[{self.category.value}] {self.message}",
            exc_info=self.original_error,
            extra={"details": self.details},
        )


# Configuration Errors


class ConfigurationError(BotError):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self, message: str, details: Optional[Dict[str, Any]] = None, **kwargs
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CONFIGURATION,
            user_message="Chyba konfigurace bota. Kontaktujte administrátora.",
            details=details,
            **kwargs,
        )


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""

    def __init__(self, config_key: str, **kwargs):
        super().__init__(
            message=f"Missing required configuration: {config_key}",
            details={"config_key": config_key},
            **kwargs,
        )


# Discord Errors


class DiscordError(BotError):
    """Base class for Discord-related errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.DISCORD)
        kwargs.setdefault("user_message", "Problém s připojením k Discordu.")
        super().__init__(message=message, **kwargs)


class DiscordConnectionError(DiscordError):
    """Raised when Discord connection fails."""

    def __init__(self, message: str = "Discord connection failed", **kwargs):
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            user_message="Nelze se připojit k Discordu. Zkouším znovu...",
            **kwargs,
        )


class DiscordAuthenticationError(DiscordError):
    """Raised when Discord authentication fails."""

    def __init__(self, message: str = "Discord authentication failed", **kwargs):
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            user_message="Chyba ověření Discord tokenu. Kontaktujte administrátora.",
            **kwargs,
        )


class DiscordRateLimitError(DiscordError):
    """Raised when Discord rate limit is hit."""

    def __init__(self, retry_after: Optional[float] = None, **kwargs):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=f"Discord rate limit hit (retry after {retry_after}s)",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.RATE_LIMIT,
            user_message="Přílišná zátěž. Zkuste to za chvíli.",
            details=details,
            **kwargs,
        )


# LLM Errors


class LLMError(BotError):
    """Base class for LLM-related errors."""

    def __init__(self, message: str, provider: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if provider:
            details["provider"] = provider

        kwargs.setdefault("category", ErrorCategory.LLM)
        kwargs.setdefault(
            "user_message", "Momentálně nemohu odpovědět. Zkuste to prosím později."
        )
        super().__init__(message=message, details=details, **kwargs)


class LLMProviderUnavailableError(LLMError):
    """Raised when an LLM provider is unavailable."""

    def __init__(self, provider: str, **kwargs):
        super().__init__(
            message=f"LLM provider unavailable: {provider}",
            provider=provider,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class LLMAllProvidersUnavailableError(LLMError):
    """Raised when all LLM providers are unavailable."""

    def __init__(self, provider_errors: Optional[Dict[str, Exception]] = None, **kwargs):
        details = {"provider_errors": provider_errors} if provider_errors else {}
        super().__init__(
            message="All LLM providers unavailable",
            severity=ErrorSeverity.HIGH,
            user_message="AI služby jsou momentálně nedostupné. Zkuste to prosím později.",
            details=details,
            **kwargs,
        )


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    def __init__(self, provider: str, timeout: float, **kwargs):
        super().__init__(
            message=f"LLM request timeout after {timeout}s",
            provider=provider,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.TIMEOUT,
            user_message="Generování odpovědi trvá déle než obvykle. Zkuste to prosím znovu.",
            details={"timeout": timeout},
            **kwargs,
        )


# Network Errors


class NetworkError(BotError):
    """Base class for network-related errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.NETWORK)
        kwargs.setdefault("user_message", "Problém se síťovým připojením.")
        super().__init__(message=message, **kwargs)


class ConnectionTimeoutError(NetworkError):
    """Raised when network connection times out."""

    def __init__(self, url: Optional[str] = None, timeout: Optional[float] = None, **kwargs):
        details = {}
        if url:
            details["url"] = url
        if timeout:
            details["timeout"] = timeout

        super().__init__(
            message=f"Connection timeout: {url or 'unknown'}",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.TIMEOUT,
            details=details,
            **kwargs,
        )


# Database Errors


class DatabaseError(BotError):
    """Base class for database-related errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.DATABASE)
        kwargs.setdefault("user_message", "Problém s databází.")
        super().__init__(message=message, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Database connection failed",
            severity=ErrorSeverity.HIGH,
            user_message="Nelze se připojit k databázi. Některé funkce mohou být omezeny.",
            **kwargs,
        )


# Validation Errors


class ValidationError(BotError):
    """Raised when data validation fails."""

    def __init__(
        self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            user_message="Neplatná data.",
            details=details,
            **kwargs,
        )


# Error Handler Utility


class ErrorHandler:
    """
    Centralized error handling utility.

    Provides methods for handling, logging, and recovering from errors.
    """

    def __init__(self, enable_graceful_degradation: bool = True):
        """
        Initialize error handler.

        Args:
            enable_graceful_degradation: Enable graceful degradation on errors
        """
        self.enable_graceful_degradation = enable_graceful_degradation
        self._error_counts: Dict[str, int] = {}

    def handle_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> BotError:
        """
        Handle an error and convert to BotError.

        Args:
            error: Exception to handle
            context: Additional error context

        Returns:
            BotError instance
        """
        # If already a BotError, just log and return
        if isinstance(error, BotError):
            error.log()
            self._track_error(error)
            return error

        # Convert to BotError
        bot_error = self._convert_to_bot_error(error, context)
        bot_error.log()
        self._track_error(bot_error)

        return bot_error

    def _convert_to_bot_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> BotError:
        """
        Convert generic exception to BotError.

        Args:
            error: Exception to convert
            context: Error context

        Returns:
            BotError instance
        """
        error_type = type(error).__name__

        # Map common exceptions to BotError types
        if "timeout" in error_type.lower():
            return ConnectionTimeoutError(
                url=context.get("url") if context else None,
                original_error=error,
                details=context,
            )

        if "connection" in error_type.lower():
            return NetworkError(
                message=str(error), original_error=error, details=context
            )

        # Generic error
        return BotError(
            message=f"Unexpected error: {str(error)}",
            severity=ErrorSeverity.MEDIUM,
            original_error=error,
            details=context or {},
        )

    def _track_error(self, error: BotError) -> None:
        """
        Track error occurrence.

        Args:
            error: Error to track
        """
        error_key = f"{error.category.value}:{type(error).__name__}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

    def get_error_stats(self) -> Dict[str, int]:
        """
        Get error statistics.

        Returns:
            Dictionary of error counts by type
        """
        return self._error_counts.copy()

    def should_retry(self, error: BotError, attempt: int, max_attempts: int) -> bool:
        """
        Determine if operation should be retried.

        Args:
            error: Error that occurred
            attempt: Current attempt number
            max_attempts: Maximum retry attempts

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= max_attempts:
            return False

        # Don't retry critical errors
        if error.severity == ErrorSeverity.CRITICAL:
            return False

        # Don't retry authentication errors
        if error.category == ErrorCategory.AUTHENTICATION:
            return False

        # Don't retry validation errors
        if error.category == ErrorCategory.VALIDATION:
            return False

        return True


# Global error handler instance
error_handler = ErrorHandler()
