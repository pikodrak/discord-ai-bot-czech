"""
Tests for Discord Bot Core Functionality

Tests for context management, interest filtering, and message handling.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import discord

from bot.context_manager import ContextManager, MessageContext, ConversationWindow
from bot.interest_filter import InterestFilter


class TestContextManager:
    """Tests for ContextManager class."""

    def test_create_window(self):
        """Test creating a new conversation window."""
        manager = ContextManager(max_messages_per_channel=50)
        window = manager.get_or_create_window(12345)

        assert isinstance(window, ConversationWindow)
        assert window.channel_id == 12345
        assert window.max_messages == 50

    def test_add_message(self):
        """Test adding messages to context."""
        manager = ContextManager()

        # Create mock Discord message
        mock_message = Mock(spec=discord.Message)
        mock_message.author.id = 123
        mock_message.author.display_name = "TestUser"
        mock_message.author.bot = False
        mock_message.content = "Hello, world!"
        mock_message.created_at = datetime.now()

        manager.add_message(12345, mock_message)

        messages = manager.get_context_messages(12345)
        assert len(messages) == 1
        assert messages[0].content == "Hello, world!"
        assert messages[0].author_name == "TestUser"

    def test_max_messages_limit(self):
        """Test that messages are trimmed when exceeding max."""
        manager = ContextManager(max_messages_per_channel=5)

        # Add 10 messages
        for i in range(10):
            mock_message = Mock(spec=discord.Message)
            mock_message.author.id = 123
            mock_message.author.display_name = "TestUser"
            mock_message.author.bot = False
            mock_message.content = f"Message {i}"
            mock_message.created_at = datetime.now()

            manager.add_message(12345, mock_message)

        messages = manager.get_context_messages(12345)

        # Should only keep last 5 messages
        assert len(messages) == 5
        assert messages[0].content == "Message 5"
        assert messages[-1].content == "Message 9"

    def test_format_for_llm(self):
        """Test formatting messages for LLM."""
        manager = ContextManager()

        # Add user message
        user_msg = Mock(spec=discord.Message)
        user_msg.author.id = 123
        user_msg.author.display_name = "User"
        user_msg.author.bot = False
        user_msg.content = "Hello bot"
        user_msg.created_at = datetime.now()

        # Add bot message
        bot_msg = Mock(spec=discord.Message)
        bot_msg.author.id = 456
        bot_msg.author.display_name = "Bot"
        bot_msg.author.bot = True
        bot_msg.content = "Hello user"
        bot_msg.created_at = datetime.now()

        manager.add_message(12345, user_msg)
        manager.add_message(12345, bot_msg)

        llm_messages = manager.format_for_llm(12345)

        assert len(llm_messages) == 2
        assert llm_messages[0]["role"] == "user"
        assert "User" in llm_messages[0]["content"]
        assert llm_messages[1]["role"] == "assistant"
        assert llm_messages[1]["content"] == "Hello user"

    def test_clear_channel(self):
        """Test clearing channel context."""
        manager = ContextManager()

        mock_message = Mock(spec=discord.Message)
        mock_message.author.id = 123
        mock_message.author.display_name = "TestUser"
        mock_message.author.bot = False
        mock_message.content = "Test"
        mock_message.created_at = datetime.now()

        manager.add_message(12345, mock_message)
        assert len(manager.get_context_messages(12345)) == 1

        manager.clear_channel(12345)
        assert len(manager.get_context_messages(12345)) == 0

    def test_get_stats(self):
        """Test getting context statistics."""
        manager = ContextManager()

        mock_message = Mock(spec=discord.Message)
        mock_message.author.id = 123
        mock_message.author.display_name = "TestUser"
        mock_message.author.bot = False
        mock_message.content = "Test"
        mock_message.created_at = datetime.now()

        manager.add_message(12345, mock_message)
        manager.add_message(67890, mock_message)

        stats = manager.get_stats()

        assert stats["total_windows"] == 2
        assert stats["total_messages"] == 2
        assert 12345 in stats["windows"]
        assert 67890 in stats["windows"]


class TestInterestFilter:
    """Tests for InterestFilter class."""

    def test_direct_mention(self):
        """Test response to direct mention."""
        filter = InterestFilter(bot_user_id=456, response_threshold=0.6)

        # Create mock message with bot mention
        mock_message = Mock(spec=discord.Message)
        mock_message.author.bot = False
        mock_message.author.id = 123
        mock_message.content = "Hey <@456> how are you?"
        mock_message.channel = Mock(spec=discord.TextChannel)

        # Create mock mention
        bot_user = Mock()
        bot_user.id = 456
        mock_message.mentions = [bot_user]

        should_respond, score, reason = filter.should_respond(mock_message)

        assert should_respond is True
        assert score >= 0.5
        assert "mentioned" in reason

    def test_reply_to_bot(self):
        """Test response to reply to bot's message."""
        filter = InterestFilter(bot_user_id=456, response_threshold=0.6)

        mock_message = Mock(spec=discord.Message)
        mock_message.author.bot = False
        mock_message.author.id = 123
        mock_message.content = "Thanks!"
        mock_message.channel = Mock(spec=discord.TextChannel)
        mock_message.mentions = []

        should_respond, score, reason = filter.should_respond(
            mock_message,
            is_reply_to_bot=True
        )

        assert should_respond is True
        assert score >= 0.4
        assert "reply_to_bot" in reason

    def test_question_detection(self):
        """Test detection of questions."""
        filter = InterestFilter(bot_user_id=456, response_threshold=0.3)

        mock_message = Mock(spec=discord.Message)
        mock_message.author.bot = False
        mock_message.author.id = 123
        mock_message.content = "Jak se máš?"
        mock_message.channel = Mock(spec=discord.TextChannel)
        mock_message.mentions = []

        should_respond, score, reason = filter.should_respond(mock_message)

        assert "question" in reason
        assert score > 0

    def test_keyword_matching(self):
        """Test keyword matching."""
        filter = InterestFilter(
            bot_user_id=456,
            response_threshold=0.3,
            keywords=["test", "custom"]
        )

        mock_message = Mock(spec=discord.Message)
        mock_message.author.bot = False
        mock_message.author.id = 123
        mock_message.content = "This is a custom keyword test"
        mock_message.channel = Mock(spec=discord.TextChannel)
        mock_message.mentions = []

        should_respond, score, reason = filter.should_respond(mock_message)

        assert "keywords" in reason
        assert score > 0

    def test_dm_always_respond(self):
        """Test always responding in DMs."""
        filter = InterestFilter(
            bot_user_id=456,
            always_respond_in_dms=True
        )

        mock_message = Mock(spec=discord.Message)
        mock_message.author.bot = False
        mock_message.author.id = 123
        mock_message.content = "Hello"
        mock_message.channel = Mock(spec=discord.DMChannel)
        mock_message.mentions = []

        should_respond, score, reason = filter.should_respond(mock_message)

        assert should_respond is True
        assert score == 1.0
        assert reason == "direct_message"

    def test_ignore_own_messages(self):
        """Test ignoring bot's own messages."""
        filter = InterestFilter(bot_user_id=456)

        mock_message = Mock(spec=discord.Message)
        mock_message.author.bot = True
        mock_message.author.id = 456
        mock_message.content = "I am the bot"
        mock_message.channel = Mock(spec=discord.TextChannel)

        should_respond, score, reason = filter.should_respond(mock_message)

        assert should_respond is False
        assert reason == "own_message"

    def test_threshold_setting(self):
        """Test changing response threshold."""
        filter = InterestFilter(response_threshold=0.5)

        assert filter.response_threshold == 0.5

        filter.set_threshold(0.8)
        assert filter.response_threshold == 0.8

        with pytest.raises(ValueError):
            filter.set_threshold(1.5)

        with pytest.raises(ValueError):
            filter.set_threshold(-0.1)

    def test_keyword_management(self):
        """Test adding and removing keywords."""
        filter = InterestFilter()

        # Add keyword
        filter.add_keyword("test")
        assert "test" in filter.get_keywords()

        # Remove keyword
        result = filter.remove_keyword("test")
        assert result is True
        assert "test" not in filter.get_keywords()

        # Try to remove non-existent keyword
        result = filter.remove_keyword("nonexistent")
        assert result is False


class TestMessageContext:
    """Tests for MessageContext dataclass."""

    def test_create_message_context(self):
        """Test creating a message context."""
        ctx = MessageContext(
            author_id=123,
            author_name="TestUser",
            content="Hello",
            timestamp=datetime.now(),
            is_bot=False,
            channel_id=456
        )

        assert ctx.author_id == 123
        assert ctx.author_name == "TestUser"
        assert ctx.content == "Hello"
        assert ctx.is_bot is False
        assert ctx.channel_id == 456


class TestConversationWindow:
    """Tests for ConversationWindow class."""

    def test_add_and_retrieve_messages(self):
        """Test adding and retrieving messages."""
        window = ConversationWindow(channel_id=123, max_messages=10)

        msg = MessageContext(
            author_id=1,
            author_name="User",
            content="Test",
            timestamp=datetime.now()
        )

        window.add_message(msg)
        messages = window.get_messages()

        assert len(messages) == 1
        assert messages[0].content == "Test"

    def test_message_limit(self):
        """Test message limit enforcement."""
        window = ConversationWindow(channel_id=123, max_messages=3)

        for i in range(5):
            msg = MessageContext(
                author_id=1,
                author_name="User",
                content=f"Message {i}",
                timestamp=datetime.now()
            )
            window.add_message(msg)

        messages = window.get_messages()

        assert len(messages) == 3
        assert messages[0].content == "Message 2"
        assert messages[-1].content == "Message 4"

    def test_get_summary(self):
        """Test getting window summary."""
        window = ConversationWindow(channel_id=123)

        msg1 = MessageContext(1, "User1", "Hello", datetime.now())
        msg2 = MessageContext(2, "User2", "Hi", datetime.now())

        window.add_message(msg1)
        window.add_message(msg2)

        summary = window.get_summary()

        assert summary["channel_id"] == 123
        assert summary["message_count"] == 2
        assert summary["user_count"] == 2

    def test_clear_messages(self):
        """Test clearing all messages."""
        window = ConversationWindow(channel_id=123)

        msg = MessageContext(1, "User", "Test", datetime.now())
        window.add_message(msg)

        assert len(window.get_messages()) == 1

        window.clear()

        assert len(window.get_messages()) == 0
