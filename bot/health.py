"""
Health Check and Monitoring Module

This module provides health check endpoints and monitoring utilities:
- Service health checks
- System metrics collection
- Readiness and liveness probes
- Performance monitoring
"""

import asyncio
import logging
import platform
import psutil
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health check status result."""

    def __init__(
        self,
        healthy: bool,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        latency_ms: Optional[float] = None,
    ):
        """
        Initialize health status.

        Args:
            healthy: Whether the check passed
            message: Status message
            details: Additional details
            latency_ms: Check latency in milliseconds
        """
        self.healthy = healthy
        self.message = message
        self.details = details or {}
        self.latency_ms = latency_ms
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns:
            Health status as dictionary
        """
        return {
            "healthy": self.healthy,
            "message": self.message,
            "details": self.details,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthCheck:
    """
    Health check manager for monitoring bot and service health.

    Provides various health check functions for different components.
    """

    def __init__(self, bot: commands.Bot, config: Any):
        """
        Initialize health check manager.

        Args:
            bot: Discord bot instance
            config: Bot configuration
        """
        self.bot = bot
        self.config = config
        self._check_results: Dict[str, HealthStatus] = {}

    async def check_discord_connection(self) -> HealthStatus:
        """
        Check Discord connection health.

        Returns:
            Health status for Discord connection
        """
        start_time = datetime.now()

        try:
            if not self.bot.is_ready():
                return HealthStatus(
                    healthy=False,
                    message="Bot not ready",
                    details={"is_closed": self.bot.is_closed()},
                )

            if not self.bot.user:
                return HealthStatus(healthy=False, message="Bot user not available")

            # Check latency
            latency = self.bot.latency * 1000  # Convert to ms
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

            is_healthy = latency < 500  # Healthy if latency < 500ms

            return HealthStatus(
                healthy=is_healthy,
                message=f"Discord connection {'healthy' if is_healthy else 'degraded'}",
                details={
                    "latency_ms": round(latency, 2),
                    "guild_count": len(self.bot.guilds),
                    "user_id": str(self.bot.user.id),
                    "user_name": str(self.bot.user),
                },
                latency_ms=round(elapsed_ms, 2),
            )

        except Exception as e:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Discord health check failed: {e}")
            return HealthStatus(
                healthy=False,
                message=f"Discord check failed: {str(e)}",
                latency_ms=round(elapsed_ms, 2),
            )

    async def check_llm_providers(self) -> HealthStatus:
        """
        Check LLM provider health.

        Returns:
            Health status for LLM providers
        """
        start_time = datetime.now()

        try:
            if not hasattr(self.bot, "llm_client"):
                return HealthStatus(
                    healthy=False,
                    message="LLM client not configured",
                )

            # Check provider availability
            availability = await self.bot.llm_client.check_availability()
            available_providers = [
                name for name, available in availability.items() if available
            ]

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

            is_healthy = len(available_providers) > 0

            return HealthStatus(
                healthy=is_healthy,
                message=f"{len(available_providers)} LLM provider(s) available",
                details={
                    "available_providers": available_providers,
                    "total_providers": len(availability),
                    "availability": availability,
                },
                latency_ms=round(elapsed_ms, 2),
            )

        except Exception as e:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"LLM health check failed: {e}")
            return HealthStatus(
                healthy=False,
                message=f"LLM check failed: {str(e)}",
                latency_ms=round(elapsed_ms, 2),
            )

    async def check_system_resources(self) -> HealthStatus:
        """
        Check system resource health.

        Returns:
            Health status for system resources
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage (current directory)
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            # Determine health
            is_healthy = (
                cpu_percent < 90 and memory_percent < 90 and disk_percent < 90
            )

            return HealthStatus(
                healthy=is_healthy,
                message=f"System resources {'healthy' if is_healthy else 'strained'}",
                details={
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_percent": round(memory_percent, 2),
                    "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                    "disk_percent": round(disk_percent, 2),
                    "disk_available_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                },
            )

        except Exception as e:
            logger.error(f"System resources health check failed: {e}")
            return HealthStatus(
                healthy=False,
                message=f"System check failed: {str(e)}",
            )

    async def check_database(self) -> HealthStatus:
        """
        Check database connection health.

        Returns:
            Health status for database
        """
        start_time = datetime.now()

        try:
            # Basic check - verify database URL is configured
            if not self.config.database_url:
                return HealthStatus(
                    healthy=False,
                    message="Database URL not configured",
                )

            # For SQLite, check if file exists and is accessible
            if "sqlite" in self.config.database_url:
                db_path = self.config.database_url.replace("sqlite:///", "")
                import os

                if os.path.exists(db_path):
                    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                    return HealthStatus(
                        healthy=True,
                        message="Database accessible",
                        details={"type": "sqlite", "path": db_path},
                        latency_ms=round(elapsed_ms, 2),
                    )
                else:
                    return HealthStatus(
                        healthy=False,
                        message="Database file not found",
                        details={"type": "sqlite", "path": db_path},
                    )

            # For other databases, just verify URL format
            return HealthStatus(
                healthy=True,
                message="Database configured",
                details={"url": self.config.database_url.split("@")[-1]},  # Hide credentials
            )

        except Exception as e:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Database health check failed: {e}")
            return HealthStatus(
                healthy=False,
                message=f"Database check failed: {str(e)}",
                latency_ms=round(elapsed_ms, 2),
            )

    async def run_all_checks(self) -> Dict[str, HealthStatus]:
        """
        Run all health checks.

        Returns:
            Dictionary mapping check names to health statuses
        """
        logger.debug("Running all health checks...")

        checks = {
            "discord": self.check_discord_connection(),
            "llm": self.check_llm_providers(),
            "system": self.check_system_resources(),
            "database": self.check_database(),
        }

        # Run checks concurrently
        results = await asyncio.gather(*checks.values(), return_exceptions=True)

        # Map results
        check_results = {}
        for (name, _), result in zip(checks.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Health check '{name}' raised exception: {result}")
                check_results[name] = HealthStatus(
                    healthy=False,
                    message=f"Check raised exception: {str(result)}",
                )
            else:
                check_results[name] = result

        self._check_results = check_results
        return check_results

    async def get_readiness_probe(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Get readiness probe result.

        Readiness indicates if the bot is ready to handle requests.

        Returns:
            Tuple of (is_ready, details)
        """
        checks = await self.run_all_checks()

        # Bot is ready if Discord and at least one LLM provider is healthy
        discord_healthy = checks.get("discord", HealthStatus(False, "")).healthy
        llm_healthy = checks.get("llm", HealthStatus(False, "")).healthy

        is_ready = discord_healthy and llm_healthy

        return is_ready, {
            "ready": is_ready,
            "checks": {name: status.to_dict() for name, status in checks.items()},
        }

    async def get_liveness_probe(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Get liveness probe result.

        Liveness indicates if the bot is alive (not deadlocked/crashed).

        Returns:
            Tuple of (is_alive, details)
        """
        # Simple check - if we can execute this, we're alive
        is_alive = True

        # Check if bot is in a recoverable state
        if hasattr(self.bot, "lifecycle"):
            lifecycle_status = self.bot.lifecycle.get_status()
            is_alive = lifecycle_status["state"] not in ["error", "stopped"]

            return is_alive, {
                "alive": is_alive,
                "lifecycle": lifecycle_status,
            }

        return is_alive, {"alive": is_alive}

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics.

        Returns:
            Dictionary with current metrics
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "bot": {
                "user": str(self.bot.user) if self.bot.user else None,
                "guilds": len(self.bot.guilds),
                "latency_ms": round(self.bot.latency * 1000, 2) if self.bot.latency else None,
                "is_ready": self.bot.is_ready(),
            },
            "system": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
            },
        }

        # Add lifecycle info if available
        if hasattr(self.bot, "lifecycle"):
            metrics["lifecycle"] = self.bot.lifecycle.get_status()

        # Add error handler stats if available
        if hasattr(self.bot, "error_handler"):
            metrics["errors"] = self.bot.error_handler.get_error_stats()

        # Add degradation info if available
        if hasattr(self.bot, "degradation"):
            metrics["degradation"] = self.bot.degradation.get_health_report()

        return metrics

    def get_last_check_results(self) -> Dict[str, Dict[str, Any]]:
        """
        Get last health check results.

        Returns:
            Dictionary with last check results
        """
        return {name: status.to_dict() for name, status in self._check_results.items()}


class HealthCheckCog(commands.Cog, name="Health Check"):
    """
    Discord cog for health check commands.

    Provides admin commands to check bot health.
    """

    def __init__(self, bot: commands.Bot, health_check: HealthCheck):
        """
        Initialize health check cog.

        Args:
            bot: Discord bot instance
            health_check: Health check manager
        """
        self.bot = bot
        self.health = health_check

    @commands.command(name="health")
    @commands.has_permissions(administrator=True)
    async def health_command(self, ctx: commands.Context) -> None:
        """
        Check bot health.

        Shows health status of all components.
        """
        async with ctx.typing():
            checks = await self.health.run_all_checks()

            embed = discord.Embed(
                title="Bot Health Status",
                color=discord.Color.green()
                if all(s.healthy for s in checks.values())
                else discord.Color.orange(),
                timestamp=datetime.now(),
            )

            for name, status in checks.items():
                emoji = "✅" if status.healthy else "❌"
                embed.add_field(
                    name=f"{emoji} {name.capitalize()}",
                    value=f"{status.message}\n({status.latency_ms:.1f}ms)"
                    if status.latency_ms
                    else status.message,
                    inline=True,
                )

            await ctx.send(embed=embed)

    @commands.command(name="metrics")
    @commands.has_permissions(administrator=True)
    async def metrics_command(self, ctx: commands.Context) -> None:
        """
        Show bot metrics.

        Displays current performance and usage metrics.
        """
        metrics = self.health.get_metrics()

        embed = discord.Embed(
            title="Bot Metrics", color=discord.Color.blue(), timestamp=datetime.now()
        )

        # Bot metrics
        bot_info = metrics.get("bot", {})
        embed.add_field(
            name="Bot",
            value=f"Guilds: {bot_info.get('guilds', 'N/A')}\n"
            f"Latency: {bot_info.get('latency_ms', 'N/A')}ms",
            inline=True,
        )

        # System metrics
        system_info = metrics.get("system", {})
        embed.add_field(
            name="System",
            value=f"CPU: {system_info.get('cpu_percent', 'N/A')}%\n"
            f"Memory: {system_info.get('memory_percent', 'N/A')}%",
            inline=True,
        )

        # Lifecycle metrics
        if "lifecycle" in metrics:
            lifecycle = metrics["lifecycle"]
            uptime = lifecycle.get("uptime_seconds")
            uptime_str = (
                f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m"
                if uptime
                else "N/A"
            )
            embed.add_field(
                name="Lifecycle",
                value=f"State: {lifecycle.get('state', 'N/A')}\n"
                f"Uptime: {uptime_str}",
                inline=True,
            )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """
    Setup health check cog.

    Args:
        bot: Discord bot instance
    """
    if not hasattr(bot, "health_check"):
        bot.health_check = HealthCheck(bot, bot.config)

    await bot.add_cog(HealthCheckCog(bot, bot.health_check))
    logger.info("Health check cog added to bot")
