"""
AI Chat Cog - Main Discord Bot Conversation Handler

This cog handles all AI-powered conversation functionality, including:
- Message processing and filtering
- Context management
- LLM integration for generating responses
- Czech language response generation
"""

import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands

from bot.context_manager import ContextManager
from bot.interest_filter import InterestFilter
from src.llm.client import LLMClient
from src.llm.base import LLMMessage
from src.llm.exceptions import LLMAllProvidersFailedError

logger = logging.getLogger(__name__)


class AIChatCog(commands.Cog, name="AI Chat"):
    """
    Handles AI-powered chat interactions in Discord.

    This cog listens to messages, determines if the bot should respond,
    maintains conversation context, and generates appropriate responses
    using configured LLM providers.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initialize the AI Chat cog.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.config = bot.config

        # Initialize components
        self.context_manager = ContextManager(
            max_messages_per_channel=self.config.bot_max_history
        )

        self.interest_filter = InterestFilter(
            bot_user_id=None,  # Will be set in cog_load
            response_threshold=self.config.bot_response_threshold,
            always_respond_in_dms=True
        )

        # Initialize LLM client
        self.llm_client = LLMClient(
            anthropic_api_key=self.config.anthropic_api_key,
            google_api_key=self.config.google_api_key,
            openai_api_key=self.config.openai_api_key,
            max_retries=3,
            retry_delay=1.0,
            language=self.config.bot_language
        )

        # Channel restrictions
        self.allowed_channel_ids = self.config.get_channel_ids()

        # System prompt for Czech responses
        self.system_prompt = self._build_system_prompt()

        logger.info("AI Chat cog initialized")

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the LLM.

        Returns:
            System prompt string
        """
        language_map = {
            "cs": "Czech",
            "en": "English",
            "sk": "Slovak",
        }

        language = language_map.get(self.config.bot_language, "Czech")
        personality = self.config.bot_personality

        return f"""You are a helpful AI assistant participating in a Discord conversation.

Language: Respond in {language} language.
Personality: {personality}

Guidelines:
- Be natural and conversational
- Keep responses concise (1-3 paragraphs unless more detail is requested)
- Show personality appropriate to the conversation tone
- Use Discord-appropriate formatting (markdown)
- If you see multiple users in the conversation, address them by name when relevant
- Don't repeat information unnecessarily
- If you're unsure, ask clarifying questions

Remember: You're part of an ongoing conversation, so read the context carefully."""

    async def cog_load(self) -> None:
        """
        Called when the cog is loaded.

        Note: We cannot call wait_until_ready() here because cog_load
        is called during setup_hook, before the bot connects to Discord.
        The bot user ID will be set in on_ready via a listener instead.
        """
        logger.info("AI Chat cog loaded successfully")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Update interest filter with bot's user ID once connected."""
        if self.bot.user:
            self.interest_filter.update_bot_user_id(self.bot.user.id)
            logger.info(f"Set bot user ID in interest filter: {self.bot.user.id}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Event listener for all messages.

        Args:
            message: Discord message object
        """
        # Ignore own messages
        if message.author == self.bot.user:
            return

        # Ignore other bots (configurable)
        if message.author.bot:
            return

        # Check channel restrictions
        if self.allowed_channel_ids:
            if message.channel.id not in self.allowed_channel_ids:
                # Not in allowed channel, ignore
                return

        # Add message to context
        self.context_manager.add_message(message.channel.id, message)

        # Check if message is a reply to the bot
        is_reply_to_bot = False
        if message.reference and message.reference.resolved:
            referenced_msg = message.reference.resolved
            if isinstance(referenced_msg, discord.Message):
                is_reply_to_bot = referenced_msg.author == self.bot.user

        # Get recent conversation context
        recent_messages = self.context_manager.get_context_messages(
            message.channel.id,
            limit=5
        )
        conversation_context = [msg.content for msg in recent_messages]

        # Check if bot should respond
        should_respond, score, reason = self.interest_filter.should_respond(
            message,
            is_reply_to_bot=is_reply_to_bot,
            conversation_context=conversation_context
        )

        if not should_respond:
            logger.debug(
                f"Ignoring message {message.id} from {message.author.name}: "
                f"score={score:.2f}, reason={reason}"
            )
            return

        logger.info(
            f"Responding to message from {message.author.name} "
            f"(score={score:.2f}, reason={reason})"
        )

        # Generate and send response
        await self._generate_and_send_response(message)

    async def _generate_and_send_response(self, message: discord.Message) -> None:
        """
        Generate AI response and send it to Discord.

        Args:
            message: Original Discord message to respond to
        """
        # Show typing indicator
        async with message.channel.typing():
            try:
                # Get conversation context
                context_messages = self.context_manager.format_for_llm(
                    message.channel.id,
                    limit=20,  # Last 20 messages for context
                    include_bot_messages=True
                )

                # Convert to LLM format
                llm_messages = [
                    LLMMessage(role=msg["role"], content=msg["content"])
                    for msg in context_messages
                ]

                # Generate response using LLM
                response = await self.llm_client.generate_response(
                    messages=llm_messages,
                    system_prompt=self.system_prompt,
                    temperature=0.7,
                    max_tokens=1000
                )

                # Send response
                await self._send_response(message, response.content, response.provider)

                logger.info(
                    f"Successfully sent response using {response.provider} "
                    f"({response.tokens_used} tokens)"
                )

            except LLMAllProvidersFailedError as e:
                logger.error(f"All LLM providers failed: {e}")
                await message.channel.send(
                    "Omlouváme se, momentálně nejsem schopen odpovědět. "
                    "Zkuste to prosím později."
                )

            except discord.HTTPException as e:
                logger.error(f"Failed to send Discord message: {e}")

            except Exception as e:
                logger.error(f"Unexpected error generating response: {e}", exc_info=True)
                await message.channel.send(
                    "Omlouváme se, došlo k neočekávané chybě."
                )

    async def _send_response(
        self,
        original_message: discord.Message,
        content: str,
        provider: str
    ) -> None:
        """
        Send response to Discord, handling long messages.

        Args:
            original_message: Original message being responded to
            content: Response content
            provider: LLM provider that generated the response
        """
        # Discord message limit is 2000 characters
        max_length = 1900  # Leave some buffer

        # Add provider attribution if in debug mode
        if self.config.log_level == "DEBUG":
            content = f"{content}\n\n*[{provider}]*"

        # Split long messages
        if len(content) <= max_length:
            await original_message.reply(content)
        else:
            # Split into chunks
            chunks = [
                content[i:i + max_length]
                for i in range(0, len(content), max_length)
            ]

            # Send first chunk as reply
            await original_message.reply(chunks[0])

            # Send remaining chunks
            for chunk in chunks[1:]:
                await original_message.channel.send(chunk)
                await asyncio.sleep(0.5)  # Small delay between chunks

    @commands.command(name="clear_context")
    @commands.has_permissions(manage_messages=True)
    async def clear_context(self, ctx: commands.Context) -> None:
        """
        Clear conversation context for current channel.

        Requires: Manage Messages permission
        """
        self.context_manager.clear_channel(ctx.channel.id)
        await ctx.send("Konverzační kontext pro tento kanál byl vymazán.")
        logger.info(
            f"Context cleared for channel {ctx.channel.id} by {ctx.author.name}"
        )

    @commands.command(name="context_stats")
    @commands.has_permissions(manage_messages=True)
    async def context_stats(self, ctx: commands.Context) -> None:
        """
        Show conversation context statistics.

        Requires: Manage Messages permission
        """
        stats = self.context_manager.get_stats()

        embed = discord.Embed(
            title="Context Statistics",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Total Windows",
            value=stats["total_windows"],
            inline=True
        )
        embed.add_field(
            name="Total Messages",
            value=stats["total_messages"],
            inline=True
        )
        embed.add_field(
            name="Max per Channel",
            value=stats["max_messages_per_channel"],
            inline=True
        )

        # Add current channel info if available
        if ctx.channel.id in stats["windows"]:
            window_stats = stats["windows"][ctx.channel.id]
            embed.add_field(
                name="This Channel",
                value=f"{window_stats['message_count']} messages",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="set_threshold")
    @commands.has_permissions(administrator=True)
    async def set_threshold(self, ctx: commands.Context, threshold: float) -> None:
        """
        Set response threshold (0.0 to 1.0).

        Args:
            threshold: New threshold value

        Requires: Administrator permission
        """
        try:
            self.interest_filter.set_threshold(threshold)
            await ctx.send(f"Práh odpovědi nastaven na {threshold}")
            logger.info(
                f"Response threshold changed to {threshold} by {ctx.author.name}"
            )
        except ValueError as e:
            await ctx.send(f"Chyba: {e}")

    @commands.command(name="add_keyword")
    @commands.has_permissions(administrator=True)
    async def add_keyword(self, ctx: commands.Context, keyword: str) -> None:
        """
        Add a trigger keyword.

        Args:
            keyword: Keyword to add

        Requires: Administrator permission
        """
        self.interest_filter.add_keyword(keyword)
        await ctx.send(f"Přidáno klíčové slovo: {keyword}")

    @commands.command(name="remove_keyword")
    @commands.has_permissions(administrator=True)
    async def remove_keyword(self, ctx: commands.Context, keyword: str) -> None:
        """
        Remove a trigger keyword.

        Args:
            keyword: Keyword to remove

        Requires: Administrator permission
        """
        if self.interest_filter.remove_keyword(keyword):
            await ctx.send(f"Odstraněno klíčové slovo: {keyword}")
        else:
            await ctx.send(f"Klíčové slovo nenalezeno: {keyword}")

    @commands.command(name="list_keywords")
    @commands.has_permissions(manage_messages=True)
    async def list_keywords(self, ctx: commands.Context) -> None:
        """
        List all configured keywords.

        Requires: Manage Messages permission
        """
        keywords = self.interest_filter.get_keywords()

        if keywords:
            keyword_list = ", ".join(sorted(keywords))
            await ctx.send(f"Klíčová slova: {keyword_list}")
        else:
            await ctx.send("Žádná vlastní klíčová slova nejsou nastavena.")


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.

    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(AIChatCog(bot))
    logger.info("AI Chat cog added to bot")
