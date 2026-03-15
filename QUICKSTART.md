# Quick Start Guide

Get your Discord AI bot running in 5 minutes.

## Prerequisites

- Discord account
- At least one AI API key (Claude, Gemini, or OpenAI)
- Python 3.9+ OR Docker installed

## Option 1: Local Setup (5 minutes)

### 1. Get Discord Bot Token

1. Visit [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" → Enter name → "Create"
3. Go to "Bot" tab → "Add Bot" → "Yes, do it!"
4. Click "Reset Token" → Copy the token
5. Enable these intents:
   - ✅ PRESENCE INTENT
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT
6. Save Changes

### 2. Invite Bot to Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - ✅ bot
3. Select permissions:
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Read Message History
4. Copy generated URL → Open in browser
5. Select your server → Authorize

### 3. Get Channel ID

1. Open Discord → User Settings → Advanced
2. Enable "Developer Mode"
3. Right-click your channel → "Copy Channel ID"

### 4. Get AI API Key

**Claude (Recommended)**:
- Go to [console.anthropic.com](https://console.anthropic.com/)
- API Keys → Create Key → Copy

**OR Gemini**:
- Go to [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
- Create API Key → Copy

**OR OpenAI**:
- Go to [platform.openai.com](https://platform.openai.com/)
- API Keys → Create new secret key → Copy

### 5. Configure and Run

```bash
# Navigate to project
cd discord-ai-bot-czech

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp .env.example .env
nano .env  # Edit with your tokens
```

Add to `.env`:
```env
DISCORD_BOT_TOKEN=your_discord_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
CLAUDE_API_KEY=your_claude_key_here
```

```bash
# Run the bot
python bot.py
```

Done! Bot is now running. Open http://localhost:8000 for admin interface.

## Option 2: Docker Setup (3 minutes)

```bash
# Navigate to project
cd discord-ai-bot-czech

# Create configuration
cp .env.example .env
nano .env  # Add your tokens (see step 4-5 above)

# Start with Docker
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

Done! Bot is running in Docker.

## Testing

1. Open your Discord channel
2. Send a message: "Ahoj, co si myslíš o umělé inteligenci?"
3. Bot should respond naturally in Czech

## Admin Interface

1. Open browser: http://localhost:8000
2. Login: `admin` / `admin` (change this!)
3. Configure bot settings via web UI

## Troubleshooting

**Bot doesn't start**:
- Check token is correct in `.env`
- Verify you have at least one API key

**Bot is silent**:
- Check channel ID is correct
- Verify MESSAGE CONTENT INTENT is enabled
- Lower RESPONSE_THRESHOLD to 0.3 in `.env`

**Permission errors**:
- Reinstall bot with correct permissions
- Check channel-specific permissions

## Next Steps

- Read full [README.md](README.md) for detailed setup
- Check [DEPLOYMENT.md](docs/DEPLOYMENT.md) for production
- Review [API.md](docs/API.md) for admin API reference
- Adjust RESPONSE_THRESHOLD to control chattiness

## Quick Commands

```bash
# Stop bot (local)
Ctrl+C

# Stop bot (Docker)
docker-compose down

# View logs (Docker)
docker-compose logs -f bot

# Restart bot (Docker)
docker-compose restart bot

# Update configuration
nano .env
docker-compose restart bot  # If using Docker
```

## Configuration Quick Reference

```env
# Required
DISCORD_BOT_TOKEN=your_token
DISCORD_CHANNEL_ID=your_channel_id
CLAUDE_API_KEY=your_key  # OR Gemini OR OpenAI

# Optional
RESPONSE_THRESHOLD=0.6  # Lower = more talkative (0.0-1.0)
BOT_NAME=AI Assistant
MAX_MESSAGE_HISTORY=50
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong_password_here
```

## Support

Need help? Check [Troubleshooting](README.md#troubleshooting) section in README.
