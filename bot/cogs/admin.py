"""
Admin Cog - Bot Management and Control

This cog provides administrative commands for managing the bot,
including status checks, configuration, and diagnostics.
"""

import logging
import platform
import sys
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class AdminCog(commands.Cog, name="Admin"):
    """
    Administrative commands for bot management.

    Provides commands for checking bot status, managing configuration,
    and performing administrative tasks.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initialize the Admin cog.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.config = bot.config
        self.start_time = datetime.now()

        logger.info("Admin cog initialized")

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        """
        Check bot latency.

        Shows the bot's current latency to Discord servers.
        """
        latency_ms = round(self.bot.latency * 1000, 2)
        await ctx.send(f"🏓 Pong! Latence: {latency_ms}ms")

    @commands.command(name="status")
    @commands.has_permissions(manage_guild=True)
    async def status(self, ctx: commands.Context) -> None:
        """
        Show detailed bot status.

        Displays information about bot uptime, configuration,
        and connected services.

        Requires: Manage Server permission
        """
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        # Create embed
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )

        # Basic info
        embed.add_field(
            name="Uptime",
            value=uptime_str,
            inline=True
        )
        embed.add_field(
            name="Latency",
            value=f"{round(self.bot.latency * 1000, 2)}ms",
            inline=True
        )
        embed.add_field(
            name="Guilds",
            value=len(self.bot.guilds),
            inline=True
        )

        # Configuration
        embed.add_field(
            name="Language",
            value=self.config.bot_language.upper(),
            inline=True
        )
        embed.add_field(
            name="Response Threshold",
            value=f"{self.config.bot_response_threshold:.2f}",
            inline=True
        )
        embed.add_field(
            name="Max History",
            value=self.config.bot_max_history,
            inline=True
        )

        # AI Providers
        providers = self.config.get_available_providers()
        providers_str = ", ".join(providers) if providers else "None"
        embed.add_field(
            name="AI Providers",
            value=providers_str,
            inline=False
        )

        # System info
        embed.add_field(
            name="Python Version",
            value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            inline=True
        )
        embed.add_field(
            name="Discord.py Version",
            value=discord.__version__,
            inline=True
        )

        embed.set_footer(text=f"Requested by {ctx.author.name}")

        await ctx.send(embed=embed)

    @commands.command(name="info")
    async def info(self, ctx: commands.Context) -> None:
        """
        Show bot information.

        Displays basic information about the bot and its purpose.
        """
        embed = discord.Embed(
            title="Discord AI Bot",
            description=(
                "Inteligentní Discord bot s podporou více AI poskytovatelů "
                "(Claude, Gemini, OpenAI).\n\n"
                "Bot automaticky detekuje relevantní zprávy a reaguje na ně "
                "s využitím kontextu konverzace."
            ),
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Jazyk odpovědí",
            value="Čeština (Czech)",
            inline=True
        )
        embed.add_field(
            name="Dostupné příkazy",
            value="Použijte `!help` pro seznam příkazů",
            inline=True
        )

        embed.set_footer(text="Vytvořeno s využitím discord.py a AI API")

        await ctx.send(embed=embed)

    @commands.command(name="providers")
    @commands.has_permissions(manage_guild=True)
    async def providers(self, ctx: commands.Context) -> None:
        """
        Check AI provider availability.

        Tests connectivity to configured AI providers.

        Requires: Manage Server permission
        """
        # Get AI chat cog to access LLM client
        ai_chat_cog = self.bot.get_cog("AI Chat")

        if not ai_chat_cog:
            await ctx.send("⚠️ AI Chat cog není načten")
            return

        embed = discord.Embed(
            title="AI Provider Status",
            color=discord.Color.blue()
        )

        # Show typing while checking
        async with ctx.typing():
            try:
                # Check availability
                availability = await ai_chat_cog.llm_client.check_availability()

                for provider, is_available in availability.items():
                    status_emoji = "✅" if is_available else "❌"
                    status_text = "Available" if is_available else "Unavailable"

                    embed.add_field(
                        name=f"{status_emoji} {provider.title()}",
                        value=status_text,
                        inline=True
                    )

                if not availability:
                    embed.description = "No AI providers configured"

            except Exception as e:
                logger.error(f"Error checking provider availability: {e}")
                embed.description = f"Error checking providers: {e}"
                embed.color = discord.Color.red()

        await ctx.send(embed=embed)

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, ctx: commands.Context, cog_name: str) -> None:
        """
        Reload a bot cog.

        Args:
            cog_name: Name of the cog to reload (e.g., 'ai_chat', 'admin')

        Requires: Bot owner only
        """
        cog_path = f"bot.cogs.{cog_name}"

        try:
            await self.bot.reload_extension(cog_path)
            await ctx.send(f"✅ Cog `{cog_name}` byl úspěšně znovu načten")
            logger.info(f"Cog {cog_name} reloaded by {ctx.author.name}")

        except commands.ExtensionNotLoaded:
            await ctx.send(f"❌ Cog `{cog_name}` není načten")

        except commands.ExtensionNotFound:
            await ctx.send(f"❌ Cog `{cog_name}` nebyl nalezen")

        except Exception as e:
            await ctx.send(f"❌ Chyba při načítání cog: {e}")
            logger.error(f"Error reloading cog {cog_name}: {e}", exc_info=True)

    @commands.command(name="shutdown")
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context) -> None:
        """
        Shutdown the bot.

        Requires: Bot owner only
        """
        await ctx.send("👋 Bot se vypíná...")
        logger.info(f"Bot shutdown initiated by {ctx.author.name}")
        await self.bot.close()

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context, command: Optional[str] = None) -> None:
        """
        Show help information.

        Args:
            command: Optional specific command to get help for
        """
        if command:
            # Show help for specific command
            cmd = self.bot.get_command(command)
            if cmd:
                embed = discord.Embed(
                    title=f"Command: {cmd.name}",
                    description=cmd.help or "No description available",
                    color=discord.Color.blue()
                )

                if cmd.aliases:
                    embed.add_field(
                        name="Aliases",
                        value=", ".join(cmd.aliases),
                        inline=False
                    )

                # Show usage
                signature = f"!{cmd.name} {cmd.signature}" if cmd.signature else f"!{cmd.name}"
                embed.add_field(
                    name="Usage",
                    value=f"`{signature}`",
                    inline=False
                )

                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Příkaz `{command}` nebyl nalezen")
            return

        # Show general help
        embed = discord.Embed(
            title="📚 Nápověda - Dostupné příkazy",
            description="Seznam všech dostupných příkazů",
            color=discord.Color.blue()
        )

        # General commands
        general_commands = [
            ("!ping", "Zkontrolovat latenci bota"),
            ("!info", "Informace o botovi"),
            ("!help [příkaz]", "Zobrazit nápovědu"),
        ]

        embed.add_field(
            name="🔹 Obecné",
            value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in general_commands]),
            inline=False
        )

        # Context management (requires Manage Messages)
        context_commands = [
            ("!clear_context", "Vymazat kontext konverzace"),
            ("!context_stats", "Zobrazit statistiky kontextu"),
            ("!list_keywords", "Zobrazit klíčová slova"),
        ]

        embed.add_field(
            name="🔹 Správa kontextu (vyžaduje 'Manage Messages')",
            value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in context_commands]),
            inline=False
        )

        # Admin commands (requires Administrator)
        admin_commands = [
            ("!set_threshold <0.0-1.0>", "Nastavit práh odpovídání"),
            ("!add_keyword <slovo>", "Přidat klíčové slovo"),
            ("!remove_keyword <slovo>", "Odebrat klíčové slovo"),
        ]

        embed.add_field(
            name="🔹 Administrace (vyžaduje 'Administrator')",
            value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in admin_commands]),
            inline=False
        )

        # Server management (requires Manage Server)
        server_commands = [
            ("!status", "Zobrazit stav bota"),
            ("!providers", "Zkontrolovat AI poskytovatele"),
        ]

        embed.add_field(
            name="🔹 Správa serveru (vyžaduje 'Manage Server')",
            value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in server_commands]),
            inline=False
        )

        embed.set_footer(text="Pro více informací o příkazu použijte !help <příkaz>")

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        """
        Handle command errors.

        Args:
            ctx: Command context
            error: The error that occurred
        """
        # This is already handled in the main bot class,
        # but we can add cog-specific error handling here if needed
        pass


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.

    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(AdminCog(bot))
    logger.info("Admin cog added to bot")
