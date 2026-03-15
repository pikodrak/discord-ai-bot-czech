"""
Pytest configuration and shared fixtures.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import discord


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_discord_message():
    """Create a mock Discord message for testing."""
    message = Mock(spec=discord.Message)
    message.author = Mock(spec=discord.User)
    message.author.bot = False
    message.author.name = "TestUser"
    message.author.id = 123456789
    message.channel = Mock(spec=discord.TextChannel)
    message.channel.name = "general"
    message.channel.id = 987654321
    message.guild = Mock(spec=discord.Guild)
    message.guild.name = "TestGuild"
    message.guild.id = 111222333
    message.content = ""
    message.mentions = []
    message.created_at = None
    return message


@pytest.fixture
def mock_discord_client():
    """Create a mock Discord client."""
    client = AsyncMock(spec=discord.Client)
    client.user = Mock()
    client.user.id = 999888777
    client.user.name = "TestBot"
    return client


@pytest.fixture
def sample_czech_messages():
    """Sample Czech messages for testing."""
    return [
        "Ahoj, jak se máš?",
        "Co si myslíš o programování v Pythonu?",
        "Víš něco o umělé inteligenci?",
        "Jaký je tvůj oblíbený film?",
        "Pomůžeš mi s problémem?",
        "To je zajímavé!",
        "Souhlasím s tebou",
        "Myslím, že máš pravdu",
    ]


@pytest.fixture
def mock_api_response():
    """Mock API response structure."""
    return {
        "claude": {
            "response": "Response from Claude API",
            "status": "success"
        },
        "gemini": {
            "response": "Response from Gemini API",
            "status": "success"
        },
        "openai": {
            "response": "Response from OpenAI API",
            "status": "success"
        }
    }


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "discord_token": "test_discord_token",
        "channels": ["general", "tech-talk"],
        "api_keys": {
            "claude": "test_claude_key",
            "gemini": "test_gemini_key",
            "openai": "test_openai_key"
        },
        "admin": {
            "username": "admin",
            "password": "test_password"
        },
        "bot": {
            "interest_threshold": 0.7,
            "rate_limit": 5,
            "response_timeout": 30
        }
    }


@pytest.fixture
async def mock_bot():
    """Create a mock bot instance."""
    # This will be implemented when bot class is created
    # from src.bot import DiscordBot
    # bot = DiscordBot()
    # return bot
    pass


@pytest.fixture
def admin_token():
    """Generate a test admin authentication token."""
    return "test_jwt_token_12345"


# Marker for tests that require Discord connection
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "requires_discord: mark test as requiring Discord connection"
    )
    config.addinivalue_line(
        "markers", "requires_api: mark test as requiring API keys"
    )
