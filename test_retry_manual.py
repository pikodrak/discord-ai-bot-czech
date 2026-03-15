#!/usr/bin/env python3
"""
Manual test to verify retry consolidation works correctly.

Tests:
1. RetryHandler with different strategies
2. Client enhanced with retry logic
3. Error handling and callbacks
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from retry_strategy import (
    RetryConfig,
    RetryHandler,
    RetryStrategy,
)
from exceptions import RetryableError, NonRetryableError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_basic_retry():
    """Test basic retry functionality."""
    print("\n=== Test 1: Basic Retry ===")

    call_count = 0

    async def failing_operation():
        nonlocal call_count
        call_count += 1
        logger.info(f"Attempt {call_count}")
        if call_count < 3:
            raise RetryableError(f"Temporary failure {call_count}")
        return "Success!"

    handler = RetryHandler(
        RetryConfig(
            max_attempts=5,
            base_delay=0.1,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=False
        )
    )

    result = await handler.execute_with_retry(
        failing_operation,
        retry_on=(RetryableError,)
    )

    print(f"✓ Result: {result}")
    print(f"✓ Total attempts: {call_count}")
    assert call_count == 3, f"Expected 3 attempts, got {call_count}"


async def test_retry_strategies():
    """Test different retry strategies."""
    print("\n=== Test 2: Retry Strategies ===")

    for strategy in [
        RetryStrategy.EXPONENTIAL_BACKOFF,
        RetryStrategy.LINEAR_BACKOFF,
        RetryStrategy.FIBONACCI_BACKOFF,
        RetryStrategy.FIXED_DELAY,
    ]:
        handler = RetryHandler(
            RetryConfig(
                max_attempts=3,
                base_delay=0.01,
                strategy=strategy,
                jitter=False
            )
        )

        delays = [handler._calculate_delay(i) for i in range(3)]
        print(f"  {strategy.value}: {delays}")


async def test_non_retryable_error():
    """Test that non-retryable errors stop immediately."""
    print("\n=== Test 3: Non-Retryable Error ===")

    call_count = 0

    async def fatal_operation():
        nonlocal call_count
        call_count += 1
        logger.info(f"Attempt {call_count}")
        raise NonRetryableError("Fatal error")

    handler = RetryHandler(
        RetryConfig(max_attempts=5, base_delay=0.1)
    )

    try:
        await handler.execute_with_retry(
            fatal_operation,
            do_not_retry_on=(NonRetryableError,)
        )
    except NonRetryableError:
        print(f"✓ Correctly stopped after {call_count} attempt(s)")
        assert call_count == 1, f"Expected 1 attempt, got {call_count}"


async def test_retry_callback():
    """Test retry callback functionality."""
    print("\n=== Test 4: Retry Callback ===")

    callback_count = 0
    call_count = 0

    def on_retry(error, attempt):
        nonlocal callback_count
        callback_count += 1
        print(f"  Callback: Retry {callback_count} at attempt {attempt}: {error}")

    async def failing_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RetryableError(f"Fail {call_count}")
        return "Success"

    handler = RetryHandler(
        RetryConfig(max_attempts=5, base_delay=0.05, jitter=False)
    )

    result = await handler.execute_with_retry(
        failing_operation,
        retry_on=(RetryableError,),
        on_retry=on_retry
    )

    print(f"✓ Result: {result}")
    print(f"✓ Callbacks: {callback_count}")
    assert callback_count == 2, f"Expected 2 callbacks, got {callback_count}"


async def test_max_attempts_exhausted():
    """Test behavior when all retries are exhausted."""
    print("\n=== Test 5: Max Attempts Exhausted ===")

    call_count = 0

    async def always_failing():
        nonlocal call_count
        call_count += 1
        logger.info(f"Attempt {call_count}")
        raise RetryableError("Always fails")

    handler = RetryHandler(
        RetryConfig(max_attempts=3, base_delay=0.05, jitter=False)
    )

    try:
        await handler.execute_with_retry(
            always_failing,
            retry_on=(RetryableError,)
        )
        assert False, "Should have raised RetryableError"
    except RetryableError:
        print(f"✓ Correctly exhausted all {call_count} attempts")
        assert call_count == 3, f"Expected 3 attempts, got {call_count}"


async def test_with_args():
    """Test retry with function arguments."""
    print("\n=== Test 6: Retry with Arguments ===")

    call_count = 0

    async def operation_with_args(x, y, multiplier=1):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RetryableError("Fail once")
        return (x + y) * multiplier

    handler = RetryHandler(
        RetryConfig(max_attempts=3, base_delay=0.05, jitter=False)
    )

    result = await handler.execute_with_retry(
        operation_with_args,
        5, 10,
        multiplier=2,
        retry_on=(RetryableError,)
    )

    print(f"✓ Result: {result}")
    assert result == 30, f"Expected 30, got {result}"


async def test_jitter():
    """Test jitter adds randomness."""
    print("\n=== Test 7: Jitter ===")

    handler = RetryHandler(
        RetryConfig(
            base_delay=1.0,
            jitter=True,
            jitter_range=0.1
        )
    )

    delays = [handler._calculate_delay(0) for _ in range(10)]

    print(f"  Delays with jitter: {[f'{d:.3f}' for d in delays]}")
    print(f"  Min: {min(delays):.3f}, Max: {max(delays):.3f}")

    # All delays should be within jitter range (1.0 ± 0.1)
    assert all(0.9 <= d <= 1.1 for d in delays), "Delays outside expected range"
    # Should have some variation
    assert len(set(delays)) > 1, "No variation in delays"
    print("✓ Jitter working correctly")


async def main():
    """Run all manual tests."""
    print("=" * 60)
    print("Retry Consolidation Manual Tests")
    print("=" * 60)

    tests = [
        test_basic_retry,
        test_retry_strategies,
        test_non_retryable_error,
        test_retry_callback,
        test_max_attempts_exhausted,
        test_with_args,
        test_jitter,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            failed += 1
            logger.error(f"Test {test.__name__} failed: {e}", exc_info=True)

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
