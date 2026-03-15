"""
Discord AI Bot - Enhanced Main Entry Point

This is an enhanced version with:
- Advanced configuration management
- Comprehensive error handling
- Graceful degradation
- Bot lifecycle management
- Health checks and monitoring
- Automatic reconnection logic
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.config_loader import AdvancedBotConfig, ConfigLoader, ConfigValidationError
from bot.errors import (
    BotError,
    ConfigurationError,
    DiscordAuthenticationError,
    ErrorHandler,
    MissingConfigurationError,
)
from bot.graceful_degradation import GracefulDegradation
from bot.health import HealthCheck
from bot.lifecycle import ManagedBot
from bot.utils.logger import setup_logger


class EnhancedDiscordBot(ManagedBot):
    """
    Enhanced Discord bot with full lifecycle and error handling.

    This bot includes:
    - Lifecycle management with auto-reconnect
    - Error handling with graceful degradation
    - Health monitoring
    - LLM client integration
    """

    def __init__(self, config: AdvancedBotConfig) -> None:
        """
        Initialize enhanced Discord bot.

        Args:
            config: Bot configuration
        """
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        # Initialize error handler and degradation manager
        error_handler = ErrorHandler(
            enable_graceful_degradation=config.enable_graceful_degradation
        )
        degradation = GracefulDegradation(enable_caching=config.enable_message_caching)

        # Initialize managed bot
        super().__init__(
            config=config,
            error_handler=error_handler,
            degradation_manager=degradation,
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        self.error_handler = error_handler
        self.degradation = degradation
        self.logger = logging.getLogger("discord_bot")

        # Initialize health check
        if config.enable_health_checks:
            self.health_check = HealthCheck(self, config)

        # Register lifecycle hooks
        self._register_lifecycle_hooks()

    def _register_lifecycle_hooks(self) -> None:
        """Register lifecycle event hooks."""

        async def startup_hook():
            """Startup hook to initialize components."""
            self.logger.info("Running startup initialization...")

            # Initialize LLM client
            await self._initialize_llm_client()

            # Perform initial health checks
            if self.config.enable_health_checks:
                await self.health_check.run_all_checks()

        async def shutdown_hook():
            """Shutdown hook to cleanup resources."""
            self.logger.info("Running shutdown cleanup...")

            # Clear caches
            if hasattr(self.degradation, "response_cache"):
                self.degradation.response_cache.clear()

            self.logger.info("Cleanup completed")

        async def ready_hook():
            """Ready hook to set bot status."""
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening, name="AI conversations"
                )
            )
            self.logger.info(f"Bot is ready and connected to {len(self.guilds)} guilds")

        self.lifecycle.register_startup_hook(startup_hook)
        self.lifecycle.register_shutdown_hook(shutdown_hook)
        self.lifecycle.register_ready_hook(ready_hook)

    async def _initialize_llm_client(self) -> None:
        """Initialize LLM client with error handling."""
        try:
            from src.llm.client import LLMClient

            self.llm_client = LLMClient(
                anthropic_api_key=self.config.anthropic_api_key,
                google_api_key=self.config.google_api_key,
                openai_api_key=self.config.openai_api_key,
                max_retries=self.config.max_retry_attempts,
                retry_delay=self.config.retry_base_delay,
                language=self.config.bot_language,
            )

            # Register LLM client in degradation manager
            self.degradation.health_tracker.record_success("llm_client")

            self.logger.info(
                f"LLM client initialized with providers: "
                f"{self.llm_client.get_available_providers()}"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)
            self.degradation.health_tracker.record_failure("llm_client")
            raise ConfigurationError(
                "LLM client initialization failed", details={"error": str(e)}
            )

    async def setup_hook(self) -> None:
        """Setup hook - load cogs and initialize components."""
        # Run parent setup
        await super().setup_hook()

        self.logger.info("Loading cogs...")

        # Load cogs
        cogs_to_load = [
            "bot.cogs.ai_chat",
            "bot.cogs.admin",
        ]

        # Add health check cog if enabled
        if self.config.enable_health_checks:
            cogs_to_load.append("bot.health")

        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                self.logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                self.logger.error(f"Failed to load cog {cog}: {e}", exc_info=True)
                # Continue loading other cogs

        self.logger.info("Cog loading completed")

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """
        Enhanced command error handler.

        Args:
            ctx: Command context
            error: The error that occurred
        """
        # Ignore command not found
        if isinstance(error, commands.CommandNotFound):
            return

        # Handle specific errors
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Chybějící argument: {error.param.name}")
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Nemáte oprávnění k použití tohoto příkazu.")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Příkaz je na cooldownu. Zkuste to za {error.retry_after:.1f}s.")
            return

        # Handle bot errors
        if isinstance(error, BotError):
            bot_error = error
        else:
            # Convert to bot error
            bot_error = self.error_handler.handle_error(
                error, {"command": ctx.command.name if ctx.command else "unknown"}
            )

        # Log error
        bot_error.log()

        # Send user-friendly message
        await ctx.send(bot_error.user_message)


async def load_configuration() -> AdvancedBotConfig:
    """
    Load and validate bot configuration.

    Returns:
        Loaded configuration

    Raises:
        ConfigValidationError: If configuration is invalid
    """
    # Load environment variables
    load_dotenv()

    # Load configuration
    config_loader = ConfigLoader()

    try:
        config = config_loader.load()
        return config

    except ConfigValidationError as e:
        print(f"Configuration validation failed: {e}")
        if e.errors:
            print("\nValidation errors:")
            for error in e.errors:
                print(f"  - {error}")
        sys.exit(1)

    except Exception as e:
        print(f"Failed to load configuration: {e}")
        sys.exit(1)


async def main() -> None:
    """
    Main function to start the enhanced Discord bot.

    This function handles:
    - Configuration loading and validation
    - Logging setup
    - Bot initialization with lifecycle management
    - Error handling and graceful shutdown
    """
    # Load configuration
    config = await load_configuration()

    # Setup logging
    logger = setup_logger(config.log_level, config.log_file)
    logger.info("=" * 60)
    logger.info("Discord AI Bot Starting")
    logger.info(f"Environment: {config.environment.value}")
    logger.info(f"Available AI providers: {config.get_available_providers()}")
    logger.info("=" * 60)

    # Validate Discord token
    if not config.discord_bot_token:
        logger.error("DISCORD_BOT_TOKEN not found in configuration")
        raise MissingConfigurationError("DISCORD_BOT_TOKEN")

    # Create bot instance
    try:
        bot = EnhancedDiscordBot(config)
        logger.info("Bot instance created successfully")
    except Exception as e:
        logger.error(f"Failed to create bot instance: {e}", exc_info=True)
        sys.exit(1)

    # Start bot with lifecycle management
    try:
        logger.info("Starting bot with lifecycle management...")
        await bot.start_with_lifecycle(config.discord_bot_token)

    except discord.LoginFailure as e:
        logger.critical(f"Discord authentication failed: {e}")
        raise DiscordAuthenticationError(str(e))

    except Exception as e:
        logger.critical(f"Fatal error during bot execution: {e}", exc_info=True)
        raise

    finally:
        logger.info("Bot process terminated")


def run_bot() -> None:
    """
    Entry point for running the bot.

    Handles top-level exception catching and exit codes.
    """
    try:
        # Run async main
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n✓ Bot stopped by user")
        sys.exit(0)

    except ConfigValidationError as e:
        print(f"\n✗ Configuration error: {e}")
        sys.exit(1)

    except DiscordAuthenticationError as e:
        print(f"\n✗ Discord authentication failed: {e}")
        print("Please check your DISCORD_BOT_TOKEN")
        sys.exit(1)

    except BotError as e:
        print(f"\n✗ Bot error: {e.message}")
        print(f"  User message: {e.user_message}")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    """Entry point when script is run directly."""
    run_bot()
