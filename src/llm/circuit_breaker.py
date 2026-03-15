"""
Circuit breaker pattern implementation for LLM provider health management.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 60.0
    half_open_timeout: float = 30.0
    expected_exception: type[Exception] = Exception

    def validate(self) -> None:
        """Validate configuration."""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be at least 1")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.half_open_timeout <= 0:
            raise ValueError("half_open_timeout must be positive")


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected
    - HALF_OPEN: Testing recovery, limited requests pass through

    The circuit breaker transitions:
    - CLOSED -> OPEN: After failure_threshold consecutive failures
    - OPEN -> HALF_OPEN: After timeout period
    - HALF_OPEN -> CLOSED: After success_threshold consecutive successes
    - HALF_OPEN -> OPEN: On any failure
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name of the circuit (for logging)
            config: Circuit breaker configuration
            on_state_change: Optional callback when state changes
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.config.validate()
        self.on_state_change = on_state_change
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self.stats.state

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the function

        Raises:
            CircuitBreakerError: If circuit is open
            Any exception raised by the function
        """
        async with self._lock:
            self.stats.total_calls += 1

            # Check if we should allow the call
            if not await self._should_allow_request():
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self.state.value}"
                )

        try:
            # Execute the function
            result = await func(*args, **kwargs)

            # Record success
            async with self._lock:
                await self._on_success()

            return result

        except self.config.expected_exception as e:
            # Record failure
            async with self._lock:
                await self._on_failure()

            raise

    async def _should_allow_request(self) -> bool:
        """
        Determine if a request should be allowed based on circuit state.

        Returns:
            True if request should be allowed, False otherwise
        """
        if self.stats.state == CircuitState.CLOSED:
            return True

        if self.stats.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if self.stats.last_failure_time:
                elapsed = time.time() - self.stats.last_failure_time
                if elapsed >= self.config.timeout:
                    await self._transition_to(CircuitState.HALF_OPEN)
                    return True
            return False

        # HALF_OPEN state
        # Check if half-open timeout has elapsed
        if self.stats.last_state_change:
            elapsed = time.time() - self.stats.last_state_change
            if elapsed >= self.config.half_open_timeout:
                # Reset to CLOSED if we've been half-open too long
                await self._transition_to(CircuitState.CLOSED)
        return True

    async def _on_success(self) -> None:
        """Handle successful call."""
        self.stats.total_successes += 1

        if self.stats.state == CircuitState.HALF_OPEN:
            self.stats.success_count += 1
            logger.debug(
                f"Circuit '{self.name}': Success in HALF_OPEN "
                f"({self.stats.success_count}/{self.config.success_threshold})"
            )

            if self.stats.success_count >= self.config.success_threshold:
                await self._transition_to(CircuitState.CLOSED)
        elif self.stats.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.stats.failure_count = 0

    async def _on_failure(self) -> None:
        """Handle failed call."""
        self.stats.total_failures += 1
        self.stats.last_failure_time = time.time()

        if self.stats.state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN triggers transition to OPEN
            logger.warning(
                f"Circuit '{self.name}': Failure in HALF_OPEN, reopening circuit"
            )
            await self._transition_to(CircuitState.OPEN)
        elif self.stats.state == CircuitState.CLOSED:
            self.stats.failure_count += 1
            logger.debug(
                f"Circuit '{self.name}': Failure count "
                f"({self.stats.failure_count}/{self.config.failure_threshold})"
            )

            if self.stats.failure_count >= self.config.failure_threshold:
                await self._transition_to(CircuitState.OPEN)

    async def _transition_to(self, new_state: CircuitState) -> None:
        """
        Transition to a new state.

        Args:
            new_state: New circuit state
        """
        old_state = self.stats.state

        if old_state == new_state:
            return

        logger.info(
            f"Circuit '{self.name}': State transition "
            f"{old_state.value} -> {new_state.value}"
        )

        self.stats.state = new_state
        self.stats.last_state_change = time.time()

        # Reset counters based on new state
        if new_state == CircuitState.CLOSED:
            self.stats.failure_count = 0
            self.stats.success_count = 0
        elif new_state == CircuitState.OPEN:
            self.stats.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.stats.failure_count = 0
            self.stats.success_count = 0

        # Call state change callback
        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    async def reset(self) -> None:
        """Reset circuit breaker to CLOSED state."""
        async with self._lock:
            logger.info(f"Circuit '{self.name}': Manual reset")
            await self._transition_to(CircuitState.CLOSED)

    def get_stats(self) -> dict[str, Any]:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_calls": self.stats.total_calls,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "success_rate": (
                self.stats.total_successes / self.stats.total_calls
                if self.stats.total_calls > 0 else 0.0
            ),
            "last_failure_time": self.stats.last_failure_time,
            "last_state_change": self.stats.last_state_change,
        }


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""

    def __init__(self):
        """Initialize circuit breaker manager."""
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker.

        Args:
            name: Circuit breaker name
            config: Configuration (only used for new breakers)
            on_state_change: State change callback

        Returns:
            CircuitBreaker instance
        """
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    config=config,
                    on_state_change=on_state_change
                )
                logger.info(f"Created circuit breaker '{name}'")
            return self._breakers[name]

    async def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all circuit breakers.

        Returns:
            Dictionary mapping names to stats
        """
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()
        logger.info("Reset all circuit breakers")
