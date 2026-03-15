# Discord Bot Core Documentation

This document describes the core functionality of the Discord AI Bot, including context management, interest filtering, and message handling.

## Architecture Overview

The bot core consists of several key components:

1. **Context Manager** - Manages conversation history per channel/thread
2. **Interest Filter** - Determines when the bot should respond
3. **AI Chat Cog** - Main message handler and LLM integration
4. **Admin Cog** - Bot management and diagnostics

## Components

### 1. Context Manager (`bot/context_manager.py`)

Manages conversation context windows for each Discord channel/thread.

#### Features

- **Per-Channel Context**: Maintains separate conversation history for each channel
- **Automatic Trimming**: Keeps only the most recent N messages (configurable)
- **LLM Formatting**: Converts Discord messages to LLM-compatible format
- **Statistics**: Provides insights into conversation activity

#### Usage Example

```python
from bot.context_manager import ContextManager

# Initialize
context_manager = ContextManager(max_messages_per_channel=50)

# Add message
context_manager.add_message(channel_id, discord_message)

# Get formatted messages for LLM
llm_messages = context_manager.format_for_llm(channel_id, limit=20)

# Clear context
context_manager.clear_channel(channel_id)
```

#### Key Classes

**MessageContext**
- `author_id`: Discord user ID
- `author_name`: Display name
- `content`: Message text
- `timestamp`: When message was sent
- `is_bot`: Whether message is from a bot
- `channel_id`: Channel where message was sent

**ConversationWindow**
- `channel_id`: Discord channel ID
- `max_messages`: Maximum messages to keep
- `messages`: Deque of MessageContext objects
- `last_activity`: Timestamp of last message

**ContextManager**
- `get_or_create_window(channel_id)`: Get/create conversation window
- `add_message(channel_id, message)`: Add Discord message to context
- `get_context_messages(channel_id, limit)`: Get messages for channel
- `format_for_llm(channel_id, limit, include_bot_messages)`: Format for LLM
- `clear_channel(channel_id)`: Clear channel context
- `clear_all()`: Clear all contexts
- `get_stats()`: Get statistics
- `cleanup_inactive(inactive_hours)`: Remove inactive windows

### 2. Interest Filter (`bot/interest_filter.py`)

Determines whether the bot should respond to a message based on multiple criteria.

#### Response Criteria

The filter evaluates messages using a scoring system (0.0 to 1.0):

1. **Direct Mention** (+0.5) - Bot is @mentioned
2. **Reply to Bot** (+0.4) - Message is a reply to bot's message
3. **Keywords** (+0.2-0.3) - Contains trigger keywords
4. **Question** (+0.2) - Message is a question (?, question words)
5. **Conversation Context** (+0.1-0.2) - Continues active conversation
6. **Message Quality** (+0.0-0.1) - Message length and substance

If total score ≥ `response_threshold`, bot responds.

#### Built-in Czech Keywords

- bot, ai, asistent, pomoc, help
- prosím, prosim, děkuji, dekuji

#### Usage Example

```python
from bot.interest_filter import InterestFilter

# Initialize
filter = InterestFilter(
    bot_user_id=123456789,
    response_threshold=0.6,
    keywords=["custom", "trigger"],
    always_respond_in_dms=True
)

# Check if should respond
should_respond, score, reason = filter.should_respond(
    message,
    is_reply_to_bot=False,
    conversation_context=["previous", "messages"]
)

# Manage keywords
filter.add_keyword("new_keyword")
filter.remove_keyword("old_keyword")
filter.set_threshold(0.7)
```

#### Configuration

- `response_threshold`: Score threshold (0.0-1.0, default: 0.6)
- `keywords`: Custom trigger keywords
- `always_respond_in_dms`: Always respond to DMs (default: True)

### 3. AI Chat Cog (`bot/cogs/ai_chat.py`)

Main cog handling AI-powered conversations.

#### Features

- **Automatic Message Filtering**: Uses InterestFilter to decide responses
- **Context-Aware Responses**: Includes conversation history in LLM prompts
- **Multi-Provider Support**: Automatic fallback between Claude/Gemini/OpenAI
- **Czech Language**: Configurable language responses
- **Discord Integration**: Proper typing indicators, message splitting, etc.

#### Event Handlers

**on_message(message)**
- Listens to all Discord messages
- Filters based on channel restrictions
- Checks interest level
- Generates and sends responses

#### Commands

**!clear_context** (Requires: Manage Messages)
- Clears conversation context for current channel

**!context_stats** (Requires: Manage Messages)
- Shows context statistics

**!set_threshold <0.0-1.0>** (Requires: Administrator)
- Sets response threshold

**!add_keyword <word>** (Requires: Administrator)
- Adds trigger keyword

**!remove_keyword <word>** (Requires: Administrator)
- Removes trigger keyword

**!list_keywords** (Requires: Manage Messages)
- Lists all configured keywords

#### System Prompt

The bot uses a customizable system prompt that includes:
- Language specification (Czech by default)
- Personality configuration
- Conversation guidelines
- Discord-specific formatting instructions

### 4. Admin Cog (`bot/cogs/admin.py`)

Administrative commands for bot management.

#### Commands

**!ping**
- Check bot latency

**!info**
- Show bot information

**!status** (Requires: Manage Server)
- Detailed bot status including:
  - Uptime
  - Latency
  - Connected guilds
  - Configuration
  - AI providers
  - System info

**!providers** (Requires: Manage Server)
- Check AI provider availability
- Tests connectivity to Claude/Gemini/OpenAI

**!reload <cog_name>** (Owner only)
- Reload a bot cog without restarting

**!shutdown** (Owner only)
- Gracefully shutdown the bot

**!help [command]**
- Show help for all commands or specific command

## Configuration

### Environment Variables

```bash
# Discord Configuration
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_guild_id
DISCORD_CHANNEL_IDS=channel1,channel2,channel3

# AI API Keys (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENAI_API_KEY=sk-...

# Bot Behavior
BOT_RESPONSE_THRESHOLD=0.6    # 0.0-1.0
BOT_MAX_HISTORY=50            # Messages to keep
BOT_LANGUAGE=cs               # cs, en, sk, etc.
BOT_PERSONALITY=friendly      # friendly, professional, casual

# Logging
LOG_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/bot.log
```

### Channel Restrictions

If `DISCORD_CHANNEL_IDS` is set, bot only responds in those channels.
Leave empty to allow all channels.

### Response Threshold

Controls how selective the bot is:
- **0.0-0.3**: Very responsive (responds to most messages)
- **0.4-0.6**: Balanced (default)
- **0.7-1.0**: Conservative (only responds to direct mentions/replies)

## Message Flow

1. User sends message in Discord
2. Bot receives `on_message` event
3. Check if message is from bot itself → ignore
4. Check channel restrictions → ignore if not allowed
5. Add message to context manager
6. Check if message is reply to bot
7. Get conversation context (last 5 messages)
8. Run interest filter to calculate score
9. If score < threshold → ignore
10. Get last 20 messages for LLM context
11. Format messages for LLM
12. Generate response using LLM client (with fallback)
13. Send response to Discord
14. Handle long messages (split if needed)

## Error Handling

### LLM Failures

When all LLM providers fail, bot sends:
> "Omlouváme se, momentálně nejsem schopen odpovědět. Zkuste to prosím později."

### Discord Errors

- HTTP errors are logged and user gets generic error message
- Rate limits are handled by discord.py
- Message send failures are caught and logged

### Logging

All events are logged with appropriate levels:
- **DEBUG**: Detailed message processing
- **INFO**: Important events (responses, config changes)
- **WARNING**: Recoverable errors
- **ERROR**: Failures requiring attention
- **CRITICAL**: Fatal errors

## Testing

Run tests with pytest:

```bash
pytest tests/test_bot_core.py -v
```

Tests cover:
- Context manager operations
- Interest filter scoring
- Message handling
- Configuration management

## Performance

### Memory Management

- Automatic context trimming (configurable max messages)
- Inactive window cleanup (24 hours default)
- Efficient deque-based message storage

### API Optimization

- Parallel provider checks
- Exponential backoff for rate limits
- Request caching in LLM client

### Discord Optimization

- Efficient message filtering
- Minimal API calls
- Proper typing indicators

## Troubleshooting

### Bot Not Responding

1. Check channel restrictions (`DISCORD_CHANNEL_IDS`)
2. Check response threshold (may be too high)
3. Verify message triggers (mention, keywords, questions)
4. Check logs for interest filter scores

### High Response Rate

1. Increase `BOT_RESPONSE_THRESHOLD` (e.g., 0.7-0.8)
2. Reduce custom keywords
3. Disable DM auto-response if needed

### Context Issues

1. Clear context with `!clear_context`
2. Check max history setting (`BOT_MAX_HISTORY`)
3. Review context stats with `!context_stats`

### LLM Errors

1. Verify API keys are valid
2. Check provider status with `!providers`
3. Review logs for specific error messages
4. Ensure at least one provider is configured

## Future Enhancements

Potential improvements:

- Sentiment analysis for better filtering
- User-specific context preferences
- Advanced conversation threading
- Multi-language detection
- Response caching
- Custom personality profiles per channel
- Conversation summarization for long threads
- Integration with Discord forums
- Voice channel support
