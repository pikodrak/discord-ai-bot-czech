"""
Bot Lifecycle Management Module

This module handles bot lifecycle events:
- Startup initialization and health checks
- Graceful shutdown
- Automatic reconnection logic
- State management
- Signal handling
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import discord
from discord.ext import commands

from bot.errors import (
    DiscordConnectionError,
    ErrorHandler,
    error_handler as default_error_handler,
)
from bot.graceful_degradation import GracefulDegradation, graceful_degradation

logger = logging.getLogger(__name__)


class BotState(str, Enum):
    """Bot lifecycle states."""

    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    RECONNECTING = "reconnecting"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    ERROR = "error"


class LifecycleEvent(str, Enum):
    """Lifecycle event types."""

    STARTUP = "startup"
    READY = "ready"
    SHUTDOWN = "shutdown"
    ERROR = "error"
    RECONNECT = "reconnect"
    DISCONNECT = "disconnect"


class LifecycleManager:
    """
    Manages bot lifecycle and handles reconnection logic.

    Provides:
    - Startup/shutdown hooks
    - Automatic reconnection with exponential backoff
    - Signal handling for graceful shutdown
    - State tracking
    """

    def __init__(
        self,
        bot: commands.Bot,
        config: Any,
        error_handler: Optional[ErrorHandler] = None,
        degradation_manager: Optional[GracefulDegradation] = None,
    ):
        """
        Initialize lifecycle manager.

        Args:
            bot: Discord bot instance
            config: Bot configuration
            error_handler: Error handler instance
            degradation_manager: Graceful degradation manager
        """
        self.bot = bot
        self.config = config
        self.error_handler = error_handler or default_error_handler
        self.degradation = degradation_manager or graceful_degradation

        self._state = BotState.INITIALIZING
        self._startup_time: Optional[datetime] = None
        self._shutdown_requested = False
        self._reconnect_attempts = 0

        # Event hooks
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
        self._ready_hooks: List[Callable] = []

        # Setup signal handlers
        self._setup_signal_handlers()

    @property
    def state(self) -> BotState:
        """Get current bot state."""
        return self._state

    @property
    def uptime(self) -> Optional[float]:
        """Get bot uptime in seconds."""
        if not self._startup_time:
            return None
        return (datetime.now() - self._startup_time).total_seconds()

    def register_startup_hook(self, hook: Callable) -> None:
        """
        Register a startup hook.

        Args:
            hook: Async function to call on startup
        """
        self._startup_hooks.append(hook)
        logger.debug(f"Registered startup hook: {hook.__name__}")

    def register_shutdown_hook(self, hook: Callable) -> None:
        """
        Register a shutdown hook.

        Args:
            hook: Async function to call on shutdown
        """
        self._shutdown_hooks.append(hook)
        logger.debug(f"Registered shutdown hook: {hook.__name__}")

    def register_ready_hook(self, hook: Callable) -> None:
        """
        Register a ready hook.

        Args:
            hook: Async function to call when bot is ready
        """
        self._ready_hooks.append(hook)
        logger.debug(f"Registered ready hook: {hook.__name__}")

    async def startup(self) -> None:
        """
        Execute startup sequence.

        Runs all registered startup hooks and performs initialization.
        """
        logger.info("Starting bot lifecycle...")
        self._state = BotState.STARTING
        self._startup_time = datetime.now()

        try:
            # Run startup hooks
            for hook in self._startup_hooks:
                try:
                    logger.info(f"Running startup hook: {hook.__name__}")
                    await hook()
                except Exception as e:
                    logger.error(f"Startup hook {hook.__name__} failed: {e}", exc_info=True)
                    # Continue with other hooks

            # Perform health checks
            await self._perform_health_checks()

            logger.info("Startup sequence completed successfully")

        except Exception as e:
            logger.error(f"Startup sequence failed: {e}", exc_info=True)
            self._state = BotState.ERROR
            raise

    async def on_ready(self) -> None:
        """
        Handle bot ready event.

        Called when bot successfully connects to Discord.
        """
        logger.info(f"Bot ready: {self.bot.user} (ID: {self.bot.user.id})")
        self._state = BotState.RUNNING
        self._reconnect_attempts = 0  # Reset on successful connection

        try:
            # Run ready hooks
            for hook in self._ready_hooks:
                try:
                    logger.info(f"Running ready hook: {hook.__name__}")
                    await hook()
                except Exception as e:
                    logger.error(f"Ready hook {hook.__name__} failed: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in on_ready: {e}", exc_info=True)

    async def shutdown(self, graceful: bool = True) -> None:
        """
        Execute shutdown sequence.

        Args:
            graceful: Whether to perform graceful shutdown
        """
        if self._shutdown_requested:
            logger.warning("Shutdown already in progress")
            return

        self._shutdown_requested = True
        self._state = BotState.SHUTTING_DOWN

        logger.info(f"Initiating {'graceful' if graceful else 'immediate'} shutdown...")

        try:
            if graceful:
                # Run shutdown hooks
                for hook in self._shutdown_hooks:
                    try:
                        logger.info(f"Running shutdown hook: {hook.__name__}")
                        await hook()
                    except Exception as e:
                        logger.error(
                            f"Shutdown hook {hook.__name__} failed: {e}", exc_info=True
                        )

            # Close bot connection
            if not self.bot.is_closed():
                logger.info("Closing bot connection...")
                await self.bot.close()

            self._state = BotState.STOPPED
            logger.info("Shutdown completed successfully")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            self._state = BotState.ERROR
            raise

    async def handle_disconnect(self) -> None:
        """
        Handle disconnect event.

        Implements reconnection logic with exponential backoff.
        """
        if self._shutdown_requested:
            logger.info("Disconnect during shutdown, skipping reconnection")
            return

        if not self.config.enable_auto_reconnect:
            logger.warning("Auto-reconnect disabled, not attempting reconnection")
            return

        logger.warning("Bot disconnected from Discord")
        self._state = BotState.RECONNECTING

        while self._reconnect_attempts < self.config.max_reconnect_attempts:
            self._reconnect_attempts += 1

            # Calculate backoff delay
            delay = min(
                self.config.reconnect_base_delay
                * (self.config.retry_exponential_base ** (self._reconnect_attempts - 1)),
                self.config.retry_max_delay,
            )

            logger.info(
                f"Reconnection attempt {self._reconnect_attempts}/"
                f"{self.config.max_reconnect_attempts} in {delay:.1f}s..."
            )

            await asyncio.sleep(delay)

            try:
                # Attempt reconnection
                await self.bot.connect(reconnect=True)
                logger.info("Reconnection successful")
                self._reconnect_attempts = 0
                self._state = BotState.RUNNING
                return

            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
                self.error_handler.handle_error(e, {"service": "discord_reconnect"})

        # Max attempts reached
        logger.critical("Maximum reconnection attempts reached, giving up")
        self._state = BotState.ERROR
        await self.shutdown(graceful=False)

    async def _perform_health_checks(self) -> None:
        """
        Perform startup health checks.

        Verifies that critical services are available.
        """
        logger.info("Performing startup health checks...")

        # Check LLM providers
        if hasattr(self.bot, "llm_client"):
            try:
                availability = await self.bot.llm_client.check_availability()
                available_providers = [
                    name for name, available in availability.items() if available
                ]

                if available_providers:
                    logger.info(f"Available LLM providers: {', '.join(available_providers)}")
                else:
                    logger.warning("No LLM providers available at startup")

            except Exception as e:
                logger.error(f"LLM health check failed: {e}")

        logger.info("Health checks completed")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        try:
            if sys.platform == "win32":
                # Windows signal handling
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            else:
                # Unix signal handling - try to use loop-based handlers
                try:
                    loop = asyncio.get_running_loop()
                    for sig in (signal.SIGINT, signal.SIGTERM):
                        loop.add_signal_handler(
                            sig,
                            lambda s=sig: asyncio.create_task(
                                self._async_signal_handler(s)
                            ),
                        )
                except RuntimeError:
                    # No running event loop yet, use basic signal handlers
                    signal.signal(signal.SIGINT, self._signal_handler)
                    signal.signal(signal.SIGTERM, self._signal_handler)

            logger.debug("Signal handlers configured")
        except Exception as e:
            logger.warning(f"Could not set up signal handlers: {e}")

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """
        Handle signals (Windows).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.shutdown(graceful=True))

    async def _async_signal_handler(self, signum: int) -> None:
        """
        Handle signals asynchronously (Unix).

        Args:
            signum: Signal number
        """
        logger.info(f"Received signal {signum}, initiating shutdown...")
        await self.shutdown(graceful=True)

    def get_status(self) -> Dict[str, Any]:
        """
        Get current lifecycle status.

        Returns:
            Dictionary with lifecycle status information
        """
        return {
            "state": self._state.value,
            "uptime_seconds": self.uptime,
            "reconnect_attempts": self._reconnect_attempts,
            "shutdown_requested": self._shutdown_requested,
            "startup_time": self._startup_time.isoformat() if self._startup_time else None,
        }


class ManagedBot(commands.Bot):
    """
    Extended Discord bot with lifecycle management.

    This bot class integrates lifecycle management, error handling,
    and graceful degradation.
    """

    def __init__(
        self,
        config: Any,
        error_handler: Optional[ErrorHandler] = None,
        degradation_manager: Optional[GracefulDegradation] = None,
        *args,
        **kwargs,
    ):
        """
        Initialize managed bot.

        Args:
            config: Bot configuration
            error_handler: Error handler instance
            degradation_manager: Graceful degradation manager
            *args: Bot arguments
            **kwargs: Bot keyword arguments
        """
        super().__init__(*args, **kwargs)

        self.config = config
        self.lifecycle = LifecycleManager(
            bot=self,
            config=config,
            error_handler=error_handler,
            degradation_manager=degradation_manager,
        )

        self.logger = logging.getLogger("discord_bot")

    async def setup_hook(self) -> None:
        """Setup hook called when bot starts."""
        await self.lifecycle.startup()

    async def on_ready(self) -> None:
        """Event handler for bot ready."""
        await self.lifecycle.on_ready()

    async def on_disconnect(self) -> None:
        """Event handler for bot disconnect.

        Note: discord.py handles reconnection internally.
        We only log the disconnect here; manual reconnection is not needed
        and would interfere with discord.py's own reconnection logic.
        """
        logger.info("Bot disconnected from Discord")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """
        Global error handler.

        Args:
            event_method: Event that caused the error
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        error = sys.exc_info()[1]
        if error:
            self.lifecycle.error_handler.handle_error(
                error, {"event": event_method, "args": args, "kwargs": kwargs}
            )

    async def start_with_lifecycle(self, token: str) -> None:
        """
        Start bot with lifecycle management.

        Args:
            token: Discord bot token
        """
        try:
            async with self:
                await self.start(token)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            # Run shutdown before re-raising
            try:
                await self.lifecycle.shutdown(graceful=True)
            except Exception:
                pass
            raise
