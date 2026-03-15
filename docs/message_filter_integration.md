# Message Filter Integration Guide

## Quick Start

This guide shows how to integrate the MessageFilter into your Discord bot.

## Installation

The MessageFilter is included in the bot utilities. No additional dependencies required.

```python
from bot.utils.message_filter import MessageFilter, MessageScore
```

## Basic Bot Integration

### Step 1: Initialize the Filter

In your bot's main file or a cog:

```python
from discord.ext import commands
from bot.utils.message_filter import MessageFilter

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!")
        self.message_filter = None

    async def setup_hook(self):
        # Initialize filter once bot is ready
        self.message_filter = MessageFilter(
            bot_id=self.user.id,
            response_threshold=0.6,
            max_responses_per_minute=5,
        )
```

### Step 2: Handle Messages

```python
@bot.event
async def on_message(message):
    # Don't respond to own messages
    if message.author.id == bot.user.id:
        return

    # Don't process commands
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    # Check if message is interesting
    should_respond, score = await bot.message_filter.is_interesting(message)

    if should_respond:
        # Generate and send response
        async with message.channel.typing():
            response = await generate_bot_response(message)
            await message.channel.send(response)

    # Still process commands
    await bot.process_commands(message)
```

### Step 3: Generate Response

```python
async def generate_bot_response(message):
    """Generate a response using your LLM client."""
    from src.llm.client import LLMClient
    from src.llm.base import LLMMessage

    # Initialize LLM client (cache this in production)
    llm = LLMClient(
        anthropic_api_key=config.anthropic_api_key,
        google_api_key=config.google_api_key,
        openai_api_key=config.openai_api_key,
    )

    # Create message history
    messages = [
        LLMMessage(role="user", content=message.content)
    ]

    # Generate response
    response = await llm.generate_response(
        messages=messages,
        system_prompt="You are a helpful Discord bot. Respond in Czech.",
        temperature=0.7,
        max_tokens=500,
    )

    return response.content
```

## Advanced Integration with Context

```python
@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return

    # Get recent message history for context
    context_messages = []
    async for msg in message.channel.history(limit=20):
        context_messages.append(msg)
    context_messages.reverse()  # Oldest first

    # Check with context
    should_respond, score = await bot.message_filter.is_interesting(
        message,
        context_messages=context_messages
    )

    if should_respond:
        # Log the decision
        logger.info(
            f"Responding to message in #{message.channel.name}: "
            f"score={score.total:.2f}, "
            f"question={score.is_question}, "
            f"keywords={score.has_keywords}"
        )

        # Generate contextual response
        response = await generate_contextual_response(
            message,
            context_messages
        )
        await message.channel.send(response)
```

## Cog-Based Implementation

```python
from discord.ext import commands
from bot.utils.message_filter import MessageFilter
import logging

logger = logging.getLogger(__name__)

class MessageResponder(commands.Cog):
    """Cog for handling automatic message responses."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_filter = MessageFilter(
            bot_id=bot.user.id,
            response_threshold=0.6,
            max_responses_per_minute=5,
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages."""
        # Skip bot messages
        if message.author.bot:
            return

        # Skip commands
        if message.content.startswith(self.bot.command_prefix):
            return

        # Get context
        context = await self._get_context(message)

        # Check interest
        should_respond, score = await self.message_filter.is_interesting(
            message,
            context_messages=context
        )

        if should_respond:
            await self._respond_to_message(message, context, score)

    async def _get_context(self, message):
        """Get recent message context."""
        context = []
        async for msg in message.channel.history(limit=20):
            context.append(msg)
        return list(reversed(context))

    async def _respond_to_message(self, message, context, score):
        """Generate and send a response."""
        try:
            async with message.channel.typing():
                # Build conversation history
                conversation = self._build_conversation(context)

                # Generate response
                response = await self._generate_response(conversation)

                # Send response
                await message.channel.send(response)

                logger.info(
                    f"Responded in #{message.channel.name} "
                    f"(score: {score.total:.2f})"
                )

        except Exception as e:
            logger.error(f"Error generating response: {e}")

    def _build_conversation(self, context_messages):
        """Build conversation history for LLM."""
        from src.llm.base import LLMMessage

        messages = []
        for msg in context_messages[-10:]:  # Last 10 messages
            role = "assistant" if msg.author.id == self.bot.user.id else "user"
            messages.append(
                LLMMessage(
                    role=role,
                    content=f"{msg.author.name}: {msg.content}"
                )
            )
        return messages

    async def _generate_response(self, messages):
        """Generate response using LLM."""
        # Your LLM integration here
        pass

    @commands.command(name="filter_stats")
    @commands.has_permissions(administrator=True)
    async def show_filter_stats(self, ctx):
        """Show message filter statistics."""
        stats = self.message_filter.get_statistics()

        embed = discord.Embed(
            title="Message Filter Statistics",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Response Threshold",
            value=f"{stats['response_threshold']:.2f}",
            inline=True
        )
        embed.add_field(
            name="Max Responses/Min",
            value=stats['max_responses_per_minute'],
            inline=True
        )
        embed.add_field(
            name="Recent Responses",
            value=stats['recent_responses_total'],
            inline=True
        )
        embed.add_field(
            name="Active Channels",
            value=stats['active_channels'],
            inline=True
        )
        embed.add_field(
            name="AI Scoring",
            value="Enabled" if stats['enable_ai_scoring'] else "Disabled",
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.command(name="set_threshold")
    @commands.has_permissions(administrator=True)
    async def set_threshold(self, ctx, threshold: float):
        """Set response threshold (0.0 to 1.0)."""
        if not 0.0 <= threshold <= 1.0:
            await ctx.send("❌ Threshold must be between 0.0 and 1.0")
            return

        self.message_filter.update_configuration(
            response_threshold=threshold
        )

        await ctx.send(f"✅ Response threshold set to {threshold:.2f}")

    @commands.command(name="set_rate_limit")
    @commands.has_permissions(administrator=True)
    async def set_rate_limit(self, ctx, limit: int):
        """Set maximum responses per minute."""
        if limit < 1:
            await ctx.send("❌ Rate limit must be at least 1")
            return

        self.message_filter.update_configuration(
            max_responses_per_minute=limit
        )

        await ctx.send(f"✅ Rate limit set to {limit} responses/minute")


async def setup(bot):
    """Setup cog."""
    await bot.add_cog(MessageResponder(bot))
```

## Configuration from Environment

```python
from bot.config import BotConfig
from bot.utils.message_filter import MessageFilter

# Load config
config = BotConfig()

# Initialize filter with config values
message_filter = MessageFilter(
    bot_id=bot.user.id,
    response_threshold=config.bot_response_threshold,
    max_responses_per_minute=5,
    conversation_context_weight=0.3,
)
```

## Monitoring and Debugging

### Enable Debug Logging

```python
import logging

logging.getLogger('bot.utils.message_filter').setLevel(logging.DEBUG)
```

### Log Score Details

```python
should_respond, score = await message_filter.is_interesting(message)

logger.debug(
    f"Message score breakdown: "
    f"total={score.total:.2f}, "
    f"mention={score.is_mention}, "
    f"question={score.is_question}, "
    f"keywords={score.has_keywords}, "
    f"context={score.conversation_context:.2f}, "
    f"sentiment={score.sentiment_score:.2f}, "
    f"spam_penalty={score.spam_penalty:.2f}"
)

if score.details:
    logger.debug(f"Score components: {score.details}")
```

## Performance Considerations

### Caching Context Messages

```python
from functools import lru_cache
from datetime import datetime, timedelta

class OptimizedResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_filter = MessageFilter(bot_id=bot.user.id)
        self._context_cache = {}
        self._cache_ttl = 30  # seconds

    async def _get_cached_context(self, channel_id):
        """Get context with caching."""
        now = datetime.now()

        # Check cache
        if channel_id in self._context_cache:
            cached_time, cached_messages = self._context_cache[channel_id]
            if (now - cached_time).total_seconds() < self._cache_ttl:
                return cached_messages

        # Fetch new context
        channel = self.bot.get_channel(channel_id)
        context = await channel.history(limit=20).flatten()

        # Update cache
        self._context_cache[channel_id] = (now, context)

        return context
```

## Testing Your Integration

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_bot_responds_to_questions(bot, message_filter):
    """Test that bot responds to questions."""
    message = Mock()
    message.content = "How does this work?"
    message.author.bot = False

    should_respond, score = await message_filter.is_interesting(message)

    assert should_respond is True
    assert score.is_question is True
```

## Troubleshooting

### Bot not responding at all

1. Check threshold is not too high
2. Verify bot ID is correct
3. Check rate limiting is not too restrictive
4. Enable debug logging

### Bot responding to everything

1. Increase response threshold
2. Reduce rate limit
3. Check spam detection is working

### Bot missing important messages

1. Lower threshold
2. Check keyword list coverage
3. Review score breakdown for missed messages

## Best Practices

1. **Start Conservative** - Begin with higher threshold (0.7+) and adjust down
2. **Monitor Performance** - Track response rates and adjust
3. **Use Context** - Always provide context messages when available
4. **Log Decisions** - Log score breakdowns for analysis
5. **Rate Limit** - Prevent bot spam with appropriate limits
6. **Handle Errors** - Gracefully handle filter failures
7. **Test Thoroughly** - Test with various message types
8. **Update Keywords** - Keep keyword lists relevant to your community
