# API Reference

This document describes the FastAPI admin interface endpoints.

## Base URL

```
http://localhost:8000
```

For production, use your domain with HTTPS:
```
https://bot.yourdomain.com
```

## Authentication

All endpoints (except `/health`) require authentication using HTTP Basic Auth or JWT tokens.

### Basic Authentication

```bash
curl -u admin:password http://localhost:8000/api/config
```

### JWT Authentication

1. **Login to get token**:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

2. **Use token in requests**:

```bash
curl http://localhost:8000/api/config \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Endpoints

### Health Check

Check if the bot and admin interface are running.

**Endpoint**: `GET /health`

**Authentication**: Not required

**Response**:
```json
{
  "status": "healthy",
  "bot_status": "connected",
  "uptime_seconds": 3600,
  "api_providers": {
    "claude": "available",
    "gemini": "available",
    "openai": "unavailable"
  }
}
```

**Example**:
```bash
curl http://localhost:8000/health
```

---

### Get Configuration

Retrieve current bot configuration.

**Endpoint**: `GET /api/config`

**Authentication**: Required

**Response**:
```json
{
  "discord": {
    "bot_token": "***************xyz",
    "channel_id": "123456789012345678",
    "channel_name": "general"
  },
  "bot": {
    "name": "AI Assistant",
    "response_threshold": 0.6,
    "max_message_history": 50
  },
  "ai_providers": {
    "claude": {
      "enabled": true,
      "api_key": "***************xyz",
      "model": "claude-3-5-sonnet-20240620"
    },
    "gemini": {
      "enabled": true,
      "api_key": "***************xyz",
      "model": "gemini-pro"
    },
    "openai": {
      "enabled": false,
      "api_key": null,
      "model": "gpt-4-turbo-preview"
    }
  }
}
```

**Example**:
```bash
curl -u admin:password http://localhost:8000/api/config
```

---

### Update Configuration

Update bot configuration. Bot will restart with new settings.

**Endpoint**: `POST /api/config`

**Authentication**: Required

**Request Body**:
```json
{
  "discord_token": "new_token_here",
  "channel_id": "987654321098765432",
  "bot_name": "AI Assistant",
  "response_threshold": 0.7,
  "max_message_history": 100,
  "claude_api_key": "sk-ant-new_key",
  "gemini_api_key": "new_gemini_key",
  "openai_api_key": "sk-new_openai_key"
}
```

All fields are optional. Only provide fields you want to update.

**Response**:
```json
{
  "status": "success",
  "message": "Configuration updated successfully",
  "restart_required": true
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/config \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "response_threshold": 0.7,
    "bot_name": "Czech Bot"
  }'
```

---

### Bot Status

Get detailed bot status and statistics.

**Endpoint**: `GET /api/status`

**Authentication**: Required

**Response**:
```json
{
  "bot": {
    "is_ready": true,
    "connected": true,
    "user": "BotName#1234",
    "guilds_count": 5,
    "uptime_seconds": 7200
  },
  "channel": {
    "id": "123456789012345678",
    "name": "general",
    "guild": "My Server"
  },
  "statistics": {
    "messages_received": 1523,
    "messages_responded": 89,
    "response_rate": 0.058,
    "api_calls": {
      "claude": 45,
      "gemini": 30,
      "openai": 14
    }
  }
}
```

**Example**:
```bash
curl -u admin:password http://localhost:8000/api/status
```

---

### Restart Bot

Restart the Discord bot with current configuration.

**Endpoint**: `POST /api/restart`

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "message": "Bot is restarting..."
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/restart \
  -u admin:password
```

---

### Get Logs

Retrieve bot logs.

**Endpoint**: `GET /api/logs`

**Authentication**: Required

**Query Parameters**:
- `limit` (optional): Number of log lines (default: 100, max: 1000)
- `level` (optional): Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `since` (optional): ISO 8601 timestamp to get logs after

**Response**:
```json
{
  "logs": [
    {
      "timestamp": "2026-03-13T10:15:30.123456",
      "level": "INFO",
      "message": "Bot connected to channel: general"
    },
    {
      "timestamp": "2026-03-13T10:16:45.789012",
      "level": "INFO",
      "message": "Received message from user123"
    }
  ],
  "total": 2,
  "filtered": true
}
```

**Examples**:

Get last 50 logs:
```bash
curl -u admin:password "http://localhost:8000/api/logs?limit=50"
```

Get only errors:
```bash
curl -u admin:password "http://localhost:8000/api/logs?level=ERROR"
```

Get logs since timestamp:
```bash
curl -u admin:password "http://localhost:8000/api/logs?since=2026-03-13T10:00:00"
```

---

### Get Statistics

Get detailed usage statistics.

**Endpoint**: `GET /api/stats`

**Authentication**: Required

**Query Parameters**:
- `period` (optional): Time period (hour, day, week, month, all)

**Response**:
```json
{
  "period": "day",
  "timestamp": "2026-03-13T17:00:00",
  "messages": {
    "received": 1523,
    "processed": 1489,
    "responded": 89,
    "ignored": 1400,
    "errors": 34
  },
  "api_usage": {
    "claude": {
      "calls": 45,
      "success": 43,
      "errors": 2,
      "avg_response_time_ms": 1250
    },
    "gemini": {
      "calls": 30,
      "success": 28,
      "errors": 2,
      "avg_response_time_ms": 890
    },
    "openai": {
      "calls": 14,
      "success": 12,
      "errors": 2,
      "avg_response_time_ms": 1580
    }
  },
  "response_quality": {
    "avg_interest_score": 0.72,
    "threshold": 0.6,
    "above_threshold": 89,
    "below_threshold": 1400
  }
}
```

**Example**:
```bash
curl -u admin:password "http://localhost:8000/api/stats?period=week"
```

---

### Test API Connection

Test connection to AI provider APIs.

**Endpoint**: `POST /api/test-connection`

**Authentication**: Required

**Request Body**:
```json
{
  "provider": "claude"
}
```

Providers: `claude`, `gemini`, `openai`

**Response**:
```json
{
  "provider": "claude",
  "status": "success",
  "response_time_ms": 1234,
  "model": "claude-3-5-sonnet-20240620",
  "message": "Connection successful"
}
```

**Error Response**:
```json
{
  "provider": "claude",
  "status": "error",
  "error": "Invalid API key",
  "message": "Failed to connect to Claude API"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/test-connection \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"provider": "claude"}'
```

---

### Send Test Message

Send a test message to the Discord channel.

**Endpoint**: `POST /api/test-message`

**Authentication**: Required

**Request Body**:
```json
{
  "content": "Test message from admin interface"
}
```

**Response**:
```json
{
  "status": "success",
  "message_id": "1234567890123456789",
  "channel": "general",
  "timestamp": "2026-03-13T17:30:00"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/test-message \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello from API!"}'
```

---

### Update Admin Password

Change the admin interface password.

**Endpoint**: `POST /api/admin/password`

**Authentication**: Required

**Request Body**:
```json
{
  "current_password": "old_password",
  "new_password": "new_secure_password"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Password updated successfully"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/admin/password \
  -u admin:old_password \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "old_password",
    "new_password": "new_secure_password"
  }'
```

---

## Error Responses

All endpoints may return these error responses:

### 401 Unauthorized
```json
{
  "detail": "Invalid authentication credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "response_threshold"],
      "msg": "value must be between 0 and 1",
      "type": "value_error"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "error": "Error message details"
}
```

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- **Health endpoint**: 60 requests/minute
- **Read endpoints** (GET): 30 requests/minute
- **Write endpoints** (POST): 10 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1710349200
```

## WebSocket Support

Real-time updates via WebSocket:

**Endpoint**: `WS /ws/logs`

**Authentication**: Send token as first message

**Example** (JavaScript):
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/logs');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your_jwt_token'
  }));
};

ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(log);
};
```

**Message Format**:
```json
{
  "type": "log",
  "timestamp": "2026-03-13T17:30:00",
  "level": "INFO",
  "message": "Bot received message"
}
```

## SDK Examples

### Python

```python
import requests

class BotAdminClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth = (username, password)
    
    def get_status(self):
        response = requests.get(
            f"{self.base_url}/api/status",
            auth=self.auth
        )
        return response.json()
    
    def update_config(self, **kwargs):
        response = requests.post(
            f"{self.base_url}/api/config",
            auth=self.auth,
            json=kwargs
        )
        return response.json()
    
    def restart_bot(self):
        response = requests.post(
            f"{self.base_url}/api/restart",
            auth=self.auth
        )
        return response.json()

# Usage
client = BotAdminClient("http://localhost:8000", "admin", "password")
status = client.get_status()
print(status)
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

class BotAdminClient {
  constructor(baseURL, username, password) {
    this.client = axios.create({
      baseURL,
      auth: { username, password }
    });
  }

  async getStatus() {
    const response = await this.client.get('/api/status');
    return response.data;
  }

  async updateConfig(config) {
    const response = await this.client.post('/api/config', config);
    return response.data;
  }

  async restartBot() {
    const response = await this.client.post('/api/restart');
    return response.data;
  }
}

// Usage
const client = new BotAdminClient('http://localhost:8000', 'admin', 'password');
client.getStatus().then(console.log);
```

### cURL Scripts

Save as `bot-admin.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
AUTH="admin:password"

# Get status
function get_status() {
  curl -s -u "$AUTH" "$BASE_URL/api/status" | jq
}

# Update threshold
function set_threshold() {
  curl -s -u "$AUTH" -X POST "$BASE_URL/api/config" \
    -H "Content-Type: application/json" \
    -d "{\"response_threshold\": $1}" | jq
}

# Restart bot
function restart() {
  curl -s -u "$AUTH" -X POST "$BASE_URL/api/restart" | jq
}

# Get logs
function logs() {
  curl -s -u "$AUTH" "$BASE_URL/api/logs?limit=${1:-100}" | jq
}

# Run command
case "$1" in
  status) get_status ;;
  threshold) set_threshold "$2" ;;
  restart) restart ;;
  logs) logs "$2" ;;
  *) echo "Usage: $0 {status|threshold|restart|logs}" ;;
esac
```

Usage:
```bash
chmod +x bot-admin.sh
./bot-admin.sh status
./bot-admin.sh threshold 0.7
./bot-admin.sh logs 50
```

## Webhooks

Configure webhooks to receive notifications:

**Endpoint**: `POST /api/webhooks`

**Request Body**:
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["message_sent", "error", "bot_restart"],
  "secret": "your_webhook_secret"
}
```

**Webhook Payload**:
```json
{
  "event": "message_sent",
  "timestamp": "2026-03-13T17:30:00",
  "data": {
    "message_id": "1234567890",
    "content": "Response text",
    "channel": "general"
  },
  "signature": "sha256=..."
}
```

## Support

For API issues or questions:
- Check [README.md](../README.md) for setup
- Review [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
- Open GitHub issue with request/response details
