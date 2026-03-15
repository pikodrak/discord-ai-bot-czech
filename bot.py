"""
Main Discord bot module.
Handles bot initialization, event handling, and command routing.
"""

import discord
from discord.ext import commands
from typing import Optional
import logging

from src.config import Settings, get_settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DiscordAIBot(commands.Bot):
    """Discord bot with AI integration."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Initialize the Discord bot with required intents.

        Args:
            settings: Optional settings instance (uses global if not provided)
        """
        self.settings = settings or get_settings()

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=self.settings.bot_prefix,
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )

        self.available_providers = self.settings.get_available_providers()
        logger.info(f"Available AI providers: {self.available_providers}")

    async def setup_hook(self) -> None:
        """
        Async initialization hook called when bot is starting.
        Used to load cogs and perform async setup.
        """
        logger.info("Bot is setting up...")
        # TODO: Load cogs/extensions here when created
        # await self.load_extension('cogs.ai_commands')

    async def on_ready(self) -> None:
        """Event handler called when bot successfully connects to Discord."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info("Bot is ready!")

        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{self.settings.bot_prefix}help"
            )
        )

    async def on_message(self, message: discord.Message) -> None:
        """
        Event handler for incoming messages.

        Args:
            message: The received Discord message.
        """
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Log message for debugging
        logger.debug(f"Message from {message.author}: {message.content}")

        # Process commands
        await self.process_commands(message)

    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        """
        Global error handler for command errors.

        Args:
            ctx: Command context.
            error: The error that occurred.
        """
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Command not found. Use {self.settings.bot_prefix}help for available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        else:
            logger.error(f"Unhandled error in command {ctx.command}: {error}", exc_info=error)
            await ctx.send("An error occurred while processing the command.")


def main() -> None:
    """
    Main entry point for the Discord bot.
    Validates configuration and starts the bot.
    """
    # Load settings
    settings = get_settings()

    # Validate configuration
    if not settings.discord_bot_token:
        logger.error("Discord bot token not configured. Please check your .env file.")
        return

    if not settings.has_any_ai_key():
        logger.error("No AI API keys configured. Please configure at least one.")
        return

    # Create and run bot
    bot = DiscordAIBot(settings)

    try:
        logger.info("Starting bot...")
        bot.run(settings.discord_bot_token, log_handler=None)
    except discord.LoginFailure:
        logger.error("Failed to login. Please check your DISCORD_BOT_TOKEN.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=e)


if __name__ == "__main__":
    main()
