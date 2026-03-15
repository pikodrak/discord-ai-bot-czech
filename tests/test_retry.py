"""
Comprehensive tests for consolidated retry module with exponential backoff.
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

# Import from consolidated retry module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from retry_strategy import (
    RetryConfig,
    RetryHandler,
    RetryStrategy,
    create_retry_handler,
)
from exceptions import (
    RetryableError,
    NonRetryableError,
    RateLimitError,
    TimeoutError as BotTimeoutError,
)


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.jitter_range == 0.1
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert Exception in config.retryable_exceptions

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config should not raise
        config = RetryConfig()
        config.validate()

        # Invalid max_attempts
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            config = RetryConfig(max_attempts=0)
            config.validate()

        # Invalid base_delay (negative)
        with pytest.raises(ValueError, match="base_delay must be non-negative"):
            config = RetryConfig(base_delay=-1.0)
            config.validate()

        # Invalid max_delay
        with pytest.raises(ValueError, match="max_delay must be >= base_delay"):
            config = RetryConfig(base_delay=10.0, max_delay=5.0)
            config.validate()


class TestRetryHandler:
    """Test RetryHandler class."""

    @pytest.mark.asyncio
    async def test_successful_operation_no_retry(self):
        """Test that successful operation doesn't retry."""
        call_count = 0

        async def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        handler = RetryHandler(RetryConfig(max_attempts=3))
        result = await handler.execute_with_retry(successful_operation)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_retryable_error(self):
        """Test retry behavior on retryable errors."""
        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("Temporary failure")
            return "success"

        handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        )
        result = await handler.execute_with_retry(
            failing_operation,
            retry_on=(RetryableError,)
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """Test that non-retryable errors don't trigger retry."""
        call_count = 0

        async def fatal_operation():
            nonlocal call_count
            call_count += 1
            raise NonRetryableError("Fatal error")

        handler = RetryHandler(RetryConfig(max_attempts=3))

        with pytest.raises(NonRetryableError):
            await handler.execute_with_retry(
                fatal_operation,
                do_not_retry_on=(NonRetryableError,)
            )

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_attempts_exhausted(self):
        """Test behavior when all retry attempts are exhausted."""
        call_count = 0

        async def always_failing():
            nonlocal call_count
            call_count += 1
            raise RetryableError("Always fails")

        handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        )

        with pytest.raises(RetryableError):
            await handler.execute_with_retry(
                always_failing,
                retry_on=(RetryableError,)
            )

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_rate_limit(self):
        """Test retry with rate limit error."""
        call_count = 0

        async def rate_limited_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("Rate limited", retry_after=0.01)
            return "success"

        handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        )
        result = await handler.execute_with_retry(
            rate_limited_operation,
            retry_on=(RateLimitError,)
        )

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        """Test that on_retry callback is called."""
        callback_calls = []

        def on_retry_callback(error, attempt):
            callback_calls.append((error, attempt))

        async def failing_operation():
            if len(callback_calls) < 2:
                raise RetryableError("Fail")
            return "success"

        handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        )
        result = await handler.execute_with_retry(
            failing_operation,
            retry_on=(RetryableError,),
            on_retry=on_retry_callback
        )

        assert result == "success"
        assert len(callback_calls) == 2
        assert callback_calls[0][1] == 0  # First retry, attempt 0
        assert callback_calls[1][1] == 1  # Second retry, attempt 1


class TestRetryStrategies:
    """Test different retry strategies."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_strategy(self):
        """Test exponential backoff strategy."""
        handler = RetryHandler(
            RetryConfig(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=0.01,
                exponential_base=2.0,
                jitter=False
            )
        )

        # Test delay calculations
        assert handler._calculate_delay(0) == 0.01
        assert handler._calculate_delay(1) == 0.02
        assert handler._calculate_delay(2) == 0.04

    @pytest.mark.asyncio
    async def test_linear_backoff_strategy(self):
        """Test linear backoff strategy."""
        handler = RetryHandler(
            RetryConfig(
                strategy=RetryStrategy.LINEAR_BACKOFF,
                base_delay=0.01,
                jitter=False
            )
        )

        # Test delay calculations
        assert handler._calculate_delay(0) == 0.01
        assert handler._calculate_delay(1) == 0.02
        assert handler._calculate_delay(2) == 0.03

    @pytest.mark.asyncio
    async def test_fibonacci_backoff_strategy(self):
        """Test Fibonacci backoff strategy."""
        handler = RetryHandler(
            RetryConfig(
                strategy=RetryStrategy.FIBONACCI_BACKOFF,
                base_delay=0.01,
                jitter=False
            )
        )

        # Test delay calculations (uses fib(attempt+2): fib(2)=1, fib(3)=2, fib(4)=3, fib(5)=5)
        assert handler._calculate_delay(0) == 0.01  # fib(2) = 1 * 0.01
        assert handler._calculate_delay(1) == 0.02  # fib(3) = 2 * 0.01
        assert handler._calculate_delay(2) == 0.03  # fib(4) = 3 * 0.01
        assert handler._calculate_delay(3) == 0.05  # fib(5) = 5 * 0.01

    @pytest.mark.asyncio
    async def test_fixed_delay_strategy(self):
        """Test fixed delay strategy."""
        handler = RetryHandler(
            RetryConfig(
                strategy=RetryStrategy.FIXED_DELAY,
                base_delay=0.01,
                jitter=False
            )
        )

        # All delays should be the same
        assert handler._calculate_delay(0) == 0.01
        assert handler._calculate_delay(1) == 0.01
        assert handler._calculate_delay(5) == 0.01


class TestRetryWithArgs:
    """Test retry with function arguments."""

    @pytest.mark.asyncio
    async def test_retry_with_positional_args(self):
        """Test retry with positional arguments."""
        call_count = 0

        async def operation_with_args(x, y):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RetryableError("Fail once")
            return x + y

        handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        )
        result = await handler.execute_with_retry(
            operation_with_args,
            5, 10,
            retry_on=(RetryableError,)
        )

        assert result == 15
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_keyword_args(self):
        """Test retry with keyword arguments."""
        call_count = 0

        async def operation_with_kwargs(name, value):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RetryableError("Fail once")
            return f"{name}={value}"

        handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        )
        result = await handler.execute_with_retry(
            operation_with_kwargs,
            name="test",
            value=42,
            retry_on=(RetryableError,)
        )

        assert result == "test=42"
        assert call_count == 2


class TestRetryTiming:
    """Test retry timing and delays."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff timing is correct."""
        call_times = []

        async def timed_operation():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise RetryableError("Fail")
            return "success"

        handler = RetryHandler(
            RetryConfig(
                max_attempts=3,
                base_delay=0.1,
                exponential_base=2.0,
                jitter=False
            )
        )
        await handler.execute_with_retry(
            timed_operation,
            retry_on=(RetryableError,)
        )

        assert len(call_times) == 3

        # Check delays between calls
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # First delay should be ~0.1s, second ~0.2s
        assert 0.08 <= delay1 <= 0.15
        assert 0.18 <= delay2 <= 0.25

    @pytest.mark.asyncio
    async def test_jitter_timing(self):
        """Test that jitter adds randomness to delays."""
        handler = RetryHandler(
            RetryConfig(
                base_delay=0.1,
                jitter=True,
                jitter_range=0.1
            )
        )

        delays = [handler._calculate_delay(0) for _ in range(10)]

        # All delays should be within jitter range
        for delay in delays:
            assert 0.09 <= delay <= 0.11

        # At least some variation
        assert len(set(delays)) > 1


class TestRetryEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_callback_exception_doesnt_break_retry(self):
        """Test that exceptions in callback don't break retry logic."""
        call_count = 0

        def bad_callback(error, attempt):
            raise ValueError("Callback error")

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RetryableError("Fail")
            return "success"

        handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        )

        # Should still succeed despite callback error
        result = await handler.execute_with_retry(
            operation,
            retry_on=(RetryableError,),
            on_retry=bad_callback
        )
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_zero_delay_retry(self):
        """Test retry with zero base delay."""
        call_count = 0

        async def instant_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("Fail")
            return "success"

        handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=0.0, jitter=False)
        )
        result = await handler.execute_with_retry(
            instant_retry,
            retry_on=(RetryableError,)
        )
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_custom_retryable_exceptions(self):
        """Test retry with custom exception types."""

        class CustomError(Exception):
            pass

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise CustomError("test")
            return "success"

        handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        )

        # Should retry CustomError
        result = await handler.execute_with_retry(
            operation,
            retry_on=(CustomError,)
        )
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that delays are capped at max_delay."""
        handler = RetryHandler(
            RetryConfig(
                base_delay=10.0,
                max_delay=15.0,
                exponential_base=2.0,
                jitter=False
            )
        )

        # Large attempt number should still be capped
        delay = handler._calculate_delay(10)
        assert delay == 15.0

    @pytest.mark.asyncio
    async def test_create_retry_handler_helper(self):
        """Test the create_retry_handler convenience function."""
        handler = create_retry_handler(
            max_attempts=5,
            base_delay=2.0,
            max_delay=30.0,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            jitter=False
        )

        assert handler.config.max_attempts == 5
        assert handler.config.base_delay == 2.0
        assert handler.config.max_delay == 30.0
        assert handler.config.strategy == RetryStrategy.LINEAR_BACKOFF
        assert handler.config.jitter is False
