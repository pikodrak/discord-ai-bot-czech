# Bot Restart Mechanism Guide

## Overview

The Discord bot includes a comprehensive restart mechanism that allows graceful process management through the FastAPI admin interface. This enables configuration changes to be applied without manual intervention.

## Architecture

### Components

1. **BotProcessManager** (`src/bot_process_manager.py`)
   - Manages the bot process lifecycle
   - Handles start, stop, and restart operations
   - Tracks process state and resource usage
   - Implements graceful shutdown with timeout
   - Provides process recovery on startup

2. **Bot API Router** (`src/api/bot.py`)
   - Exposes REST endpoints for bot control
   - Integrates with BotProcessManager
   - Provides status monitoring and statistics
   - Handles error cases and validation

3. **Process State Management**
   - PID file tracking in `data/bot.pid`
   - Process state monitoring
   - Resource usage tracking (CPU, memory)
   - Automatic recovery on API startup

## API Endpoints

### GET /api/bot/status

Get current bot status including process information and resource usage.

**Response:**
```json
{
  "running": true,
  "state": "running",
  "pid": 12345,
  "uptime_seconds": 3600.5,
  "cpu_percent": 2.5,
  "memory_mb": 125.3,
  "restart_count": 2,
  "started_at": "2026-03-14T20:00:00"
}
```

**States:**
- `stopped` - Bot is not running
- `starting` - Bot is being started
- `running` - Bot is running normally
- `stopping` - Bot is being stopped
- `restarting` - Bot is being restarted
- `error` - Bot encountered an error

### POST /api/bot/restart

**Recommended endpoint** for restarting the bot after configuration changes.

**Request:**
```json
{
  "timeout": 10.0,
  "env_vars": {
    "ENVIRONMENT": "production",
    "LOG_LEVEL": "INFO"
  }
}
```

**Parameters:**
- `timeout` (float, optional): Maximum seconds to wait for shutdown (default: 10.0, range: 1-60)
- `env_vars` (dict, optional): Environment variables to pass to the new process

**Response:**
```json
{
  "success": true,
  "message": "Bot restarted successfully",
  "previous_state": "running",
  "current_state": "running",
  "pid": 12346,
  "restart_count": 3
}
```

### POST /api/bot/control

Generic control endpoint for start, stop, or restart operations.

**Request:**
```json
{
  "action": "restart",
  "timeout": 10.0,
  "env_vars": {}
}
```

**Parameters:**
- `action` (string, required): One of `start`, `stop`, or `restart`
- `timeout` (float, optional): Timeout for stop operation (default: 10.0)
- `env_vars` (dict, optional): Environment variables for start/restart

**Response:**
```json
{
  "success": true,
  "message": "Bot restarted successfully",
  "action": "restart",
  "current_state": "running",
  "pid": 12346
}
```

### GET /api/bot/stats

Get bot statistics including resource usage.

**Response:**
```json
{
  "total_messages_processed": 0,
  "total_responses_sent": 0,
  "ai_provider_usage": {
    "anthropic": 0,
    "google": 0,
    "openai": 0
  },
  "average_response_time_ms": 0.0,
  "uptime_hours": 1.5,
  "memory_usage_mb": 125.3,
  "cpu_usage_percent": 2.5
}
```

Note: Message and provider statistics are placeholders for future implementation.

### GET /api/bot/health

Health check endpoint for monitoring.

**Response:**
```json
{
  "healthy": true,
  "running": true,
  "state": "running",
  "pid": 12345,
  "uptime_seconds": 3600.5
}
```

## Usage Examples

### Restart Bot via API

Using curl:
```bash
curl -X POST http://localhost:8080/api/bot/restart \
  -H "Content-Type: application/json" \
  -d '{"timeout": 15.0}'
```

Using Python:
```python
import requests

response = requests.post(
    "http://localhost:8080/api/bot/restart",
    json={"timeout": 15.0}
)

if response.status_code == 200:
    result = response.json()
    print(f"Restart successful! New PID: {result['pid']}")
else:
    print(f"Restart failed: {response.text}")
```

Using JavaScript:
```javascript
fetch('http://localhost:8080/api/bot/restart', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({timeout: 15.0})
})
.then(res => res.json())
.then(data => console.log('Restart successful!', data))
.catch(err => console.error('Restart failed:', err));
```

### Check Bot Status

```bash
curl http://localhost:8080/api/bot/status
```

### Stop Bot

```bash
curl -X POST http://localhost:8080/api/bot/control \
  -H "Content-Type: application/json" \
  -d '{"action": "stop", "timeout": 10.0}'
```

### Start Bot

```bash
curl -X POST http://localhost:8080/api/bot/control \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'
```

## Workflow: Configuration Change

1. **Update configuration** via config API:
   ```bash
   curl -X POST http://localhost:8080/api/config/update \
     -H "Content-Type: application/json" \
     -d '{"ai_provider": "anthropic", "log_level": "DEBUG"}'
   ```

2. **Restart bot** to apply changes:
   ```bash
   curl -X POST http://localhost:8080/api/bot/restart
   ```

3. **Verify bot is running** with new config:
   ```bash
   curl http://localhost:8080/api/bot/status
   ```

## Process Management Details

### Graceful Shutdown

When stopping or restarting, the bot process manager:

1. Sends SIGTERM signal to the bot process
2. Waits for graceful shutdown (default: 10 seconds)
3. Bot runs shutdown hooks:
   - Saves state
   - Closes connections
   - Cleans up resources
4. If timeout expires, sends SIGKILL to force termination
5. Cleans up PID file

### Process Recovery

On API server startup, the BotProcessManager:

1. Checks for existing PID file in `data/bot.pid`
2. Verifies the process is still running
3. Validates it's the correct bot process
4. Recovers process state and monitoring
5. Cleans up stale PID files if process is dead

### Resource Monitoring

The manager tracks:
- **CPU usage** - Percentage of CPU used by bot process
- **Memory usage** - RAM usage in megabytes
- **Uptime** - Time since bot started
- **Restart count** - Number of restarts performed

### Error Handling

Common error scenarios:

1. **Bot already running** (on start):
   - Returns HTTP 409 Conflict
   - Message: "Bot is already running"

2. **Bot not running** (on stop):
   - Returns success (idempotent)
   - Message: "Bot is already stopped"

3. **Bot script not found**:
   - Returns HTTP 500 Internal Server Error
   - Message: "Bot script not found: /path/to/main.py"

4. **Restart timeout**:
   - Forces kill after timeout
   - Logs warning about forced termination
   - Continues with restart

5. **Process manager not initialized**:
   - Returns HTTP 503 Service Unavailable
   - Message: "Bot manager not initialized"

## Security Considerations

### Process Isolation

- Bot runs in separate process from API server
- Process groups prevent signal propagation
- Clean separation of concerns

### Environment Variables

- Can pass environment variables during restart
- Useful for applying configuration changes
- Avoid passing secrets via API (use .env file instead)

### Authentication

- All bot control endpoints should be protected by authentication
- Use JWT tokens from `/api/auth/login`
- Configure proper CORS settings

Example with authentication:
```bash
# Login first
TOKEN=$(curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}' \
  | jq -r '.access_token')

# Use token to restart bot
curl -X POST http://localhost:8080/api/bot/restart \
  -H "Authorization: Bearer $TOKEN"
```

## Testing

Run the test suite:
```bash
python3 test_bot_restart.py
```

The test verifies:
- ✓ BotProcessManager initialization
- ✓ Process state tracking
- ✓ PID file management
- ✓ Process recovery on startup
- ✓ Resource monitoring
- ✓ Graceful restart mechanism
- ✓ API integration

## Troubleshooting

### Bot won't start

1. Check if bot is already running:
   ```bash
   curl http://localhost:8080/api/bot/status
   ```

2. Check if main.py exists:
   ```bash
   ls -la main.py
   ```

3. Check bot logs:
   ```bash
   tail -f logs/bot.log
   ```

### Bot won't stop

1. Check process status:
   ```bash
   curl http://localhost:8080/api/bot/status
   ```

2. Increase timeout:
   ```bash
   curl -X POST http://localhost:8080/api/bot/control \
     -d '{"action": "stop", "timeout": 30.0}'
   ```

3. Manually kill if necessary:
   ```bash
   cat data/bot.pid
   kill <PID>
   ```

### Restart fails

1. Check API logs:
   ```bash
   tail -f logs/api.log
   ```

2. Verify enough time for shutdown:
   - Increase timeout in restart request
   - Default 10s should be sufficient

3. Check system resources:
   - Ensure enough RAM available
   - Check disk space for logs

### PID file issues

If PID file becomes stale:
```bash
rm data/bot.pid
# Restart API to recover
```

## Future Enhancements

Planned improvements:

1. **Metrics Collection**
   - Implement actual message/response tracking
   - AI provider usage statistics
   - Response time monitoring

2. **Auto-restart on Crash**
   - Monitor bot health
   - Automatic restart on failure
   - Configurable retry policies

3. **Log Streaming**
   - Real-time log streaming via WebSocket
   - Filter logs by level
   - Search log history

4. **Scheduled Restarts**
   - Configure restart schedules
   - Maintenance windows
   - Automatic updates

5. **Multi-instance Support**
   - Manage multiple bot instances
   - Load balancing
   - Rolling restarts

## Related Documentation

- [API README](../API_README.md) - General API documentation
- [FastAPI Setup](../FASTAPI_SETUP_COMPLETE.md) - Admin interface setup
- [Configuration Management](../docs/configuration.md) - Config system details
- [Deployment Guide](../DEPLOYMENT.md) - Production deployment
