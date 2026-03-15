"""
Advanced retry strategies with exponential backoff and jitter.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import Callable, TypeVar, Any, Optional, Tuple

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryStrategy(Enum):
    """Enumeration of available retry strategies."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"
    FIXED_DELAY = "fixed_delay"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_exceptions: Tuple[type, ...] = (Exception,)

    def validate(self) -> None:
        """Validate retry configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.exponential_base < 1:
            raise ValueError("exponential_base must be >= 1")
        if not 0 <= self.jitter_range <= 1:
            raise ValueError("jitter_range must be between 0 and 1")
        if not self.retryable_exceptions:
            raise ValueError("retryable_exceptions must not be empty")


class RetryHandler:
    """
    Advanced retry handler with multiple backoff strategies.

    Supports:
    - Exponential backoff with jitter
    - Linear backoff
    - Fibonacci backoff
    - Fixed delay
    - Configurable retry conditions
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry handler.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        self.config.validate()

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = self.config.base_delay * self._fibonacci(attempt + 1)
        else:  # FIXED_DELAY
            delay = self.config.base_delay

        # Cap at max delay
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)

        return delay

    @staticmethod
    def _fibonacci(n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    async def execute_with_retry(
        self,
        operation: Callable[..., Any],
        *args: Any,
        retryable_exceptions: Optional[Tuple[type, ...]] = None,
        retry_on: Optional[Tuple[type, ...]] = None,
        do_not_retry_on: Tuple[type, ...] = (),
        on_retry: Optional[Callable[[Exception, int], None]] = None,
        **kwargs: Any
    ) -> T:
        """
        Execute an operation with retry logic.

        Args:
            operation: Async function to execute
            *args: Positional arguments for operation
            retryable_exceptions: Tuple of exception types to retry on (preferred)
            retry_on: Alias for retryable_exceptions (deprecated, use retryable_exceptions)
            do_not_retry_on: Tuple of exception types to never retry
            on_retry: Optional callback called on each retry
            **kwargs: Keyword arguments for operation

        Returns:
            Result of the operation

        Raises:
            Last exception if all retries fail

        Note:
            If both retryable_exceptions and retry_on are provided, retryable_exceptions takes precedence.
            If neither is provided, uses the config's retryable_exceptions.
        """
        # Determine which exceptions to retry on
        # Priority: retryable_exceptions > retry_on > config.retryable_exceptions
        exceptions_to_retry = (
            retryable_exceptions
            if retryable_exceptions is not None
            else (retry_on if retry_on is not None else self.config.retryable_exceptions)
        )

        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_attempts):
            try:
                # Execute the operation
                result = await operation(*args, **kwargs)

                if attempt > 0:
                    logger.info(
                        f"Operation succeeded on attempt {attempt + 1}/{self.config.max_attempts}"
                    )

                return result

            except do_not_retry_on as e:
                # Don't retry these exceptions
                logger.error(f"Non-retryable error encountered: {type(e).__name__}: {e}")
                raise

            except exceptions_to_retry as e:
                last_exception = e

                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{self.config.max_attempts}): "
                    f"{type(e).__name__}: {e}"
                )

                # Call retry callback if provided
                if on_retry:
                    try:
                        on_retry(e, attempt)
                    except Exception as callback_error:
                        logger.error(
                            f"Error in retry callback: {callback_error}",
                            exc_info=True
                        )

                # Don't sleep after the last attempt
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)

            except Exception as e:
                # Unexpected exception - log and re-raise
                logger.error(f"Unexpected error during retry: {type(e).__name__}: {e}")
                raise

        # All retries exhausted
        logger.error(
            f"Operation failed after {self.config.max_attempts} attempts"
        )
        if last_exception:
            raise last_exception
        raise RuntimeError("Operation failed with no exception recorded")


def create_retry_handler(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    jitter: bool = True
) -> RetryHandler:
    """
    Create a retry handler with common configuration.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        strategy: Retry strategy to use
        jitter: Whether to add jitter to delays

    Returns:
        Configured RetryHandler instance
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=strategy,
        jitter=jitter
    )
    return RetryHandler(config)
