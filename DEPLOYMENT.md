# Docker Deployment Guide

This guide covers deploying the Discord AI Bot using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Management](#management)
- [Troubleshooting](#troubleshooting)
- [Production Considerations](#production-considerations)

## Prerequisites

Before deploying, ensure you have:

1. **Docker** (version 20.10 or higher)
   ```bash
   docker --version
   ```

2. **Docker Compose** (version 2.0 or higher)
   ```bash
   docker-compose --version
   ```

3. **Discord Bot Token**
   - Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a bot user and copy the token
   - Enable necessary intents: Message Content, Server Members, Presence

4. **AI API Key** (at least one):
   - Anthropic Claude API key (preferred)
   - Google Gemini API key
   - OpenAI API key

## Quick Start

### 1. Clone and Configure

```bash
# Navigate to project directory
cd discord-ai-bot-czech

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # or use your preferred editor
```

### 2. Configure Environment Variables

Edit `.env` file with your credentials:

```env
# Required: Discord Configuration
DISCORD_BOT_TOKEN=your_actual_bot_token
DISCORD_GUILD_ID=your_server_id
DISCORD_CHANNEL_IDS=channel_id_1,channel_id_2

# Required: At least one AI API key
ANTHROPIC_API_KEY=sk-ant-your_key_here

# Required: Admin credentials (CHANGE THESE!)
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=$(openssl rand -hex 32)
```

### 3. Deploy

Using the deployment script:

```bash
# Full deployment (build, stop old, start new)
./scripts/deploy.sh deploy

# Or manually:
docker-compose build
docker-compose up -d
```

### 4. Verify Deployment

```bash
# Check service status
./scripts/deploy.sh status

# Check health
./scripts/deploy.sh health

# View logs
./scripts/deploy.sh logs
```

## Configuration

### Environment Variables

All configuration is done through environment variables in the `.env` file:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DISCORD_BOT_TOKEN` | Discord bot token | Yes | - |
| `DISCORD_GUILD_ID` | Discord server ID | Yes | - |
| `DISCORD_CHANNEL_IDS` | Comma-separated channel IDs | Yes | - |
| `ANTHROPIC_API_KEY` | Claude API key | One required | - |
| `GOOGLE_API_KEY` | Gemini API key | One required | - |
| `OPENAI_API_KEY` | OpenAI API key | One required | - |
| `ADMIN_USERNAME` | Admin panel username | Yes | admin |
| `ADMIN_PASSWORD` | Admin panel password | Yes | changeme |
| `SECRET_KEY` | JWT secret key | Yes | auto-generated |
| `API_PORT` | FastAPI port | No | 8000 |
| `BOT_RESPONSE_THRESHOLD` | Response sensitivity (0-1) | No | 0.6 |
| `BOT_MAX_HISTORY` | Message history size | No | 50 |
| `BOT_LANGUAGE` | Response language | No | cs |
| `LOG_LEVEL` | Logging level | No | INFO |

### Persistent Data

Docker volumes are used for persistent storage:

- `bot-logs`: Application logs
- `bot-data`: Database and configuration

View volumes:
```bash
docker volume ls | grep discord-bot
```

Backup volumes:
```bash
docker run --rm -v bot-data:/data -v $(pwd):/backup alpine tar czf /backup/bot-data-backup.tar.gz /data
```

## Deployment

### Using Deployment Script

The `scripts/deploy.sh` script provides convenient commands:

```bash
# Build Docker image
./scripts/deploy.sh build

# Start services
./scripts/deploy.sh start

# Stop services
./scripts/deploy.sh stop

# Restart services
./scripts/deploy.sh restart

# View logs (follow mode)
./scripts/deploy.sh logs

# Check status
./scripts/deploy.sh status

# Check health
./scripts/deploy.sh health

# Full deployment
./scripts/deploy.sh deploy
```

### Manual Deployment

```bash
# Build image
docker-compose build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Remove volumes (CAUTION: deletes data)
docker-compose down -v
```

### Pushing to Registry

To push the image to a container registry:

```bash
# Set registry credentials
export DOCKER_REGISTRY=docker.io
export DOCKER_REPOSITORY=your-username
export DOCKER_USERNAME=your-username
export DOCKER_PASSWORD=your-password

# Push image
./scripts/docker-push.sh v1.0.0
```

## Management

### Accessing Admin Interface

The FastAPI admin interface is available at:

```
http://localhost:8000
```

Or if deployed on a server:

```
http://your-server-ip:8000
```

Login with credentials from `.env`:
- Username: `ADMIN_USERNAME`
- Password: `ADMIN_PASSWORD`

### Viewing Logs

```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100

# View specific service logs
docker-compose logs -f discord-bot
```

### Updating Configuration

To update configuration without rebuilding:

1. Edit `.env` file
2. Restart services:
   ```bash
   ./scripts/deploy.sh restart
   ```

### Updating Code

To deploy code changes:

```bash
# Pull latest changes
git pull

# Rebuild and restart
./scripts/deploy.sh deploy
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker-compose logs

# Check if port is already in use
netstat -tuln | grep 8000

# Check .env file is present
ls -la .env
```

### Health Check Failing

```bash
# Check if container is running
docker ps

# Check health endpoint manually
curl http://localhost:8000/health

# View detailed logs
docker-compose logs --tail=50
```

### Bot Not Responding

1. Check Discord token is valid
2. Verify channel IDs are correct
3. Ensure bot has Message Content intent enabled
4. Check bot has permissions in channels
5. View logs for errors:
   ```bash
   docker-compose logs | grep ERROR
   ```

### Permission Denied Errors

```bash
# Fix volume permissions
docker-compose down
sudo chown -R 1000:1000 ./logs ./data
docker-compose up -d
```

### Out of Memory

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 1G  # Increase from 512M
```

## Production Considerations

### Security

1. **Change default credentials**:
   ```bash
   # Generate secure secret key
   openssl rand -hex 32
   ```

2. **Use HTTPS** with reverse proxy (nginx/traefik)

3. **Restrict API access**:
   ```yaml
   ports:
     - "127.0.0.1:8000:8000"  # Only localhost
   ```

4. **Keep secrets secure**:
   - Never commit `.env` to git
   - Use Docker secrets or external secret management
   - Rotate API keys regularly

### Monitoring

1. **Health checks**: Built-in healthcheck runs every 30s

2. **Log monitoring**:
   ```bash
   # Set up log rotation
   docker-compose logs --tail=1000 > logs/$(date +%Y%m%d).log
   ```

3. **Resource monitoring**:
   ```bash
   docker stats discord-ai-bot-czech
   ```

### Backups

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup volumes
docker run --rm -v bot-data:/data -v $(pwd)/$BACKUP_DIR:/backup \
  alpine tar czf /backup/data.tar.gz /data

docker run --rm -v bot-logs:/logs -v $(pwd)/$BACKUP_DIR:/backup \
  alpine tar czf /backup/logs.tar.gz /logs

# Backup .env (encrypted)
openssl enc -aes-256-cbc -salt -in .env -out "$BACKUP_DIR/.env.enc"
```

### High Availability

For production deployments:

1. Use orchestration platform (Kubernetes, Docker Swarm)
2. Implement load balancing
3. Set up automated backups
4. Configure monitoring and alerting
5. Use managed database instead of SQLite

### Reverse Proxy Example (nginx)

```nginx
server {
    listen 80;
    server_name bot.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service (Alternative)

For systems without Docker Compose:

```ini
[Unit]
Description=Discord AI Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/discord-ai-bot-czech
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

## Support

For issues and questions:

- Check logs: `./scripts/deploy.sh logs`
- Review documentation: `README.md`
- Check Discord bot setup in Discord Developer Portal
- Verify API keys are valid and have credits

## License

See LICENSE file for details.
