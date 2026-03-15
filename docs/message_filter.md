# Message Interest Detection System

## Overview

The Message Interest Detection System is a sophisticated filtering module that determines whether a Discord message is interesting enough to warrant a bot response. It uses multiple heuristics including keyword matching, question detection, sentiment analysis, conversation context, and spam detection.

## Features

### Core Detection Methods

1. **Direct Mentions** - Always responds when the bot is @mentioned
2. **Question Detection** - Identifies questions in Czech and English
3. **Keyword Matching** - Detects interesting topics (AI, programming, etc.)
4. **Conversation Starters** - Recognizes phrases that invite discussion
5. **Context Awareness** - Considers recent conversation history
6. **Sentiment Analysis** - Basic sentiment scoring
7. **Spam Detection** - Filters out spam and repetitive messages
8. **Rate Limiting** - Prevents excessive bot responses

### Configurable Parameters

- **Response Threshold** (0.0 to 1.0) - Minimum score required to respond
- **Max Responses Per Minute** - Rate limit for bot responses
- **Conversation Context Weight** - How much to weight recent context
- **AI Scoring** - Optional AI-based scoring (future enhancement)

## Usage

### Basic Usage

```python
from bot.utils.message_filter import MessageFilter

# Initialize filter
message_filter = MessageFilter(
    bot_id=YOUR_BOT_ID,
    response_threshold=0.6,  # 60% confidence required
    max_responses_per_minute=5,
)

# Check if message is interesting
should_respond, score = await message_filter.is_interesting(message)

if should_respond:
    # Generate and send response
    response = await generate_response(message)
    await message.channel.send(response)
```

### With Context Messages

```python
# Get recent channel messages
context_messages = await message.channel.history(limit=20).flatten()

# Check with context
should_respond, score = await message_filter.is_interesting(
    message,
    context_messages=context_messages
)
```

### Dynamic Configuration

```python
# Update configuration at runtime
message_filter.update_configuration(
    response_threshold=0.7,  # Raise threshold
    max_responses_per_minute=3,  # Lower rate limit
)
```

### Getting Statistics

```python
stats = message_filter.get_statistics()
print(f"Current threshold: {stats['response_threshold']}")
print(f"Recent responses: {stats['recent_responses_total']}")
```

## Score Breakdown

The `MessageScore` object contains detailed information about why a message received its score:

```python
should_respond, score = await message_filter.is_interesting(message)

print(f"Total score: {score.total}")
print(f"Is mention: {score.is_mention}")
print(f"Is question: {score.is_question}")
print(f"Has keywords: {score.has_keywords}")
print(f"Context score: {score.conversation_context}")
print(f"Sentiment: {score.sentiment_score}")
print(f"Length score: {score.length_score}")
print(f"Spam penalty: {score.spam_penalty}")
```

## Detection Heuristics

### Question Detection

Detects questions in both Czech and English:

**Czech Question Words:**
- co, kdo, kdy, kde, jak, proč, jaký, která, které, který
- víš, víte, znáš, znáte, myslíš, myslíte

**English Question Words:**
- what, who, when, where, why, how, which
- do you know, do you think, do you believe

**Pattern:**
- Any message ending with `?`

### Interesting Keywords

Matches keywords related to:

**Technology:**
- AI, umělá inteligence, Python, JavaScript, programming
- kód, code, bug, error, algorithm, algoritmus

**Discussion:**
- myslíš, myslíte, think, opinion, názor
- diskuze, debate, debata

**Help/Questions:**
- pomoc, help, nevím, don't know, otázka, question
- poradit, advice, suggest

**Engaging Topics:**
- zajímavé, interesting, cool, amazing, skvělé

### Conversation Starters

Phrases that typically invite discussion:

- "co si myslíš/myslíte" (what do you think)
- "slyšel jsi/slyšeli jste" (have you heard)
- "víš něco o/víte něco o" (do you know about)
- "mám otázku" (I have a question)
- "co říkáš na/co říkáte na" (what do you say about)

### Spam Detection

Filters out:

- **Repeated characters**: `aaaaaaaaaa`
- **Excessive punctuation**: `!!!!!!!!!!`
- **All caps spam**: `THIS IS SPAM`
- **Only emojis**: `😂😂😂😂`
- **High repetition ratio**: Messages with mostly repeated words

### Length Scoring

Optimal message length: **5-50 words**

- Very short (< 2 words): Low score
- Short (2-5 words): Medium score
- Optimal (5-50 words): High score
- Long (50-100 words): Medium score
- Very long (> 100 words): Low score (potential spam/copypasta)

### Sentiment Analysis

Basic sentiment detection using positive/negative word lists:

**Positive words:** skvělé, great, awesome, cool, amazing, zajímavé, interesting, díky, thanks

**Negative words:** špatné, bad, awful, terrible, stupid, hate, nefunguje, doesn't work, broken

Sentiment contributes up to 30% of the score.

## Rate Limiting

The filter implements per-channel rate limiting to prevent spam:

- Tracks responses in the last minute
- Enforces configurable maximum responses per minute
- Automatically resets after time window
- Independent limits per channel

## Score Calculation

The total score is calculated using weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Mention | 100% | Direct @mention (always responds) |
| Question | 35% | Detected question pattern |
| Keywords | 25% | Interesting keywords found |
| Conversation Starter | 25% | Phrase that invites discussion |
| Context | 20% | Recent conversation relevance |
| Length | 10% | Message length quality |
| Sentiment | 10% | Positive/negative sentiment |
| Spam Penalty | -100% | Detected spam patterns |

**Note:** Mentions bypass all other scoring and always result in a response.

## Integration Example

```python
import discord
from discord.ext import commands
from bot.utils.message_filter import MessageFilter

class MessageHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_filter = MessageFilter(
            bot_id=bot.user.id,
            response_threshold=0.6,
            max_responses_per_minute=5,
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore own messages
        if message.author.id == self.bot.user.id:
            return

        # Get recent context
        context_messages = await message.channel.history(limit=20).flatten()

        # Check if interesting
        should_respond, score = await self.message_filter.is_interesting(
            message,
            context_messages=context_messages
        )

        if should_respond:
            # Generate response using LLM
            response = await self.generate_response(message, context_messages)
            await message.channel.send(response)

    async def generate_response(self, message, context):
        # Your LLM integration here
        pass

async def setup(bot):
    await bot.add_cog(MessageHandler(bot))
```

## Configuration Best Practices

### Conservative Bot (Less Active)

```python
MessageFilter(
    bot_id=bot_id,
    response_threshold=0.75,  # High threshold
    max_responses_per_minute=3,  # Low rate limit
)
```

### Balanced Bot (Recommended)

```python
MessageFilter(
    bot_id=bot_id,
    response_threshold=0.6,  # Medium threshold
    max_responses_per_minute=5,  # Medium rate limit
)
```

### Active Bot (More Engagement)

```python
MessageFilter(
    bot_id=bot_id,
    response_threshold=0.4,  # Lower threshold
    max_responses_per_minute=8,  # Higher rate limit
)
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_message_filter.py -v
```

Run the example script:

```bash
python examples/message_filter_example.py
```

## Future Enhancements

1. **AI-Based Scoring** - Use LLM to score message relevance
2. **User Preferences** - Per-user sensitivity settings
3. **Learning Mode** - Adapt thresholds based on user feedback
4. **Multi-language Support** - Extended language support
5. **Topic Tracking** - Remember ongoing discussion topics
6. **Personality Matching** - Adjust scoring based on bot personality

## Troubleshooting

### Bot responds too often

Increase `response_threshold` or decrease `max_responses_per_minute`:

```python
message_filter.update_configuration(
    response_threshold=0.7,
    max_responses_per_minute=3
)
```

### Bot doesn't respond enough

Decrease `response_threshold`:

```python
message_filter.update_configuration(response_threshold=0.4)
```

### Bot responds to spam

Check that spam detection is working:

```python
should_respond, score = await message_filter.is_interesting(message)
if score.spam_penalty > 0:
    print(f"Spam detected: penalty={score.spam_penalty}")
```

### Bot ignores important messages

Check score breakdown to understand why:

```python
should_respond, score = await message_filter.is_interesting(message)
print(f"Score details: {score.details}")
```

## API Reference

### MessageFilter

#### Constructor

```python
MessageFilter(
    bot_id: int,
    response_threshold: float = 0.6,
    min_message_length: int = 3,
    max_responses_per_minute: int = 5,
    conversation_context_weight: float = 0.3,
    enable_ai_scoring: bool = False,
)
```

#### Methods

- `is_interesting(message, context_messages=None) -> tuple[bool, MessageScore]`
- `update_configuration(response_threshold=None, max_responses_per_minute=None, enable_ai_scoring=None)`
- `get_statistics() -> Dict[str, any]`

### MessageScore

#### Attributes

- `total: float` - Total score (0.0 to 1.0)
- `is_mention: bool` - Whether bot was mentioned
- `is_question: bool` - Whether message is a question
- `has_keywords: bool` - Whether interesting keywords found
- `conversation_context: float` - Conversation context score
- `sentiment_score: float` - Sentiment analysis score
- `length_score: float` - Message length score
- `spam_penalty: float` - Spam detection penalty
- `details: Dict[str, any]` - Additional scoring details
