# Discord Bot Quick Start Guide

Get your Discord AI bot up and running in minutes.

## Prerequisites

- Python 3.11+
- Discord account
- At least one AI API key (Claude, Gemini, or OpenAI)

## Step 1: Discord Bot Setup

### Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give it a name and click "Create"
4. Go to "Bot" section
5. Click "Add Bot"
6. Under "Privileged Gateway Intents", enable:
   - ✅ Message Content Intent
   - ✅ Server Members Intent
   - ✅ Presence Intent (optional)
7. Click "Reset Token" and copy your bot token (keep it secret!)

### Invite Bot to Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - ✅ bot
   - ✅ applications.commands
3. Select bot permissions:
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Send Messages in Threads
   - ✅ Embed Links
   - ✅ Read Message History
   - ✅ Add Reactions
4. Copy the generated URL and open it in your browser
5. Select your server and authorize

### Get Channel IDs

1. Enable Developer Mode in Discord:
   - User Settings → Advanced → Developer Mode
2. Right-click on a channel and select "Copy ID"
3. Save these channel IDs for configuration

## Step 2: AI API Keys

Choose at least one AI provider:

### Claude (Anthropic) - Recommended

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create an account or log in
3. Go to "API Keys"
4. Create a new key
5. Copy the key (starts with `sk-ant-`)

### Gemini (Google)

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Copy the key

### OpenAI

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-`)

## Step 3: Installation

```bash
# Clone or navigate to project directory
cd discord-ai-bot-czech

# Install dependencies
pip install -r requirements.txt

# Or use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 4: Configuration

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Required
DISCORD_BOT_TOKEN=your_discord_bot_token_here
ANTHROPIC_API_KEY=sk-ant-your_key_here  # Or use GOOGLE_API_KEY or OPENAI_API_KEY

# Optional but recommended
DISCORD_CHANNEL_IDS=123456789,987654321  # Comma-separated channel IDs
BOT_LANGUAGE=cs                           # cs=Czech, en=English
BOT_RESPONSE_THRESHOLD=0.6               # 0.0-1.0 (higher = more selective)
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | *required* | Your Discord bot token |
| `DISCORD_CHANNEL_IDS` | *all* | Comma-separated allowed channel IDs |
| `ANTHROPIC_API_KEY` | - | Claude API key (recommended) |
| `GOOGLE_API_KEY` | - | Gemini API key |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `BOT_LANGUAGE` | `cs` | Response language (cs, en, sk) |
| `BOT_RESPONSE_THRESHOLD` | `0.6` | Response selectivity (0.0-1.0) |
| `BOT_MAX_HISTORY` | `50` | Messages to keep in context |
| `BOT_PERSONALITY` | `friendly` | Bot personality type |
| `LOG_LEVEL` | `INFO` | Logging level |

## Step 5: Run the Bot

```bash
# Standard run
python main.py

# With debug logging
LOG_LEVEL=DEBUG python main.py
```

You should see:

```
INFO | Logger initialized with level: INFO
INFO | ContextManager initialized with max 50 messages per channel
INFO | AI Chat cog loaded successfully
INFO | Bot is ready! Logged in as YourBot#1234 (ID: 123456789)
```

## Step 6: Test the Bot

In your Discord server:

### Basic Commands

```
!ping              # Check if bot is alive
!info              # Get bot information
!help              # Show all commands
```

### Talk to the Bot

The bot responds based on interest level. Try:

```
@YourBot Ahoj!                    # Direct mention - will respond
Jak se máš?                       # Question - might respond
@YourBot Můžeš mi pomoct?        # Mention + question - will respond
```

### Admin Commands (requires permissions)

```
!status                    # Bot status (Manage Server permission)
!providers                 # Check AI providers (Manage Server)
!clear_context            # Clear conversation history (Manage Messages)
!set_threshold 0.7        # Adjust response threshold (Administrator)
!add_keyword pomoc        # Add trigger keyword (Administrator)
```

## How the Bot Works

### Interest Scoring

The bot calculates an interest score (0.0-1.0) for each message:

- **Direct mention (@bot)**: +0.5
- **Reply to bot**: +0.4
- **Keywords** (bot, ai, help, etc.): +0.2-0.3
- **Question** (?, question words): +0.2
- **Conversation context**: +0.1-0.2
- **Message quality**: +0.0-0.1

If score ≥ threshold, bot responds.

### Response Threshold Guide

- **0.0-0.3**: Very chatty (responds to almost everything)
- **0.4-0.5**: Conversational (participates actively)
- **0.6**: Balanced (default, good for most cases)
- **0.7-0.8**: Selective (mainly mentions and questions)
- **0.9-1.0**: Very quiet (only direct mentions)

### Context Management

- Bot keeps last N messages per channel (default: 50)
- Sends last 20 messages to AI for context
- Automatically trims old messages
- Cleans up inactive channels after 24 hours

## Troubleshooting

### Bot doesn't respond

**Check threshold:**
```
!set_threshold 0.3
```

**Check channel restrictions:**
```env
# Remove or comment out to allow all channels
# DISCORD_CHANNEL_IDS=
```

**Try direct mention:**
```
@YourBot hello
```

**Check logs:**
```bash
tail -f logs/bot.log
```

### "All LLM providers failed"

1. Verify API key is correct in `.env`
2. Check API key has credits/is active
3. Test provider availability:
   ```
   !providers
   ```

### Permission errors

Ensure bot has these permissions in Discord:
- Read Messages/View Channels
- Send Messages
- Embed Links
- Read Message History

Grant via Server Settings → Roles → Your Bot Role

### Import errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Advanced Configuration

### Channel-Specific Responses

Restrict to specific channels:

```env
DISCORD_CHANNEL_IDS=123456789,987654321,555555555
```

### Custom Keywords

Add keywords that trigger responses:

```
!add_keyword help
!add_keyword python
!add_keyword discord
!list_keywords
```

### Personality Customization

Edit `bot/cogs/ai_chat.py` → `_build_system_prompt()` to customize personality:

```python
bot_personality: friendly, professional, casual, humorous, formal
```

### Multiple Servers

Bot works across multiple servers. Each server/channel maintains separate:
- Conversation context
- Command permissions
- Message history

### Production Deployment

For production, use:

```bash
# Set secure admin password
ADMIN_PASSWORD=strong_random_password_here

# Use production secret key
SECRET_KEY=$(openssl rand -hex 32)

# Set appropriate log level
LOG_LEVEL=WARNING

# Use PostgreSQL for production (optional)
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

## Next Steps

- Read [BOT_CORE.md](BOT_CORE.md) for detailed documentation
- Check [examples/bot_usage_example.py](../examples/bot_usage_example.py) for usage examples
- Review [SECURITY_AUDIT_REPORT.json](../SECURITY_AUDIT_REPORT.json) for security best practices
- See [DEPLOYMENT.md](../DEPLOYMENT.md) for production deployment

## Getting Help

- Check logs: `logs/bot.log`
- Run diagnostics: `!status` and `!providers`
- Test components: `python examples/bot_usage_example.py`
- Review test output: `pytest tests/test_bot_core.py -v`

## Common Scenarios

### Use Case 1: Support Bot
```env
BOT_RESPONSE_THRESHOLD=0.5
BOT_LANGUAGE=cs
BOT_PERSONALITY=helpful and professional
# Keywords: help, pomoc, support, issue
```

### Use Case 2: Community Bot
```env
BOT_RESPONSE_THRESHOLD=0.6
BOT_LANGUAGE=cs
BOT_PERSONALITY=friendly and casual
# Keywords: your community-specific terms
```

### Use Case 3: Technical Bot
```env
BOT_RESPONSE_THRESHOLD=0.7
BOT_LANGUAGE=en
BOT_PERSONALITY=technical and precise
# Keywords: code, python, bug, debug, api
```

Happy botting! 🤖
