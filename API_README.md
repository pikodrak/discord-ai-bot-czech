# FastAPI Admin Interface

This document describes the FastAPI-based admin interface for managing the Discord AI bot.

## Overview

The admin interface provides a RESTful API for:
- User authentication (JWT-based)
- Bot configuration management
- Bot status monitoring and control
- Real-time statistics

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# FastAPI Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
SECRET_KEY=your-secure-secret-key-here-at-least-32-characters

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# Discord Configuration
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CHANNEL_IDS=channel1,channel2

# AI API Keys (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENAI_API_KEY=sk-...
```

### 3. Start the Server

```bash
# Using the startup script
python run_api.py

# Or directly with uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000

# For development with auto-reload
uvicorn app:app --reload
```

### 4. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Authentication

#### POST /api/auth/login
Login with username and password to receive JWT token.

**Request Body:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Configuration Management

#### GET /api/config/
Get current bot configuration.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "discord_configured": true,
  "ai_provider": "anthropic",
  "bot_settings": {
    "language": "cs",
    "personality": "friendly",
    "response_threshold": 0.6,
    "max_history": 50
  },
  "channels": ["123456789", "987654321"]
}
```

#### PUT /api/config/
Update bot configuration.

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "bot_language": "cs",
  "bot_personality": "friendly",
  "bot_response_threshold": 0.7
}
```

#### POST /api/config/reload
Reload configuration from .env file.

#### GET /api/config/validate
Validate current configuration.

### Bot Management

#### GET /api/bot/status
Get bot status (running, connected, uptime, etc.).

#### POST /api/bot/control
Control bot operations (start, stop, restart).

**Request Body:**
```json
{
  "action": "start"
}
```

#### GET /api/bot/stats
Get bot statistics (messages processed, responses sent, etc.).

## Security

### JWT Token Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-token>
```

Tokens expire after 24 hours by default.

### Secret Key

Generate a secure secret key for production:

```bash
# Generate a random 32-character key
openssl rand -hex 32
```

Add to `.env`:
```
SECRET_KEY=<generated-key>
```

### Password Security

- Passwords are hashed using bcrypt
- Minimum password length: 8 characters
- Change default credentials immediately

## Configuration Options

### FastAPI Settings

| Variable | Default | Description |
|----------|---------|-------------|
| API_HOST | 0.0.0.0 | Server host address |
| API_PORT | 8000 | Server port |
| API_RELOAD | false | Auto-reload on code changes |
| SECRET_KEY | (required) | JWT signing key (min 32 chars) |

### Admin Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| ADMIN_USERNAME | admin | Admin username |
| ADMIN_PASSWORD | (required) | Admin password (min 8 chars) |

### Discord Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| DISCORD_BOT_TOKEN | Yes | Discord bot token |
| DISCORD_GUILD_ID | No | Target server ID |
| DISCORD_CHANNEL_IDS | Yes | Comma-separated channel IDs |

### AI Provider Configuration

At least one AI API key is required:

| Variable | Description |
|----------|-------------|
| ANTHROPIC_API_KEY | Claude API key (preferred) |
| GOOGLE_API_KEY | Gemini API key |
| OPENAI_API_KEY | OpenAI API key |

### Bot Behavior

| Variable | Default | Description |
|----------|---------|-------------|
| BOT_RESPONSE_THRESHOLD | 0.6 | Response confidence threshold (0.0-1.0) |
| BOT_MAX_HISTORY | 50 | Max messages in history (1-200) |
| BOT_LANGUAGE | cs | Bot language code |
| BOT_PERSONALITY | friendly | Bot personality |

## Development

### Running in Development Mode

```bash
# Enable auto-reload
export API_RELOAD=true
python run_api.py
```

### Testing the API

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### API Documentation

The API is self-documenting using OpenAPI/Swagger:

- Interactive docs: http://localhost:8000/docs
- ReDoc format: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Docker Deployment

The FastAPI application is included in the Docker setup:

```bash
# Build and run
docker-compose up -d

# API will be available at http://localhost:8000
```

## Troubleshooting

### Port Already in Use

```bash
# Change port in .env
API_PORT=8001
```

### Configuration Validation Errors

Check configuration with the validate endpoint:

```bash
curl http://localhost:8000/api/config/validate
```

### Import Errors

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### SECRET_KEY Too Short

Generate a proper key:

```bash
openssl rand -hex 32
```

## Architecture

```
app.py                  # Main FastAPI application
├── src/
│   ├── config.py      # Pydantic settings configuration
│   ├── api/
│   │   ├── auth.py    # Authentication endpoints
│   │   ├── config.py  # Configuration endpoints
│   │   └── bot.py     # Bot management endpoints
│   └── auth/
│       ├── security.py    # JWT and password hashing
│       ├── middleware.py  # Auth middleware
│       └── models.py      # Auth data models
└── run_api.py         # Server startup script
```

## Next Steps

1. Configure your Discord bot token
2. Set up at least one AI API key
3. Change default admin credentials
4. Generate a secure SECRET_KEY
5. Start the API server
6. Test endpoints using /docs
7. Integrate with your Discord bot

## Support

For issues and questions, refer to the main README.md or project documentation.
