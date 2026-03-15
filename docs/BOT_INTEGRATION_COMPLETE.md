# Discord Bot Integration Complete

This document describes the integration between the FastAPI admin interface and the Discord bot process, including shared configuration management, hot-reload capability, and inter-process communication.

## Overview

The Discord bot now integrates with the FastAPI admin interface through:

1. **Shared Configuration Storage** - Both processes read/write from a common configuration source
2. **Hot-Reload Capability** - Bot can reload configuration without restarting
3. **IPC Communication** - Admin interface can send commands to the bot process
4. **Process Management** - Admin interface can start, stop, and restart the bot

## Architecture

### Components

#### 1. Shared Configuration Loader (`src/shared_config.py`)

- Manages runtime configuration in `data/runtime_config.json`
- Thread-safe configuration updates
- Validates configuration before saving
- Loads from environment/YAML as fallback
- Used by both bot and API processes

**Key Functions:**
- `get_shared_config_loader()` - Get global config loader instance
- `load_bot_config_from_shared()` - Load config for bot
- `save_bot_config_to_shared()` - Save config from API

#### 2. IPC Communication Channel (`src/ipc.py`)

- File-based IPC using JSON signals
- Command/response pattern
- Status updates from bot to API
- Non-blocking signal processing

**IPC Commands:**
- `RELOAD_CONFIG` - Reload bot configuration
- `SHUTDOWN` - Gracefully shutdown bot
- `PING` - Health check
- `RESTART` - Restart bot process

**Files:**
- `data/ipc/signal.json` - Command signals
- `data/ipc/response.json` - Command responses
- `data/ipc/status.json` - Bot status updates

#### 3. Bot Process Manager (`src/bot_process_manager.py`)

- Manages Discord bot subprocess
- Start, stop, restart operations
- Process monitoring and resource tracking
- Graceful shutdown handling

**Process States:**
- `STOPPED` - Bot is not running
- `STARTING` - Bot is starting up
- `RUNNING` - Bot is active
- `STOPPING` - Bot is shutting down
- `ERROR` - Bot encountered an error

#### 4. Enhanced Bot Main (`main.py`)

Modified Discord bot with:
- Loads config from shared storage
- IPC signal processing loop
- Hot-reload handler
- Status updates to admin interface

**New Features:**
- Configuration reload without restart
- IPC command handlers
- Periodic status updates
- Graceful IPC cleanup

## Usage

### Starting the Bot

```python
# Via API endpoint
POST /api/bot/control
{
    "action": "start",
    "env_vars": {
        "LOG_LEVEL": "DEBUG"
    }
}
```

```bash
# Direct execution
python main.py
```

### Hot-Reloading Configuration

```python
# Update config via API
PATCH /api/config/behavior
{
    "bot_response_threshold": 0.8
}

# Trigger hot-reload
POST /api/config/hot-reload
```

The bot will reload configuration without disconnecting from Discord.

### Restarting the Bot

```python
# Via API endpoint
POST /api/bot/restart
{
    "timeout": 10.0
}
```

This performs a graceful restart:
1. Sends SIGTERM to bot process
2. Waits for clean shutdown (up to timeout)
3. Starts new bot process
4. Verifies new process is running

### Monitoring Bot Status

```python
# Get current status
GET /api/bot/status

# Response:
{
    "running": true,
    "state": "running",
    "pid": 12345,
    "uptime_seconds": 3600.5,
    "cpu_percent": 2.5,
    "memory_mb": 128.4,
    "restart_count": 0,
    "started_at": "2024-03-14T10:30:00"
}
```

### Getting Bot Statistics

```python
GET /api/bot/stats

# Response:
{
    "total_messages_processed": 0,
    "total_responses_sent": 0,
    "ai_provider_usage": {
        "anthropic": 0,
        "google": 0,
        "openai": 0
    },
    "average_response_time_ms": 0.0,
    "uptime_hours": 1.0,
    "memory_usage_mb": 128.4,
    "cpu_usage_percent": 2.5
}
```

## Configuration Flow

### 1. Initial Configuration Load

```
Environment Variables → YAML Files → Shared Storage → Bot Process
```

1. Bot reads from `data/runtime_config.json` if exists
2. Falls back to environment variables and YAML
3. Saves to shared storage for future use

### 2. Configuration Update

```
Admin UI → FastAPI API → Shared Storage → IPC Signal → Bot Reload
```

1. User updates config via admin interface
2. FastAPI saves to `.env` and shared storage
3. FastAPI sends `RELOAD_CONFIG` IPC signal
4. Bot receives signal and reloads configuration
5. Bot responds with success/failure

### 3. Configuration Validation

All configuration changes are validated before saving:
- Required fields presence
- Type checking
- Value constraints
- API key format validation

## Implementation Details

### IPC Signal Processing

The bot runs an IPC processing loop that:
1. Checks for signals every 1 second
2. Processes commands via registered handlers
3. Sends responses back to admin interface
4. Updates status information

```python
async def _process_ipc_loop(self):
    while not self.is_closed():
        await self.ipc_channel.process_signals()
        self.ipc_channel.update_status({
            "running": True,
            "guilds": len(self.guilds),
            "latency_ms": round(self.latency * 1000, 2)
        })
        await asyncio.sleep(1.0)
```

### Configuration Reload Handler

When receiving a reload command, the bot:
1. Loads fresh config from shared storage
2. Creates new config object with validation
3. Reconfigures logger if needed
4. Continues running with new settings

```python
async def handle_reload_config(signal: IPCSignal):
    shared_loader = get_shared_config_loader(project_root)
    new_config_dict = shared_loader.load_config(force_reload=True)
    self.config = AdvancedBotConfig(**new_config_dict)
    setup_logger(self.config.log_level, self.config.log_file)
    return {"message": "Configuration reloaded successfully"}
```

### Process Management

The process manager uses:
- `asyncio.subprocess` for process control
- `psutil` for resource monitoring
- Signal-based shutdown (SIGTERM then SIGKILL)
- Process group management

```python
# Start bot process
self._process = await asyncio.create_subprocess_exec(
    "python3", str(self.bot_script),
    cwd=str(self.project_dir),
    env=env,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    start_new_session=True
)
```

## Error Handling

### Configuration Errors

- Invalid configuration is rejected with validation errors
- Bot falls back to direct config load if shared storage fails
- Configuration changes are atomic (temp file + rename)

### Process Errors

- Failed starts are logged and state set to ERROR
- Unexpected exits trigger state change to ERROR
- Force kill used if graceful shutdown times out

### IPC Errors

- Failed IPC commands return error responses
- Missing handlers log warning and return error
- Signal file errors are caught and logged

## Testing

### Manual Testing

1. Start the FastAPI admin interface:
   ```bash
   python run_api.py
   ```

2. Start the bot via API:
   ```bash
   curl -X POST http://localhost:8000/api/bot/control \
     -H "Content-Type: application/json" \
     -d '{"action": "start"}'
   ```

3. Check bot status:
   ```bash
   curl http://localhost:8000/api/bot/status
   ```

4. Update configuration:
   ```bash
   curl -X PATCH http://localhost:8000/api/config/behavior \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"bot_response_threshold": 0.8}'
   ```

5. Trigger hot-reload:
   ```bash
   curl -X POST http://localhost:8000/api/config/hot-reload \
     -H "Authorization: Bearer <token>"
   ```

### Integration Test Script

See `test_bot_restart.py` for automated testing of:
- Bot start/stop/restart
- Configuration updates
- Hot-reload functionality
- Process monitoring

## File Structure

```
discord-ai-bot-czech/
├── src/
│   ├── shared_config.py          # Shared configuration loader
│   ├── ipc.py                    # IPC communication
│   ├── bot_process_manager.py    # Process management
│   └── api/
│       ├── bot.py                # Bot control endpoints
│       └── config.py             # Config management endpoints
├── main.py                       # Enhanced bot main (with IPC)
├── app.py                        # FastAPI application
├── data/
│   ├── runtime_config.json       # Shared config storage
│   └── ipc/
│       ├── signal.json           # IPC signals
│       ├── response.json         # IPC responses
│       └── status.json           # Bot status
└── docs/
    └── BOT_INTEGRATION_COMPLETE.md  # This document
```

## API Endpoints

### Bot Management

- `GET /api/bot/status` - Get bot status
- `POST /api/bot/control` - Control bot (start/stop/restart)
- `POST /api/bot/restart` - Restart bot with options
- `GET /api/bot/stats` - Get bot statistics
- `GET /api/bot/health` - Health check

### Configuration Management

- `GET /api/config/` - Get current config
- `PUT /api/config/` - Update config
- `PATCH /api/config/discord` - Update Discord config
- `PATCH /api/config/ai` - Update AI config
- `PATCH /api/config/behavior` - Update behavior config
- `POST /api/config/reload` - Reload from disk
- `POST /api/config/hot-reload` - Hot-reload bot config
- `GET /api/config/validate` - Validate config

## Future Enhancements

1. **WebSocket Communication** - Replace file-based IPC with WebSocket
2. **Metrics Collection** - Implement actual bot statistics
3. **Configuration History** - Track config changes over time
4. **Auto-Restart** - Automatic restart on crash
5. **Health Checks** - Periodic health checks with auto-recovery
6. **Log Streaming** - Stream bot logs to admin interface
7. **Multi-Bot Support** - Manage multiple bot instances

## Security Considerations

1. All configuration endpoints require admin authentication
2. Sensitive values are masked in API responses
3. Configuration validation prevents injection attacks
4. Process isolation via separate process groups
5. File permissions on IPC and config files

## Troubleshooting

### Bot Won't Start

Check:
- Bot script exists at `main.py`
- Python dependencies installed
- Discord token is valid
- Logs in `logs/bot.log`

### Hot-Reload Not Working

Check:
- Bot is running (`GET /api/bot/status`)
- IPC files writable in `data/ipc/`
- Bot logs for reload errors
- Configuration is valid

### Configuration Not Persisting

Check:
- `.env` file is writable
- `data/runtime_config.json` is writable
- No validation errors in response
- Check API logs for save errors

## Summary

The integration provides:

✅ Shared configuration between bot and API
✅ Hot-reload without bot restart
✅ IPC communication for commands
✅ Full process lifecycle management
✅ Resource monitoring and statistics
✅ Graceful shutdown handling
✅ Comprehensive error handling
✅ Thread-safe operations
✅ Atomic configuration updates
✅ Validation and security

The bot can now be fully managed through the FastAPI admin interface with real-time configuration updates and process control.
