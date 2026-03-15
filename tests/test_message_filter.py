"""
Tests for message interest detection and filtering.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
import discord

from bot.utils.message_filter import MessageFilter, MessageScore


class TestMessageFilter:
    """Test suite for message interest detection."""

    @pytest.fixture
    def message_filter(self):
        """Create a message filter instance."""
        return MessageFilter(
            bot_id=123456789,
            response_threshold=0.6,
            max_responses_per_minute=5,
        )

    @pytest.fixture
    def mock_message(self):
        """Create a mock Discord message."""
        message = Mock(spec=discord.Message)
        message.author = Mock(spec=discord.User)
        message.author.bot = False
        message.author.id = 999999999
        message.author.name = "TestUser"
        message.channel = Mock()
        message.channel.id = 111111111
        message.channel.name = "general"
        message.guild = Mock()
        message.guild.name = "TestGuild"
        message.type = discord.MessageType.default
        message.mentions = []
        message.reference = None
        message.created_at = datetime.now()
        return message

    @pytest.mark.asyncio
    async def test_detects_mentions(self, message_filter, mock_message):
        """Bot should always respond when mentioned."""
        mock_message.content = "<@123456789> Ahoj!"
        mock_mention = Mock()
        mock_mention.id = 123456789
        mock_message.mentions = [mock_mention]

        should_respond, score = await message_filter.is_interesting(mock_message)

        assert should_respond is True
        assert score.is_mention is True
        assert score.total == 1.0

    @pytest.mark.asyncio
    async def test_detects_czech_questions(self, message_filter, mock_message):
        """Bot should detect Czech questions."""
        test_questions = [
            "Jak se máš?",
            "Co si myslíš o AI?",
            "Kdy to bude hotové?",
            "Kde to najdu?",
            "Proč to nefunguje?",
        ]

        for question in test_questions:
            mock_message.content = question
            should_respond, score = await message_filter.is_interesting(mock_message)

            assert score.is_question is True, f"Failed to detect question: {question}"
            # Questions should score high enough to respond
            assert score.total >= 0.3, f"Question scored too low: {question}"

    @pytest.mark.asyncio
    async def test_detects_english_questions(self, message_filter, mock_message):
        """Bot should detect English questions."""
        test_questions = [
            "How are you?",
            "What do you think about AI?",
            "When will it be ready?",
            "Where can I find it?",
            "Why doesn't it work?",
        ]

        for question in test_questions:
            mock_message.content = question
            should_respond, score = await message_filter.is_interesting(mock_message)

            assert score.is_question is True, f"Failed to detect question: {question}"

    @pytest.mark.asyncio
    async def test_detects_conversation_starters(self, message_filter, mock_message):
        """Bot should detect conversation starters."""
        test_cases = [
            "Co si myslíš o programování?",
            "Slyšel jsi o tom novém frameworku?",
            "Víš něco o Pythonu?",
            "Mám otázku ohledně AI",
        ]

        for content in test_cases:
            mock_message.content = content
            should_respond, score = await message_filter.is_interesting(mock_message)

            assert score.total > 0.3, f"Failed to score starter: {content}"

    @pytest.mark.asyncio
    async def test_detects_interesting_keywords(self, message_filter, mock_message):
        """Bot should detect interesting keywords."""
        test_cases = [
            "Mám problém s Python kódem",
            "Tento AI model je zajímavý",
            "Potřebuji pomoc s algoritmem",
            "Je to nějaká chyba v programování?",
        ]

        for content in test_cases:
            mock_message.content = content
            should_respond, score = await message_filter.is_interesting(mock_message)

            assert score.has_keywords is True, f"Failed to detect keywords: {content}"
            assert score.total > 0.2, f"Keywords scored too low: {content}"

    @pytest.mark.asyncio
    async def test_ignores_bot_messages(self, message_filter, mock_message):
        """Bot should ignore messages from other bots."""
        mock_message.author.bot = True
        mock_message.content = "This is a very interesting question about AI!"

        should_respond, score = await message_filter.is_interesting(mock_message)

        assert should_respond is False
        assert score.total == 0.0

    @pytest.mark.asyncio
    async def test_ignores_short_messages(self, message_filter, mock_message):
        """Bot should ignore very short non-meaningful messages."""
        short_messages = ["ok", "lol", "xd", "👍", "k", "nice"]

        for content in short_messages:
            mock_message.content = content
            should_respond, score = await message_filter.is_interesting(mock_message)

            assert should_respond is False, f"Should ignore: {content}"

    @pytest.mark.asyncio
    async def test_ignores_spam(self, message_filter, mock_message):
        """Bot should detect and ignore spam patterns."""
        spam_messages = [
            "aaaaaaaaaaaaaaaa",
            "!!!!!!!!!!",
            "THIS IS ALL CAPS SPAM MESSAGE",
            "😂😂😂😂😂",
        ]

        for content in spam_messages:
            mock_message.content = content
            should_respond, score = await message_filter.is_interesting(mock_message)

            assert score.spam_penalty > 0, f"Failed to detect spam: {content}"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, message_filter, mock_message):
        """Bot should implement rate limiting."""
        mock_message.content = "This is an interesting question about programming?"

        # First few messages should pass
        results = []
        for i in range(10):
            should_respond, score = await message_filter.is_interesting(mock_message)
            results.append(should_respond)

        # Should have some rate limiting applied
        responded_count = sum(results)
        assert responded_count <= message_filter.max_responses_per_minute

    @pytest.mark.asyncio
    async def test_context_awareness_reply(self, message_filter, mock_message):
        """Bot should recognize when someone replies to it."""
        # Create a bot message
        bot_message = Mock(spec=discord.Message)
        bot_message.id = 555555555
        bot_message.author = Mock()
        bot_message.author.id = 123456789  # Bot's ID
        bot_message.created_at = datetime.now() - timedelta(seconds=30)

        # User replies to bot
        mock_message.content = "That's interesting!"
        mock_message.reference = Mock()
        mock_message.reference.message_id = 555555555

        context_messages = [bot_message, mock_message]

        should_respond, score = await message_filter.is_interesting(
            mock_message,
            context_messages=context_messages
        )

        assert score.conversation_context > 0, "Should detect reply to bot"

    @pytest.mark.asyncio
    async def test_message_length_scoring(self, message_filter, mock_message):
        """Bot should score messages based on appropriate length."""
        # Too short
        mock_message.content = "hi"
        _, score_short = await message_filter.is_interesting(mock_message)

        # Good length
        mock_message.content = "This is a well-formed question about programming concepts"
        _, score_good = await message_filter.is_interesting(mock_message)

        # Very long
        mock_message.content = " ".join(["word"] * 200)
        _, score_long = await message_filter.is_interesting(mock_message)

        assert score_good.length_score > score_short.length_score
        assert score_good.length_score > score_long.length_score

    @pytest.mark.asyncio
    async def test_sentiment_analysis(self, message_filter, mock_message):
        """Bot should analyze basic sentiment."""
        # Positive message
        mock_message.content = "This is great! Really awesome and interesting!"
        _, score_positive = await message_filter.is_interesting(mock_message)

        # Negative message
        mock_message.content = "This is terrible and broken, doesn't work at all"
        _, score_negative = await message_filter.is_interesting(mock_message)

        # Sentiment should be detected
        assert score_positive.sentiment_score > 0
        assert score_negative.sentiment_score < 0

    @pytest.mark.asyncio
    async def test_configuration_update(self, message_filter):
        """Should allow dynamic configuration updates."""
        original_threshold = message_filter.response_threshold

        message_filter.update_configuration(response_threshold=0.8)
        assert message_filter.response_threshold == 0.8

        message_filter.update_configuration(max_responses_per_minute=10)
        assert message_filter.max_responses_per_minute == 10

        message_filter.update_configuration(enable_ai_scoring=True)
        assert message_filter.enable_ai_scoring is True

    @pytest.mark.asyncio
    async def test_get_statistics(self, message_filter):
        """Should return current statistics."""
        stats = message_filter.get_statistics()

        assert 'response_threshold' in stats
        assert 'max_responses_per_minute' in stats
        assert 'enable_ai_scoring' in stats
        assert 'recent_responses_total' in stats
        assert 'active_channels' in stats

    @pytest.mark.asyncio
    async def test_combined_high_score(self, message_filter, mock_message):
        """Message with multiple interest indicators should score high."""
        mock_message.content = "Co si myslíš o AI a programování? Mám zajímavou otázku."

        should_respond, score = await message_filter.is_interesting(mock_message)

        # Should have multiple positive indicators
        assert score.is_question is True
        assert score.has_keywords is True
        assert score.total >= message_filter.response_threshold

    @pytest.mark.asyncio
    async def test_threshold_boundary(self, message_filter, mock_message):
        """Test behavior at threshold boundary."""
        # Set threshold
        message_filter.update_configuration(response_threshold=0.5)

        # Create message that scores around threshold
        mock_message.content = "Maybe we could discuss this topic?"

        should_respond, score = await message_filter.is_interesting(mock_message)

        # Response should match threshold
        assert should_respond == (score.total >= 0.5)


class TestMessageScore:
    """Test suite for MessageScore dataclass."""

    def test_message_score_creation(self):
        """Should create MessageScore with all fields."""
        score = MessageScore(
            total=0.75,
            is_mention=True,
            is_question=False,
            has_keywords=True,
            conversation_context=0.5,
            sentiment_score=0.2,
            length_score=0.4,
            spam_penalty=0.0,
        )

        assert score.total == 0.75
        assert score.is_mention is True
        assert score.has_keywords is True
        assert score.details == {}

    def test_message_score_with_details(self):
        """Should store additional details."""
        details = {'reason': 'high_confidence', 'keywords': ['ai', 'python']}
        score = MessageScore(
            total=0.8,
            details=details
        )

        assert score.details == details
