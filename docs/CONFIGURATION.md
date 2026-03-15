# Configuration Reference

Complete reference for all configuration options.

## Configuration Methods

The bot supports multiple configuration methods:

1. **Environment variables** (`.env` file) - Recommended for deployment
2. **Configuration file** (`config/config.yml`) - For advanced settings
3. **Admin interface** - Runtime configuration changes

### Priority Order

Admin interface > Environment variables > Config file > Defaults

## Environment Variables

### Discord Configuration

#### DISCORD_BOT_TOKEN
- **Required**: Yes
- **Type**: String
- **Description**: Your Discord bot token from Developer Portal
- **Example**: `YOUR_DISCORD_BOT_TOKEN_HERE`
- **Security**: Keep secret, never commit to git

#### DISCORD_CHANNEL_ID
- **Required**: Yes
- **Type**: String (numeric)
- **Description**: Discord channel ID where bot participates
- **Example**: `123456789012345678`
- **How to get**: Enable Developer Mode → Right-click channel → Copy ID

#### DISCORD_GUILD_ID
- **Required**: No
- **Type**: String (numeric)
- **Description**: Restrict bot to specific server (optional)
- **Example**: `987654321098765432`
- **Default**: All servers where bot is member

### AI Provider Configuration

#### CLAUDE_API_KEY
- **Required**: No (but at least one AI key required)
- **Type**: String
- **Description**: Anthropic Claude API key
- **Example**: `sk-ant-api03-abc123...`
- **Get it**: https://console.anthropic.com/
- **Cost**: ~$3-15 per 1M tokens

#### GEMINI_API_KEY
- **Required**: No
- **Type**: String
- **Description**: Google Gemini API key
- **Example**: `AIzaSyAbc123...`
- **Get it**: https://makersuite.google.com/app/apikey
- **Cost**: Free tier available

#### OPENAI_API_KEY
- **Required**: No
- **Type**: String
- **Description**: OpenAI API key
- **Example**: `sk-abc123...`
- **Get it**: https://platform.openai.com/
- **Cost**: Varies by model

#### AI_PROVIDER_PRIORITY
- **Required**: No
- **Type**: Comma-separated list
- **Description**: Order to try AI providers
- **Example**: `claude,gemini,openai`
- **Default**: `claude,gemini,openai`

#### CLAUDE_MODEL
- **Required**: No
- **Type**: String
- **Description**: Claude model to use
- **Default**: `claude-3-5-sonnet-20240620`
- **Options**: 
  - `claude-3-5-sonnet-20240620` (Recommended)
  - `claude-3-opus-20240229` (Most capable, expensive)
  - `claude-3-haiku-20240307` (Fast, cheaper)

#### GEMINI_MODEL
- **Required**: No
- **Type**: String
- **Description**: Gemini model to use
- **Default**: `gemini-pro`
- **Options**: `gemini-pro`, `gemini-pro-vision`

#### OPENAI_MODEL
- **Required**: No
- **Type**: String
- **Description**: OpenAI model to use
- **Default**: `gpt-4-turbo-preview`
- **Options**: `gpt-4-turbo-preview`, `gpt-3.5-turbo`, `gpt-4`

### Bot Behavior Configuration

#### BOT_NAME
- **Required**: No
- **Type**: String
- **Description**: Bot's display name in responses
- **Default**: `AI Assistant`
- **Example**: `Czech Bot`

#### RESPONSE_THRESHOLD
- **Required**: No
- **Type**: Float (0.0 - 1.0)
- **Description**: Minimum interest score to respond
- **Default**: `0.6`
- **Recommendations**:
  - `0.3-0.4`: Very talkative, responds often
  - `0.5-0.6`: Balanced, responds to interesting messages
  - `0.7-0.8`: Selective, only very interesting messages
  - `0.9+`: Rarely responds

#### MAX_MESSAGE_HISTORY
- **Required**: No
- **Type**: Integer
- **Description**: Number of messages to keep in context
- **Default**: `50`
- **Range**: 10-200
- **Impact**: Higher = better context, more API cost

#### LANGUAGE
- **Required**: No
- **Type**: String
- **Description**: Primary language for responses
- **Default**: `cs` (Czech)
- **Options**: `cs`, `en`, `sk`, etc.

#### PERSONALITY
- **Required**: No
- **Type**: String
- **Description**: Bot personality/style
- **Default**: `friendly`
- **Options**: `friendly`, `formal`, `casual`, `humorous`

#### RESPONSE_DELAY_MIN
- **Required**: No
- **Type**: Integer (seconds)
- **Description**: Minimum delay before responding
- **Default**: `1`
- **Purpose**: Appear more human-like

#### RESPONSE_DELAY_MAX
- **Required**: No
- **Type**: Integer (seconds)
- **Description**: Maximum delay before responding
- **Default**: `3`
- **Purpose**: Randomize response timing

#### TYPING_INDICATOR
- **Required**: No
- **Type**: Boolean
- **Description**: Show typing indicator before responding
- **Default**: `true`
- **Purpose**: More natural interaction

### Admin Interface Configuration

#### ADMIN_USERNAME
- **Required**: No
- **Type**: String
- **Description**: Admin interface username
- **Default**: `admin`
- **Security**: Change immediately in production!

#### ADMIN_PASSWORD
- **Required**: No
- **Type**: String
- **Description**: Admin interface password
- **Default**: `admin`
- **Security**: Use strong password in production!

#### ADMIN_PORT
- **Required**: No
- **Type**: Integer
- **Description**: Port for admin interface
- **Default**: `8000`
- **Range**: 1024-65535

#### ADMIN_HOST
- **Required**: No
- **Type**: String
- **Description**: Host to bind admin interface
- **Default**: `0.0.0.0`
- **Options**: `0.0.0.0` (all interfaces), `127.0.0.1` (localhost only)

#### ADMIN_CORS_ORIGINS
- **Required**: No
- **Type**: Comma-separated list
- **Description**: Allowed CORS origins
- **Default**: `*`
- **Example**: `https://yourdomain.com,https://admin.yourdomain.com`

#### JWT_SECRET_KEY
- **Required**: No
- **Type**: String
- **Description**: Secret key for JWT tokens
- **Default**: Auto-generated
- **Security**: Set manually for production

#### JWT_EXPIRATION_HOURS
- **Required**: No
- **Type**: Integer
- **Description**: JWT token expiration time
- **Default**: `24`
- **Range**: 1-720 (1 hour to 30 days)

### Logging Configuration

#### LOG_LEVEL
- **Required**: No
- **Type**: String
- **Description**: Logging verbosity
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

#### LOG_FILE
- **Required**: No
- **Type**: String
- **Description**: Path to log file
- **Default**: `logs/bot.log`

#### LOG_MAX_SIZE_MB
- **Required**: No
- **Type**: Integer
- **Description**: Maximum log file size before rotation
- **Default**: `10`

#### LOG_BACKUP_COUNT
- **Required**: No
- **Type**: Integer
- **Description**: Number of backup log files to keep
- **Default**: `5`

#### LOG_FORMAT
- **Required**: No
- **Type**: String
- **Description**: Log message format
- **Default**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Rate Limiting Configuration

#### RATE_LIMIT_MESSAGES
- **Required**: No
- **Type**: Integer
- **Description**: Max messages to process per minute
- **Default**: `60`
- **Purpose**: Prevent spam

#### RATE_LIMIT_API_CALLS
- **Required**: No
- **Type**: Integer
- **Description**: Max API calls per minute
- **Default**: `30`
- **Purpose**: Control API costs

#### COOLDOWN_SECONDS
- **Required**: No
- **Type**: Integer
- **Description**: Cooldown between bot responses
- **Default**: `5`
- **Purpose**: Prevent flooding

### Advanced Configuration

#### DEBUG
- **Required**: No
- **Type**: Boolean
- **Description**: Enable debug mode
- **Default**: `false`
- **Usage**: `DEBUG=true`

#### DRY_RUN
- **Required**: No
- **Type**: Boolean
- **Description**: Process messages but don't send responses
- **Default**: `false`
- **Usage**: Testing mode

#### CACHE_ENABLED
- **Required**: No
- **Type**: Boolean
- **Description**: Cache AI responses for similar messages
- **Default**: `true`

#### CACHE_TTL_SECONDS
- **Required**: No
- **Type**: Integer
- **Description**: Cache entry time-to-live
- **Default**: `3600` (1 hour)

#### DATABASE_URL
- **Required**: No
- **Type**: String
- **Description**: Database connection string
- **Default**: `sqlite:///data/bot.db`
- **Example**: `postgresql://user:pass@localhost/botdb`

## Configuration File (config/config.yml)

For advanced configuration, create `config/config.yml`:

```yaml
discord:
  bot_token: ${DISCORD_BOT_TOKEN}
  channel_id: ${DISCORD_CHANNEL_ID}
  guild_id: ${DISCORD_GUILD_ID}

ai:
  providers:
    - name: claude
      enabled: true
      api_key: ${CLAUDE_API_KEY}
      model: claude-3-5-sonnet-20240620
      max_tokens: 1000
      temperature: 0.7
    
    - name: gemini
      enabled: true
      api_key: ${GEMINI_API_KEY}
      model: gemini-pro
      max_tokens: 1000
      temperature: 0.7
    
    - name: openai
      enabled: false
      api_key: ${OPENAI_API_KEY}
      model: gpt-4-turbo-preview
      max_tokens: 1000
      temperature: 0.7

bot:
  name: AI Assistant
  response_threshold: 0.6
  max_message_history: 50
  language: cs
  personality: friendly
  
  timing:
    response_delay_min: 1
    response_delay_max: 3
    typing_indicator: true
  
  filters:
    ignore_bots: true
    ignore_commands: true
    min_message_length: 5
    blacklist_users: []
    whitelist_channels: []

admin:
  username: ${ADMIN_USERNAME}
  password: ${ADMIN_PASSWORD}
  port: 8000
  host: 0.0.0.0
  
  security:
    jwt_secret: ${JWT_SECRET_KEY}
    jwt_expiration_hours: 24
    cors_origins: ["*"]
    rate_limit: 30

logging:
  level: INFO
  file: logs/bot.log
  max_size_mb: 10
  backup_count: 5
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

features:
  cache_enabled: true
  cache_ttl_seconds: 3600
  rate_limiting_enabled: true
  metrics_enabled: true
```

## Environment-Specific Configuration

### Development (.env.development)

```env
DISCORD_BOT_TOKEN=your_dev_token
DISCORD_CHANNEL_ID=your_test_channel
CLAUDE_API_KEY=your_key

# Verbose logging
LOG_LEVEL=DEBUG

# Lower threshold for testing
RESPONSE_THRESHOLD=0.3

# Faster responses
RESPONSE_DELAY_MIN=0
RESPONSE_DELAY_MAX=1

# No rate limiting
RATE_LIMIT_MESSAGES=1000
```

### Production (.env.production)

```env
DISCORD_BOT_TOKEN=your_prod_token
DISCORD_CHANNEL_ID=your_prod_channel
CLAUDE_API_KEY=your_key

# Production logging
LOG_LEVEL=INFO

# Balanced threshold
RESPONSE_THRESHOLD=0.6

# Human-like timing
RESPONSE_DELAY_MIN=2
RESPONSE_DELAY_MAX=5

# Rate limiting
RATE_LIMIT_MESSAGES=30

# Strong admin credentials
ADMIN_USERNAME=admin_prod
ADMIN_PASSWORD=very_strong_password_here

# Security
JWT_SECRET_KEY=your_secret_key_here
ADMIN_CORS_ORIGINS=https://yourdomain.com
```

## Configuration Validation

The bot validates configuration on startup:

```python
# Example validation errors:
ERROR: DISCORD_BOT_TOKEN is required
ERROR: At least one AI API key must be provided
ERROR: RESPONSE_THRESHOLD must be between 0.0 and 1.0
ERROR: ADMIN_PORT must be between 1024 and 65535
WARNING: Using default admin password (change immediately!)
```

## Dynamic Configuration Updates

Some settings can be updated at runtime via admin interface:

**Hot-reload supported** (no restart required):
- RESPONSE_THRESHOLD
- BOT_NAME
- MAX_MESSAGE_HISTORY
- TYPING_INDICATOR
- LOG_LEVEL

**Requires restart**:
- DISCORD_BOT_TOKEN
- DISCORD_CHANNEL_ID
- AI API keys
- ADMIN_PORT

## Configuration Best Practices

1. **Never commit secrets**: Use `.env` and add to `.gitignore`
2. **Use strong passwords**: Especially for admin interface
3. **Start conservative**: High threshold (0.7), test and adjust
4. **Monitor costs**: Track API usage, set limits
5. **Enable logging**: Keep LOG_LEVEL=INFO minimum
6. **Regular backups**: Backup configuration files
7. **Document changes**: Comment why you changed defaults

## Troubleshooting Configuration

### Bot won't start

Check required variables:
```bash
grep -E "DISCORD_BOT_TOKEN|DISCORD_CHANNEL_ID|CLAUDE_API_KEY" .env
```

### Configuration not applied

Check priority order:
1. Admin interface (highest)
2. Environment variables
3. Config file
4. Defaults (lowest)

### Invalid values

Run validation:
```bash
python src/validate_config.py
```

## Example Configurations

### Minimal Configuration

```env
DISCORD_BOT_TOKEN=your_token
DISCORD_CHANNEL_ID=your_channel
CLAUDE_API_KEY=your_key
```

### Recommended Configuration

```env
# Discord
DISCORD_BOT_TOKEN=your_token
DISCORD_CHANNEL_ID=your_channel

# AI
CLAUDE_API_KEY=your_claude_key
GEMINI_API_KEY=your_gemini_key

# Bot behavior
RESPONSE_THRESHOLD=0.6
MAX_MESSAGE_HISTORY=50
BOT_NAME=AI Assistant

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong_password_here
ADMIN_PORT=8000

# Logging
LOG_LEVEL=INFO
```

### Full Configuration

See `.env.example` for complete template with all options.

## Support

For configuration issues:
- Check [Troubleshooting](../README.md#troubleshooting)
- Validate with `python src/validate_config.py`
- Review logs: `tail -f logs/bot.log`
