"""
Example usage of MessageFilter for Discord bot message interest detection.

This example demonstrates how to use the MessageFilter to determine
if messages are interesting enough to respond to.
"""

import asyncio
import logging
from unittest.mock import Mock
import discord

from bot.utils.message_filter import MessageFilter, MessageScore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_mock_message(content: str, author_id: int = 999999999, bot_id: int = 123456789) -> Mock:
    """
    Create a mock Discord message for testing.

    Args:
        content: Message content
        author_id: Author's user ID
        bot_id: Bot's user ID (for mentions)

    Returns:
        Mock Discord message
    """
    message = Mock(spec=discord.Message)
    message.content = content
    message.author = Mock(spec=discord.User)
    message.author.bot = False
    message.author.id = author_id
    message.author.name = "TestUser"
    message.channel = Mock()
    message.channel.id = 111111111
    message.channel.name = "general"
    message.guild = Mock()
    message.guild.name = "TestGuild"
    message.type = discord.MessageType.default
    message.mentions = []
    message.reference = None

    return message


async def example_basic_usage():
    """Demonstrate basic message filtering."""
    logger.info("=== Basic Message Filter Usage ===\n")

    # Initialize filter with bot ID and threshold
    message_filter = MessageFilter(
        bot_id=123456789,
        response_threshold=0.6,  # 60% confidence to respond
        max_responses_per_minute=5,
    )

    # Test various message types
    test_messages = [
        "Jak se máš?",  # Czech question
        "What is AI?",  # English question
        "ok",  # Short, should ignore
        "Co si myslíš o programování v Pythonu?",  # Question with keywords
        "aaaaaaaaaaaaa",  # Spam
        "Mám zajímavou otázku o AI algoritmech",  # Keywords + starter
    ]

    for content in test_messages:
        message = create_mock_message(content)
        should_respond, score = await message_filter.is_interesting(message)

        logger.info(f"Message: '{content}'")
        logger.info(f"Should respond: {should_respond}")
        logger.info(f"Score: {score.total:.2f}")
        logger.info(f"  - Is question: {score.is_question}")
        logger.info(f"  - Has keywords: {score.has_keywords}")
        logger.info(f"  - Spam penalty: {score.spam_penalty}")
        logger.info("")


async def example_mention_detection():
    """Demonstrate mention detection."""
    logger.info("=== Mention Detection ===\n")

    message_filter = MessageFilter(bot_id=123456789, response_threshold=0.6)

    # Create message with mention
    message = create_mock_message("Hey bot, help me!")
    mock_mention = Mock()
    mock_mention.id = 123456789
    message.mentions = [mock_mention]

    should_respond, score = await message_filter.is_interesting(message)

    logger.info("Message with mention: 'Hey bot, help me!'")
    logger.info(f"Should respond: {should_respond}")
    logger.info(f"Score: {score.total:.2f}")
    logger.info(f"Is mention: {score.is_mention}")
    logger.info("")


async def example_configuration_update():
    """Demonstrate dynamic configuration updates."""
    logger.info("=== Dynamic Configuration ===\n")

    message_filter = MessageFilter(bot_id=123456789, response_threshold=0.6)

    message = create_mock_message("Maybe we should talk about this?")

    # Test with default threshold
    should_respond, score = await message_filter.is_interesting(message)
    logger.info(f"Default threshold (0.6): should_respond={should_respond}, score={score.total:.2f}")

    # Lower threshold
    message_filter.update_configuration(response_threshold=0.4)
    should_respond, score = await message_filter.is_interesting(message)
    logger.info(f"Lower threshold (0.4): should_respond={should_respond}, score={score.total:.2f}")

    # Raise threshold
    message_filter.update_configuration(response_threshold=0.8)
    should_respond, score = await message_filter.is_interesting(message)
    logger.info(f"Higher threshold (0.8): should_respond={should_respond}, score={score.total:.2f}")
    logger.info("")


async def example_rate_limiting():
    """Demonstrate rate limiting."""
    logger.info("=== Rate Limiting ===\n")

    message_filter = MessageFilter(
        bot_id=123456789,
        response_threshold=0.5,
        max_responses_per_minute=3,  # Only 3 responses per minute
    )

    # Send multiple interesting messages
    responses = []
    for i in range(6):
        message = create_mock_message(f"This is interesting question number {i}?")
        should_respond, score = await message_filter.is_interesting(message)
        responses.append(should_respond)
        logger.info(f"Message {i+1}: should_respond={should_respond}, score={score.total:.2f}")

    total_responses = sum(responses)
    logger.info(f"\nTotal responses: {total_responses}/{len(responses)}")
    logger.info(f"Rate limit applied: {total_responses <= 3}")
    logger.info("")


async def example_statistics():
    """Demonstrate statistics retrieval."""
    logger.info("=== Filter Statistics ===\n")

    message_filter = MessageFilter(
        bot_id=123456789,
        response_threshold=0.6,
        max_responses_per_minute=5,
    )

    # Process some messages
    test_messages = [
        "How does this work?",
        "What about AI?",
        "Is this interesting?",
    ]

    for content in test_messages:
        message = create_mock_message(content)
        await message_filter.is_interesting(message)

    # Get statistics
    stats = message_filter.get_statistics()

    logger.info("Current filter statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    logger.info("")


async def example_score_breakdown():
    """Demonstrate detailed score breakdown."""
    logger.info("=== Detailed Score Breakdown ===\n")

    message_filter = MessageFilter(bot_id=123456789, response_threshold=0.6)

    # Complex message with multiple scoring factors
    message = create_mock_message(
        "Co si myslíš o AI a programování? Je to zajímavé téma!"
    )

    should_respond, score = await message_filter.is_interesting(message)

    logger.info("Message: 'Co si myslíš o AI a programování? Je to zajímavé téma!'")
    logger.info(f"Final score: {score.total:.2f}")
    logger.info(f"Should respond: {should_respond}\n")

    logger.info("Score breakdown:")
    logger.info(f"  Is mention: {score.is_mention}")
    logger.info(f"  Is question: {score.is_question}")
    logger.info(f"  Has keywords: {score.has_keywords}")
    logger.info(f"  Conversation context: {score.conversation_context:.2f}")
    logger.info(f"  Sentiment score: {score.sentiment_score:.2f}")
    logger.info(f"  Length score: {score.length_score:.2f}")
    logger.info(f"  Spam penalty: {score.spam_penalty:.2f}")

    if score.details:
        logger.info("\nDetailed components:")
        for key, value in score.details.items():
            logger.info(f"  {key}: {value}")
    logger.info("")


async def main():
    """Run all examples."""
    logger.info("MessageFilter Examples\n" + "=" * 50 + "\n")

    await example_basic_usage()
    await example_mention_detection()
    await example_configuration_update()
    await example_rate_limiting()
    await example_statistics()
    await example_score_breakdown()

    logger.info("=" * 50)
    logger.info("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
