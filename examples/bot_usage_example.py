"""
Discord Bot Usage Example

This example demonstrates how to use the Discord bot core components
independently for testing or integration purposes.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock

from bot.context_manager import ContextManager, MessageContext
from bot.interest_filter import InterestFilter


def example_context_manager():
    """
    Example: Using the Context Manager

    Demonstrates how to manage conversation contexts across channels.
    """
    print("=" * 60)
    print("Context Manager Example")
    print("=" * 60)

    # Initialize context manager
    manager = ContextManager(max_messages_per_channel=10)

    # Simulate adding messages to a channel
    channel_id = 123456789

    messages = [
        ("Alice", "Ahoj! Jak se máš?"),
        ("Bot", "Ahoj Alice! Mám se dobře, díky!"),
        ("Alice", "Můžeš mi pomoct s něčím?"),
        ("Bob", "Ahoj všem!"),
        ("Bot", "Ahoj Bob!"),
        ("Alice", "Potřebuji poradit s Pythonem"),
    ]

    # Add messages to context
    for i, (author, content) in enumerate(messages):
        msg = MessageContext(
            author_id=hash(author) % 1000000,
            author_name=author,
            content=content,
            timestamp=datetime.now(),
            is_bot=(author == "Bot"),
            channel_id=channel_id
        )
        manager.get_or_create_window(channel_id).add_message(msg)

    print(f"\nAdded {len(messages)} messages to channel {channel_id}")

    # Retrieve context
    context = manager.get_context_messages(channel_id)
    print(f"\nRetrieved {len(context)} messages from context:")
    for msg in context:
        print(f"  [{msg.author_name}]: {msg.content}")

    # Format for LLM
    print("\nFormatted for LLM:")
    llm_messages = manager.format_for_llm(channel_id)
    for msg in llm_messages:
        print(f"  {msg['role']}: {msg['content']}")

    # Get statistics
    print("\nContext Statistics:")
    stats = manager.get_stats()
    print(f"  Total windows: {stats['total_windows']}")
    print(f"  Total messages: {stats['total_messages']}")

    # Clear context
    manager.clear_channel(channel_id)
    print(f"\nCleared channel {channel_id}")
    print(f"Messages remaining: {len(manager.get_context_messages(channel_id))}")


def example_interest_filter():
    """
    Example: Using the Interest Filter

    Demonstrates how the interest filter scores messages.
    """
    print("\n" + "=" * 60)
    print("Interest Filter Example")
    print("=" * 60)

    # Initialize filter
    filter = InterestFilter(
        bot_user_id=999,
        response_threshold=0.6,
        keywords=["python", "pomoc"],
        always_respond_in_dms=True
    )

    print(f"\nResponse threshold: {filter.response_threshold}")
    print(f"Custom keywords: {', '.join(filter.get_keywords())}")

    # Test various message types
    test_cases = [
        {
            "content": "Ahoj všem!",
            "mentions_bot": False,
            "is_reply": False,
            "description": "Simple greeting"
        },
        {
            "content": "Jak se dělá python?",
            "mentions_bot": False,
            "is_reply": False,
            "description": "Question with keyword"
        },
        {
            "content": "Díky za pomoc!",
            "mentions_bot": False,
            "is_reply": True,
            "description": "Reply to bot with keyword"
        },
        {
            "content": "Hey bot, co umíš?",
            "mentions_bot": True,
            "is_reply": False,
            "description": "Direct mention with question"
        },
        {
            "content": "test",
            "mentions_bot": False,
            "is_reply": False,
            "description": "Short message"
        },
    ]

    print("\nTesting messages:\n")

    for i, test in enumerate(test_cases, 1):
        # Create mock message
        mock_message = Mock()
        mock_message.author.bot = False
        mock_message.author.id = 123
        mock_message.content = test["content"]
        mock_message.channel = Mock()  # Text channel

        # Add mention if needed
        if test["mentions_bot"]:
            bot_user = Mock()
            bot_user.id = 999
            mock_message.mentions = [bot_user]
        else:
            mock_message.mentions = []

        # Check response
        should_respond, score, reason = filter.should_respond(
            mock_message,
            is_reply_to_bot=test["is_reply"]
        )

        print(f"{i}. {test['description']}")
        print(f"   Message: \"{test['content']}\"")
        print(f"   Score: {score:.2f} | Threshold: {filter.response_threshold}")
        print(f"   Respond: {'YES ✓' if should_respond else 'NO ✗'}")
        print(f"   Reason: {reason}")
        print()

    # Demonstrate threshold adjustment
    print("\nAdjusting threshold to 0.3 (more responsive):")
    filter.set_threshold(0.3)

    mock_message = Mock()
    mock_message.author.bot = False
    mock_message.author.id = 123
    mock_message.content = "test"
    mock_message.channel = Mock()
    mock_message.mentions = []

    should_respond, score, reason = filter.should_respond(mock_message)
    print(f"Message \"test\" now: {'responds ✓' if should_respond else 'ignored ✗'}")


def example_combined_usage():
    """
    Example: Combined Usage

    Demonstrates using context manager and interest filter together.
    """
    print("\n" + "=" * 60)
    print("Combined Usage Example")
    print("=" * 60)

    # Initialize components
    context_manager = ContextManager(max_messages_per_channel=20)
    interest_filter = InterestFilter(
        bot_user_id=999,
        response_threshold=0.5,
        keywords=["help", "python"]
    )

    channel_id = 123456789

    # Simulate conversation
    print("\nSimulating a conversation:\n")

    conversation = [
        ("Alice", "Ahoj kanále!", False, False),
        ("Bob", "Ahoj Alice!", False, False),
        ("Alice", "Někdo mi může pomoct s Pythonem?", False, False),
        ("Bot", "Ahoj Alice! Samozřejmě, s čím potřebuješ pomoct?", False, True),
        ("Alice", "Jak použít async/await?", True, False),
    ]

    for author, content, is_reply_to_bot, is_from_bot in conversation:
        # Create message context
        msg_ctx = MessageContext(
            author_id=hash(author) % 1000000,
            author_name=author,
            content=content,
            timestamp=datetime.now(),
            is_bot=is_from_bot,
            channel_id=channel_id
        )

        # Add to context
        context_manager.get_or_create_window(channel_id).add_message(msg_ctx)

        # Check if bot should respond (skip bot's own messages)
        if not is_from_bot:
            # Create mock Discord message
            mock_msg = Mock()
            mock_msg.author.bot = False
            mock_msg.author.id = msg_ctx.author_id
            mock_msg.content = content
            mock_msg.channel = Mock()
            mock_msg.mentions = []

            # Get recent context for filtering
            recent = context_manager.get_context_messages(channel_id, limit=3)
            context_list = [m.content for m in recent]

            should_respond, score, reason = interest_filter.should_respond(
                mock_msg,
                is_reply_to_bot=is_reply_to_bot,
                conversation_context=context_list
            )

            response_status = "→ BOT RESPONDS" if should_respond else ""
            print(f"[{author}]: {content}")
            print(f"  Score: {score:.2f} | Reason: {reason} {response_status}")
        else:
            print(f"[{author}]: {content}")

        print()

    # Show final context
    print("\nFinal conversation context for LLM:")
    llm_messages = context_manager.format_for_llm(channel_id, limit=5)
    for msg in llm_messages:
        role_emoji = "🤖" if msg["role"] == "assistant" else "👤"
        print(f"{role_emoji} {msg['role']}: {msg['content']}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("DISCORD BOT CORE COMPONENTS - USAGE EXAMPLES")
    print("=" * 60)

    example_context_manager()
    example_interest_filter()
    example_combined_usage()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
