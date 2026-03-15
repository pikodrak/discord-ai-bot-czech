"""
Graceful Degradation Module

This module provides graceful degradation strategies when APIs or services fail:
- Fallback mechanisms
- Cached responses
- Simplified functionality
- User-friendly degradation messages
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from bot.errors import (
    BotError,
    ErrorSeverity,
    LLMAllProvidersUnavailableError,
    LLMError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceStatus(str, Enum):
    """Service status levels."""

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    PARTIAL_OUTAGE = "partial_outage"
    MAJOR_OUTAGE = "major_outage"


class FallbackStrategy(str, Enum):
    """Fallback strategy types."""

    CACHE = "cache"  # Use cached response
    SIMPLIFIED = "simplified"  # Use simplified functionality
    SKIP = "skip"  # Skip the operation gracefully
    MANUAL = "manual"  # Manual fallback logic


class ServiceHealthTracker:
    """
    Tracks health status of various services.

    Monitors service availability and failure patterns to make
    intelligent degradation decisions.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_threshold: int = 2,
        check_window: int = 300,
    ):
        """
        Initialize service health tracker.

        Args:
            failure_threshold: Number of failures to mark service as degraded
            recovery_threshold: Number of successes to mark service as recovered
            check_window: Time window in seconds for health checks
        """
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        self.check_window = check_window

        self._service_statuses: Dict[str, ServiceStatus] = {}
        self._failure_counts: Dict[str, int] = {}
        self._success_counts: Dict[str, int] = {}
        self._last_check: Dict[str, datetime] = {}

    def record_failure(self, service_name: str) -> None:
        """
        Record a service failure.

        Args:
            service_name: Name of the service
        """
        self._reset_if_expired(service_name)

        self._failure_counts[service_name] = (
            self._failure_counts.get(service_name, 0) + 1
        )
        self._success_counts[service_name] = 0
        self._last_check[service_name] = datetime.now()

        # Update status
        failures = self._failure_counts[service_name]
        if failures >= self.failure_threshold:
            self._service_statuses[service_name] = ServiceStatus.MAJOR_OUTAGE
            logger.warning(f"Service {service_name} marked as MAJOR_OUTAGE")
        elif failures >= self.failure_threshold // 2:
            self._service_statuses[service_name] = ServiceStatus.DEGRADED
            logger.warning(f"Service {service_name} marked as DEGRADED")

    def record_success(self, service_name: str) -> None:
        """
        Record a service success.

        Args:
            service_name: Name of the service
        """
        self._reset_if_expired(service_name)

        self._success_counts[service_name] = (
            self._success_counts.get(service_name, 0) + 1
        )
        self._last_check[service_name] = datetime.now()

        # Update status
        successes = self._success_counts[service_name]
        if successes >= self.recovery_threshold:
            old_status = self._service_statuses.get(service_name)
            self._service_statuses[service_name] = ServiceStatus.OPERATIONAL
            self._failure_counts[service_name] = 0

            if old_status and old_status != ServiceStatus.OPERATIONAL:
                logger.info(f"Service {service_name} recovered to OPERATIONAL")

    def get_status(self, service_name: str) -> ServiceStatus:
        """
        Get current service status.

        Args:
            service_name: Name of the service

        Returns:
            Current service status
        """
        self._reset_if_expired(service_name)
        return self._service_statuses.get(service_name, ServiceStatus.OPERATIONAL)

    def is_healthy(self, service_name: str) -> bool:
        """
        Check if service is healthy.

        Args:
            service_name: Name of the service

        Returns:
            True if service is operational
        """
        status = self.get_status(service_name)
        return status == ServiceStatus.OPERATIONAL

    def _reset_if_expired(self, service_name: str) -> None:
        """Reset counters if check window expired."""
        last_check = self._last_check.get(service_name)
        if last_check:
            elapsed = (datetime.now() - last_check).total_seconds()
            if elapsed > self.check_window:
                self._failure_counts[service_name] = 0
                self._success_counts[service_name] = 0
                self._service_statuses[service_name] = ServiceStatus.OPERATIONAL

    def get_all_statuses(self) -> Dict[str, ServiceStatus]:
        """
        Get status of all tracked services.

        Returns:
            Dictionary mapping service names to statuses
        """
        return {
            name: self.get_status(name) for name in self._service_statuses.keys()
        }


class ResponseCache:
    """
    Simple in-memory response cache for fallback.

    Caches successful responses for use during service degradation.
    """

    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """
        Initialize response cache.

        Args:
            max_size: Maximum cache size
            ttl: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]

        self._cache[key] = {"value": value, "timestamp": datetime.now()}
        logger.debug(f"Cached response for key: {key}")

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache:
            return None

        cached = self._cache[key]
        age = (datetime.now() - cached["timestamp"]).total_seconds()

        if age > self.ttl:
            del self._cache[key]
            logger.debug(f"Cache expired for key: {key}")
            return None

        logger.debug(f"Cache hit for key: {key}")
        return cached["value"]

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        logger.info("Response cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {"size": len(self._cache), "max_size": self.max_size, "ttl": self.ttl}


class GracefulDegradation:
    """
    Manages graceful degradation for the bot.

    Provides fallback mechanisms when services fail, ensuring
    the bot continues to function with reduced capabilities.
    """

    def __init__(
        self,
        enable_caching: bool = True,
        health_tracker: Optional[ServiceHealthTracker] = None,
        response_cache: Optional[ResponseCache] = None,
    ):
        """
        Initialize graceful degradation manager.

        Args:
            enable_caching: Enable response caching
            health_tracker: Service health tracker instance
            response_cache: Response cache instance
        """
        self.enable_caching = enable_caching
        self.health_tracker = health_tracker or ServiceHealthTracker()
        self.response_cache = response_cache or ResponseCache()

        # Default fallback messages
        self.fallback_messages = {
            "llm_unavailable": [
                "Omlouváme se, AI služby jsou momentálně nedostupné.",
                "Bohužel momentálně nemohu generovat odpovědi.",
                "AI systém je dočasně nedostupný. Zkuste to prosím později.",
            ],
            "api_error": [
                "Došlo k problému s externím API.",
                "Služba je momentálně nedostupná.",
            ],
            "timeout": [
                "Operace trvala příliš dlouho. Zkuste to prosím znovu.",
                "Vypršel časový limit požadavku.",
            ],
        }

    async def with_fallback(
        self,
        service_name: str,
        operation: Callable[..., T],
        fallback_strategy: FallbackStrategy = FallbackStrategy.CACHE,
        cache_key: Optional[str] = None,
        fallback_value: Optional[T] = None,
        *args,
        **kwargs,
    ) -> Optional[T]:
        """
        Execute operation with fallback support.

        Args:
            service_name: Name of the service
            operation: Async operation to execute
            fallback_strategy: Strategy to use on failure
            cache_key: Cache key for CACHE strategy
            fallback_value: Value to return on failure
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Operation result or fallback value
        """
        try:
            result = await operation(*args, **kwargs)
            self.health_tracker.record_success(service_name)

            # Cache successful result
            if self.enable_caching and cache_key:
                self.response_cache.set(cache_key, result)

            return result

        except Exception as e:
            logger.warning(f"Operation failed for {service_name}: {e}")
            self.health_tracker.record_failure(service_name)

            # Apply fallback strategy
            return await self._apply_fallback(
                service_name, fallback_strategy, cache_key, fallback_value, e
            )

    async def _apply_fallback(
        self,
        service_name: str,
        strategy: FallbackStrategy,
        cache_key: Optional[str],
        fallback_value: Optional[T],
        error: Exception,
    ) -> Optional[T]:
        """
        Apply fallback strategy.

        Args:
            service_name: Service name
            strategy: Fallback strategy
            cache_key: Cache key
            fallback_value: Fallback value
            error: Original error

        Returns:
            Fallback result
        """
        logger.info(f"Applying fallback strategy '{strategy.value}' for {service_name}")

        if strategy == FallbackStrategy.CACHE and cache_key:
            cached = self.response_cache.get(cache_key)
            if cached is not None:
                logger.info(f"Using cached response for {service_name}")
                return cached

        if strategy == FallbackStrategy.SKIP:
            logger.info(f"Skipping operation for {service_name}")
            return None

        if strategy == FallbackStrategy.SIMPLIFIED or strategy == FallbackStrategy.MANUAL:
            logger.info(f"Using fallback value for {service_name}")
            return fallback_value

        # Default: return None
        logger.warning(f"No fallback available for {service_name}")
        return None

    def get_fallback_message(self, error_type: str) -> str:
        """
        Get a fallback message for an error type.

        Args:
            error_type: Type of error

        Returns:
            User-friendly fallback message
        """
        messages = self.fallback_messages.get(
            error_type, ["Došlo k neočekávané chybě."]
        )
        # Rotate through messages
        import random

        return random.choice(messages)

    def get_service_status_message(self, service_name: str) -> Optional[str]:
        """
        Get status message for a service.

        Args:
            service_name: Name of the service

        Returns:
            Status message or None if operational
        """
        status = self.health_tracker.get_status(service_name)

        if status == ServiceStatus.OPERATIONAL:
            return None

        status_messages = {
            ServiceStatus.DEGRADED: f"Služba {service_name} má problémy. Funkčnost může být omezená.",
            ServiceStatus.PARTIAL_OUTAGE: f"Služba {service_name} je částečně nedostupná.",
            ServiceStatus.MAJOR_OUTAGE: f"Služba {service_name} je nedostupná.",
        }

        return status_messages.get(status)

    def get_health_report(self) -> Dict[str, Any]:
        """
        Get health report for all services.

        Returns:
            Dictionary with service health information
        """
        statuses = self.health_tracker.get_all_statuses()
        cache_stats = self.response_cache.get_stats()

        return {
            "service_statuses": {
                name: status.value for name, status in statuses.items()
            },
            "cache_stats": cache_stats,
            "degraded_services": [
                name
                for name, status in statuses.items()
                if status != ServiceStatus.OPERATIONAL
            ],
        }

    async def check_service_health(
        self, service_name: str, health_check: Callable[..., bool]
    ) -> bool:
        """
        Check service health using a health check function.

        Args:
            service_name: Name of the service
            health_check: Async health check function

        Returns:
            True if service is healthy
        """
        try:
            is_healthy = await health_check()
            if is_healthy:
                self.health_tracker.record_success(service_name)
            else:
                self.health_tracker.record_failure(service_name)
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            self.health_tracker.record_failure(service_name)
            return False


# Global instance
graceful_degradation = GracefulDegradation()
