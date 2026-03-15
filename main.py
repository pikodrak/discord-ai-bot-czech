"""
Discord AI Bot - Main Entry Point

This is the main entry point for the Discord AI bot that integrates with multiple AI providers
(Claude, Gemini, OpenAI) to provide intelligent responses in Czech language.

Features:
- Environment-based configuration management
- Comprehensive error handling and logging
- Graceful degradation when APIs fail
- Automatic reconnection logic
- Lifecycle management (startup, shutdown, health checks)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.config_loader import load_config, ConfigValidationError
from bot.errors import (
    error_handler,
    DiscordConnectionError,
    DiscordAuthenticationError,
    ConfigurationError,
)
from bot.graceful_degradation import GracefulDegradation
from bot.lifecycle import ManagedBot, LifecycleManager
from bot.utils.logger import setup_logger

# Import shared config and IPC
from src.shared_config import get_shared_config_loader, load_bot_config_from_shared
from src.ipc import get_ipc_channel, IPCCommand, IPCSignal


class DiscordAIBot(ManagedBot):
    """
    Enhanced Discord bot with advanced error handling and lifecycle management.

    This bot extends ManagedBot to include:
    - Multi-provider AI integration (Claude, Gemini, OpenAI)
    - Message history management
    - Context-aware responses
    - Graceful degradation
    - Automatic failover between providers
    """

    def __init__(self, config, *args, use_message_content_intent: bool = True, **kwargs) -> None:
        """
        Initialize the Discord AI Bot with lifecycle management.

        Args:
            config: Advanced bot configuration object
            use_message_content_intent: Whether to request the message_content
                privileged intent. Set to False if not enabled in developer portal.
            *args: Additional arguments for ManagedBot
            **kwargs: Additional keyword arguments for ManagedBot
        """
        # Setup Discord intents
        intents = discord.Intents.default()
        intents.guilds = True

        # message_content is a privileged intent - only request if enabled
        if use_message_content_intent:
            intents.message_content = True

        # Initialize graceful degradation
        degradation = GracefulDegradation(
            enable_caching=config.enable_message_caching
        )

        # Initialize parent with lifecycle management
        super().__init__(
            config=config,
            error_handler=error_handler,
            degradation_manager=degradation,
            command_prefix="!",
            intents=intents,
            help_command=None,
            *args,
            **kwargs
        )

        # IPC channel for communication with admin interface
        self.ipc_channel = get_ipc_channel(project_root)
        self._config_reload_enabled = True
        self._ipc_task: Optional[asyncio.Task] = None

        # Register lifecycle hooks
        self._register_hooks()

    def _register_hooks(self) -> None:
        """Register startup, shutdown, and ready hooks."""
        # Startup hook: Load cogs
        async def load_cogs():
            """Load all bot cogs/extensions."""
            self.logger.info("Loading bot cogs...")
            cogs_to_load = [
                "bot.cogs.ai_chat",
                "bot.cogs.admin",
            ]

            for cog in cogs_to_load:
                try:
                    await self.load_extension(cog)
                    self.logger.info(f"Loaded cog: {cog}")
                except Exception as e:
                    self.logger.error(f"Failed to load cog {cog}: {e}", exc_info=True)
                    # Don't fail completely if a cog fails to load
                    if self.config.enable_graceful_degradation:
                        self.logger.warning(f"Continuing without {cog} (graceful degradation)")
                    else:
                        raise

        # Startup hook: Initialize LLM client
        async def initialize_llm():
            """Initialize LLM client with configured providers."""
            try:
                from src.llm.factory import create_llm_client

                self.logger.info("Initializing LLM client...")
                self.llm_client = await create_llm_client(self.config)

                # Check provider availability
                availability = await self.llm_client.check_availability()
                available = [p for p, avail in availability.items() if avail]

                if available:
                    self.logger.info(f"LLM client initialized with providers: {', '.join(available)}")
                else:
                    self.logger.warning("No LLM providers available at startup")

            except Exception as e:
                self.logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)
                if self.config.enable_graceful_degradation:
                    self.logger.warning("Bot will run with limited AI capabilities")
                else:
                    raise

        # Ready hook: Set bot presence
        async def set_presence():
            """Set bot status and activity."""
            try:
                await self.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.listening,
                        name="AI conversations"
                    )
                )
                self.logger.info("Bot presence set successfully")
            except Exception as e:
                self.logger.warning(f"Failed to set bot presence: {e}")

        # Shutdown hook: Cleanup resources
        async def cleanup_resources():
            """Cleanup resources before shutdown."""
            self.logger.info("Cleaning up resources...")

            # Close LLM client if exists
            if hasattr(self, "llm_client") and self.llm_client:
                try:
                    await self.llm_client.close()
                    self.logger.info("LLM client closed")
                except Exception as e:
                    self.logger.error(f"Error closing LLM client: {e}")

            # Log error statistics
            error_stats = error_handler.get_error_stats()
            if error_stats:
                self.logger.info(f"Session error statistics: {error_stats}")

        # IPC handler setup
        async def setup_ipc_handlers():
            """Setup IPC command handlers."""
            self.logger.info("Setting up IPC handlers...")

            async def handle_reload_config(signal: IPCSignal):
                """Handle configuration reload command."""
                self.logger.info("Received reload config command via IPC")
                try:
                    # Reload configuration from shared storage
                    shared_loader = get_shared_config_loader(project_root)
                    new_config_dict = shared_loader.load_config(force_reload=True)

                    # Update bot config (create new config object)
                    from bot.config_loader import AdvancedBotConfig
                    self.config = AdvancedBotConfig(**new_config_dict)

                    # Reconfigure logger if needed
                    from bot.utils.logger import setup_logger
                    setup_logger(self.config.log_level, self.config.log_file)

                    self.logger.info("Configuration reloaded successfully")
                    return {"message": "Configuration reloaded successfully"}

                except Exception as e:
                    self.logger.error(f"Failed to reload config: {e}", exc_info=True)
                    return {"error": str(e)}

            async def handle_shutdown(signal: IPCSignal):
                """Handle shutdown command."""
                self.logger.info("Received shutdown command via IPC")
                asyncio.create_task(self.close())
                return {"message": "Shutdown initiated"}

            async def handle_ping(signal: IPCSignal):
                """Handle ping command."""
                return {"message": "pong", "status": "running"}

            # Register IPC handlers
            self.ipc_channel.register_handler(IPCCommand.RELOAD_CONFIG, handle_reload_config)
            self.ipc_channel.register_handler(IPCCommand.SHUTDOWN, handle_shutdown)
            self.ipc_channel.register_handler(IPCCommand.PING, handle_ping)

            # Start IPC processing task
            self._ipc_task = asyncio.create_task(self._process_ipc_loop())

            self.logger.info("IPC handlers configured")

        # Shutdown hook: Stop IPC and cleanup
        async def cleanup_ipc():
            """Cleanup IPC resources."""
            self.logger.info("Cleaning up IPC...")

            if self._ipc_task and not self._ipc_task.done():
                self._ipc_task.cancel()
                try:
                    await self._ipc_task
                except asyncio.CancelledError:
                    pass

            self.ipc_channel.cleanup()
            self.logger.info("IPC cleanup complete")

        # Register all hooks
        self.lifecycle.register_startup_hook(load_cogs)
        self.lifecycle.register_startup_hook(initialize_llm)
        self.lifecycle.register_startup_hook(setup_ipc_handlers)
        self.lifecycle.register_ready_hook(set_presence)
        self.lifecycle.register_shutdown_hook(cleanup_resources)
        self.lifecycle.register_shutdown_hook(cleanup_ipc)

    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        """
        Enhanced error handler for command errors.

        Args:
            ctx: Command context
            error: The error that occurred
        """
        # Ignore command not found errors
        if isinstance(error, commands.CommandNotFound):
            return

        # Handle specific error types
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Chybí povinný argument: {error.param.name}")
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Nemáte oprávnění použít tento příkaz.")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Příkaz je na cooldownu. Zkuste to znovu za {error.retry_after:.1f}s.")
            return

        # Log and handle unexpected errors
        bot_error = error_handler.handle_error(
            error.original if hasattr(error, "original") else error,
            {"command": ctx.command.name if ctx.command else None, "channel": ctx.channel.id}
        )

        await ctx.send(bot_error.user_message)

    async def _process_ipc_loop(self) -> None:
        """
        Process IPC signals in a loop.

        This runs continuously to handle commands from the admin interface.
        """
        self.logger.info("IPC processing loop started")

        try:
            while not self.is_closed():
                # Process any pending signals
                await self.ipc_channel.process_signals()

                # Update status
                self.ipc_channel.update_status({
                    "running": True,
                    "guilds": len(self.guilds),
                    "latency_ms": round(self.latency * 1000, 2),
                    "user_count": sum(g.member_count or 0 for g in self.guilds)
                })

                # Sleep to avoid busy waiting
                await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            self.logger.info("IPC processing loop cancelled")
            raise

        except Exception as e:
            self.logger.error(f"Error in IPC processing loop: {e}", exc_info=True)


async def main() -> None:
    """
    Main function to start the Discord bot.

    This function handles:
    - Environment variable loading
    - Configuration management with validation
    - Logger setup with rotation
    - Bot initialization with lifecycle management
    - Graceful error handling and shutdown
    """
    # Load environment variables
    env_file = os.getenv("ENV_FILE", ".env")
    load_dotenv(env_file)

    # Determine environment
    environment = os.getenv("ENVIRONMENT", "development")

    # Setup logging (initial setup, will be reconfigured by config)
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "logs/bot.log")
    logger = setup_logger(log_level, log_file)

    logger.info("=" * 60)
    logger.info(f"Starting Discord AI Bot - Environment: {environment}")
    logger.info("=" * 60)

    # Load and validate configuration
    try:
        logger.info("Loading configuration from shared storage...")

        # First try to load from shared storage
        shared_loader = get_shared_config_loader(project_root)
        config_dict = shared_loader.load_config()

        # Convert to AdvancedBotConfig
        from bot.config_loader import AdvancedBotConfig
        config = AdvancedBotConfig(**config_dict)

        logger.info(f"Configuration loaded from shared storage: {config}")

    except ConfigValidationError as e:
        logger.critical(f"Configuration validation failed: {e}")
        if e.errors:
            for error in e.errors:
                logger.error(f"  - {error}")
        sys.exit(1)

    except Exception as e:
        logger.warning(f"Failed to load from shared storage, falling back to direct load: {e}")

        # Fallback to direct config loading
        try:
            config = load_config(env_file=env_file)
            logger.info(f"Configuration loaded directly: {config}")

            # Save to shared storage for future use
            shared_loader = get_shared_config_loader(project_root)
            shared_loader.save_config(config.model_dump())

        except Exception as fallback_error:
            logger.critical(f"Failed to load configuration: {fallback_error}", exc_info=True)
            sys.exit(1)

    # Reconfigure logger with settings from config
    logger = setup_logger(config.log_level, config.log_file)
    logger.info("Logger reconfigured with settings from configuration")

    # Validate Discord token
    if not config.discord_bot_token:
        logger.critical("DISCORD_BOT_TOKEN not found in configuration")
        raise ConfigurationError("Missing DISCORD_BOT_TOKEN")

    # Create the bot with lifecycle management
    try:
        logger.info("Initializing bot...")
        bot = DiscordAIBot(config)
        logger.info("Bot initialized successfully")

    except Exception as e:
        logger.critical(f"Failed to initialize bot: {e}", exc_info=True)
        sys.exit(1)

    # Start the bot with lifecycle management
    try:
        logger.info("Starting bot with lifecycle management...")
        await bot.start_with_lifecycle(config.discord_bot_token)

    except discord.PrivilegedIntentsRequired:
        logger.warning(
            "Privileged intents (message_content) not enabled in Discord developer portal. "
            "Retrying without privileged intents..."
        )
        # Close the failed bot and recreate without message_content intent
        try:
            await bot.close()
        except Exception:
            pass

        # Recreate bot without message_content intent
        bot = DiscordAIBot(config, use_message_content_intent=False)
        try:
            await bot.start_with_lifecycle(config.discord_bot_token)
        except Exception as e:
            logger.critical(f"Failed to start bot even without privileged intents: {e}")
            sys.exit(1)

    except DiscordAuthenticationError as e:
        logger.critical("Discord authentication failed - check your bot token")
        logger.critical(f"Error: {e}")
        sys.exit(1)

    except DiscordConnectionError as e:
        logger.critical("Failed to connect to Discord")
        logger.critical(f"Error: {e}")
        sys.exit(1)

    except discord.LoginFailure as e:
        logger.critical(f"Discord login failed - check your bot token: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt signal")

    except Exception as e:
        logger.critical(f"Fatal error during bot execution: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logger.info("=" * 60)
        logger.info("Discord AI Bot shutdown complete")
        logger.info("=" * 60)


if __name__ == "__main__":
    """Entry point when script is run directly."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except SystemExit:
        # Re-raise SystemExit to preserve exit codes
        raise
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
