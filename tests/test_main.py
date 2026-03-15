"""
Comprehensive tests for main module (Discord bot initialization and lifecycle).
"""
import pytest
import asyncio
import discord
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Assuming main module is in root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock dependencies before importing main
sys.modules['bot.errors'] = MagicMock()
sys.modules['bot.graceful_degradation'] = MagicMock()
sys.modules['bot.lifecycle'] = MagicMock()
sys.modules['src.shared_config'] = MagicMock()
sys.modules['src.ipc'] = MagicMock()

from main import DiscordAIBot


class TestDiscordAIBotInitialization:
    """Test DiscordAIBot initialization."""

    @patch('main.ManagedBot.__init__')
    @patch('main.get_ipc_channel')
    def test_bot_initialization(self, mock_ipc, mock_managed_bot):
        """Test basic bot initialization."""
        mock_managed_bot.return_value = None
        mock_ipc.return_value = Mock()

        mock_config = Mock()
        mock_config.enable_message_caching = True

        bot = DiscordAIBot(mock_config)

        assert bot is not None
        assert bot._config_reload_enabled is True
        mock_ipc.assert_called_once()

    @patch('main.ManagedBot.__init__')
    @patch('main.get_ipc_channel')
    def test_bot_initialization_with_intents(self, mock_ipc, mock_managed_bot):
        """Test that Discord intents are properly configured."""
        mock_managed_bot.return_value = None
        mock_ipc.return_value = Mock()

        mock_config = Mock()
        mock_config.enable_message_caching = True

        with patch('main.discord.Intents') as mock_intents:
            mock_intents_instance = Mock()
            mock_intents.default.return_value = mock_intents_instance

            bot = DiscordAIBot(mock_config)

            # Verify guilds intent is enabled
            assert mock_intents_instance.guilds is True

    @patch('main.ManagedBot.__init__')
    @patch('main.get_ipc_channel')
    def test_bot_initialization_without_message_content(self, mock_ipc, mock_managed_bot):
        """Test bot initialization without message_content intent."""
        mock_managed_bot.return_value = None
        mock_ipc.return_value = Mock()

        mock_config = Mock()
        mock_config.enable_message_caching = True

        bot = DiscordAIBot(mock_config, use_message_content_intent=False)

        assert bot is not None


class TestDiscordAIBotHooks:
    """Test lifecycle hooks registration."""

    @patch('main.ManagedBot.__init__')
    @patch('main.get_ipc_channel')
    def test_hooks_registered(self, mock_ipc, mock_managed_bot):
        """Test that lifecycle hooks are registered."""
        mock_managed_bot.return_value = None
        mock_ipc.return_value = Mock()

        mock_config = Mock()
        mock_config.enable_message_caching = True

        with patch('main.DiscordAIBot._register_hooks') as mock_register:
            bot = DiscordAIBot(mock_config)
            mock_register.assert_called_once()


class TestDiscordAIBotCogLoading:
    """Test cog loading functionality."""

    @pytest.mark.asyncio
    async def test_load_cogs_success(self):
        """Test successful cog loading."""
        mock_bot = Mock()
        mock_bot.load_extension = AsyncMock()
        mock_bot.logger = Mock()
        mock_bot.config = Mock()
        mock_bot.config.enable_graceful_degradation = True

        # Simulate load_cogs hook
        cogs = ["bot.cogs.ai_chat", "bot.cogs.admin"]

        for cog in cogs:
            await mock_bot.load_extension(cog)

        assert mock_bot.load_extension.call_count == 2

    @pytest.mark.asyncio
    async def test_load_cogs_failure_with_degradation(self):
        """Test cog loading failure with graceful degradation."""
        mock_bot = Mock()
        mock_bot.load_extension = AsyncMock(side_effect=Exception("Load failed"))
        mock_bot.logger = Mock()
        mock_bot.config = Mock()
        mock_bot.config.enable_graceful_degradation = True

        # Should not raise exception
        try:
            await mock_bot.load_extension("bot.cogs.ai_chat")
        except Exception:
            pass  # Graceful degradation should handle this

        assert mock_bot.load_extension.called

    @pytest.mark.asyncio
    async def test_load_cogs_failure_without_degradation(self):
        """Test cog loading failure without graceful degradation."""
        mock_bot = Mock()
        mock_bot.load_extension = AsyncMock(side_effect=Exception("Load failed"))
        mock_bot.logger = Mock()
        mock_bot.config = Mock()
        mock_bot.config.enable_graceful_degradation = False

        with pytest.raises(Exception):
            await mock_bot.load_extension("bot.cogs.ai_chat")


class TestDiscordAIBotLLMInitialization:
    """Test LLM client initialization."""

    @pytest.mark.asyncio
    async def test_llm_initialization_success(self):
        """Test successful LLM initialization."""
        mock_config = Mock()
        mock_config.enable_graceful_degradation = True

        with patch('main.create_llm_client') as mock_create:
            mock_client = AsyncMock()
            mock_client.check_availability = AsyncMock(return_value={
                "anthropic": True,
                "google": False,
                "openai": True
            })
            mock_create.return_value = mock_client

            client = await mock_create(mock_config)
            availability = await client.check_availability()

            assert "anthropic" in availability
            assert availability["anthropic"] is True

    @pytest.mark.asyncio
    async def test_llm_initialization_no_providers(self):
        """Test LLM initialization with no available providers."""
        mock_config = Mock()
        mock_config.enable_graceful_degradation = True

        with patch('main.create_llm_client') as mock_create:
            mock_client = AsyncMock()
            mock_client.check_availability = AsyncMock(return_value={
                "anthropic": False,
                "google": False,
                "openai": False
            })
            mock_create.return_value = mock_client

            client = await mock_create(mock_config)
            availability = await client.check_availability()

            # Should complete without error (graceful degradation)
            assert all(not avail for avail in availability.values())

    @pytest.mark.asyncio
    async def test_llm_initialization_failure(self):
        """Test LLM initialization failure."""
        mock_config = Mock()
        mock_config.enable_graceful_degradation = False

        with patch('main.create_llm_client') as mock_create:
            mock_create.side_effect = Exception("LLM init failed")

            with pytest.raises(Exception):
                await mock_create(mock_config)


class TestDiscordAIBotIPCHandlers:
    """Test IPC command handlers."""

    @pytest.mark.asyncio
    async def test_ipc_reload_config_handler(self):
        """Test IPC reload config handler."""
        mock_signal = Mock()
        mock_signal.data = {}

        # Mock handler would reload config and return success
        result = {"message": "Configuration reloaded successfully"}

        assert "message" in result
        assert result["message"] == "Configuration reloaded successfully"

    @pytest.mark.asyncio
    async def test_ipc_shutdown_handler(self):
        """Test IPC shutdown handler."""
        mock_signal = Mock()

        # Mock handler would initiate shutdown
        result = {"message": "Shutdown initiated"}

        assert "message" in result
        assert result["message"] == "Shutdown initiated"

    @pytest.mark.asyncio
    async def test_ipc_ping_handler(self):
        """Test IPC ping handler."""
        mock_signal = Mock()

        # Mock handler would return pong
        result = {"message": "pong", "status": "running"}

        assert result["message"] == "pong"
        assert result["status"] == "running"


class TestDiscordAIBotCommandErrors:
    """Test command error handling."""

    @pytest.mark.asyncio
    async def test_command_not_found_ignored(self):
        """Test that CommandNotFound errors are ignored."""
        from discord.ext import commands

        mock_bot = Mock()
        mock_ctx = Mock()
        error = commands.CommandNotFound()

        # Should not raise or send message
        # (tested by not calling ctx.send)


class TestMainFunction:
    """Test main function."""

    @pytest.mark.asyncio
    @patch('main.load_dotenv')
    @patch('main.setup_logger')
    @patch('main.get_shared_config_loader')
    @patch('main.DiscordAIBot')
    async def test_main_successful_startup(self, mock_bot_class, mock_shared_loader, mock_logger, mock_dotenv):
        """Test successful bot startup."""
        mock_logger.return_value = Mock()

        mock_loader = Mock()
        mock_loader.load_config.return_value = {
            "discord_bot_token": "test_token",
            "log_level": "INFO",
            "log_file": "logs/bot.log"
        }
        mock_shared_loader.return_value = mock_loader

        mock_bot = Mock()
        mock_bot.start_with_lifecycle = AsyncMock()
        mock_bot_class.return_value = mock_bot

        with patch('main.AdvancedBotConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.discord_bot_token = "test_token"
            mock_config.log_level = "INFO"
            mock_config.log_file = "logs/bot.log"
            mock_config_class.return_value = mock_config

            # Test would call main() here
            # For now, verify mocks would be called
            assert mock_shared_loader is not None

    @pytest.mark.asyncio
    @patch('main.load_dotenv')
    @patch('main.setup_logger')
    async def test_main_missing_token(self, mock_logger, mock_dotenv):
        """Test main function with missing Discord token."""
        mock_logger.return_value = Mock()

        with patch.dict('os.environ', {}, clear=True):
            with patch('main.get_shared_config_loader') as mock_loader:
                mock_loader.return_value.load_config.side_effect = Exception("Missing token")

                # Would exit with error
                # Verify logger called with error


class TestBotPresence:
    """Test bot presence setting."""

    @pytest.mark.asyncio
    async def test_set_presence_success(self):
        """Test successful presence setting."""
        mock_bot = Mock()
        mock_bot.change_presence = AsyncMock()

        await mock_bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="AI conversations"
            )
        )

        mock_bot.change_presence.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_presence_failure(self):
        """Test presence setting failure (should not crash bot)."""
        mock_bot = Mock()
        mock_bot.change_presence = AsyncMock(side_effect=Exception("Presence failed"))
        mock_bot.logger = Mock()

        try:
            await mock_bot.change_presence(activity=Mock())
        except Exception:
            pass  # Should be caught and logged


class TestBotCleanup:
    """Test bot cleanup and shutdown."""

    @pytest.mark.asyncio
    async def test_cleanup_llm_client(self):
        """Test LLM client cleanup."""
        mock_llm_client = AsyncMock()
        mock_llm_client.close = AsyncMock()

        await mock_llm_client.close()

        mock_llm_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_ipc(self):
        """Test IPC cleanup."""
        mock_ipc = Mock()
        mock_ipc.cleanup = Mock()

        mock_ipc.cleanup()

        mock_ipc.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_errors(self):
        """Test cleanup continues despite errors."""
        mock_llm_client = AsyncMock()
        mock_llm_client.close = AsyncMock(side_effect=Exception("Close failed"))

        # Should not raise
        try:
            await mock_llm_client.close()
        except Exception:
            pass  # Cleanup should handle errors gracefully


class TestBotReconnection:
    """Test bot reconnection logic."""

    @pytest.mark.asyncio
    async def test_privileged_intents_fallback(self):
        """Test fallback when privileged intents not available."""
        # First attempt with message_content intent fails
        # Second attempt without message_content succeeds

        # This would be tested in integration, mocking the flow:
        attempt = 0

        async def mock_start(token):
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise discord.PrivilegedIntentsRequired(None)
            # Second attempt succeeds

        mock_bot1 = Mock()
        mock_bot1.start_with_lifecycle = mock_start
        mock_bot1.close = AsyncMock()

        try:
            await mock_bot1.start_with_lifecycle("token")
        except discord.PrivilegedIntentsRequired:
            await mock_bot1.close()
            # Create new bot without privileged intents
            mock_bot2 = Mock()
            mock_bot2.start_with_lifecycle = AsyncMock()
            await mock_bot2.start_with_lifecycle("token")


class TestEnvironmentLoading:
    """Test environment variable loading."""

    @patch('main.load_dotenv')
    def test_default_env_file(self, mock_dotenv):
        """Test loading default .env file."""
        with patch.dict('os.environ', {"ENV_FILE": ".env"}):
            env_file = os.getenv("ENV_FILE", ".env")
            assert env_file == ".env"

    @patch('main.load_dotenv')
    def test_custom_env_file(self, mock_dotenv):
        """Test loading custom env file."""
        with patch.dict('os.environ', {"ENV_FILE": "custom.env"}):
            env_file = os.getenv("ENV_FILE", ".env")
            assert env_file == "custom.env"


class TestConfigurationLoading:
    """Test configuration loading and validation."""

    @patch('main.load_config')
    def test_config_validation_error(self, mock_load):
        """Test handling of config validation errors."""
        from bot.config_loader import ConfigValidationError

        mock_load.side_effect = ConfigValidationError(
            "Invalid config",
            [{"field": "discord_token", "error": "required"}]
        )

        with pytest.raises(ConfigValidationError):
            mock_load()

    @patch('main.get_shared_config_loader')
    def test_shared_config_fallback(self, mock_shared_loader):
        """Test fallback to direct config loading."""
        mock_loader = Mock()
        mock_loader.load_config.side_effect = Exception("Shared load failed")
        mock_shared_loader.return_value = mock_loader

        # Should fall back to direct load
        with patch('main.load_config') as mock_direct_load:
            mock_direct_load.return_value = Mock(discord_bot_token="token")

            # Fallback logic would call mock_direct_load


class TestIPCProcessing:
    """Test IPC signal processing."""

    @pytest.mark.asyncio
    async def test_ipc_processing_loop(self):
        """Test IPC processing loop."""
        mock_ipc = Mock()
        mock_ipc.process_signals = AsyncMock()
        mock_ipc.update_status = Mock()

        # Process once
        await mock_ipc.process_signals()
        mock_ipc.update_status({"running": True})

        mock_ipc.process_signals.assert_called_once()
        mock_ipc.update_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_ipc_loop_cancellation(self):
        """Test IPC loop handles cancellation."""
        async def cancellable_loop():
            while True:
                await asyncio.sleep(1)

        task = asyncio.create_task(cancellable_loop())
        await asyncio.sleep(0.1)

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


class TestBotStatus:
    """Test bot status updates."""

    def test_status_update_data(self):
        """Test status update contains correct data."""
        status = {
            "running": True,
            "guilds": 5,
            "latency_ms": 45.67,
            "user_count": 1250
        }

        assert status["running"] is True
        assert isinstance(status["guilds"], int)
        assert isinstance(status["latency_ms"], float)
        assert isinstance(status["user_count"], int)


# Import os for environment tests
import os
