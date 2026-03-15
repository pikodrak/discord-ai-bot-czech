# Secure Setup Guide

This guide walks you through setting up the Discord AI Bot with proper security measures.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Secure Credentials

```bash
# Generate SECRET_KEY for JWT tokens
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate master encryption key (optional)
python -m src.secrets_manager generate-key
```

### 3. Create Environment File

```bash
# Copy example
cp .env.example .env

# Edit with your credentials
nano .env
```

### 4. Configure Credentials

Edit `.env` and set:

```env
# REQUIRED: Change these immediately!
SECRET_KEY=<generated-key-from-step-2>
ADMIN_USERNAME=<your-admin-username>
ADMIN_PASSWORD=<strong-password>

# Discord credentials
DISCORD_BOT_TOKEN=<your-discord-token>
DISCORD_GUILD_ID=<your-guild-id>
DISCORD_CHANNEL_IDS=<channel-id-1>,<channel-id-2>

# AI API keys (at least one required)
ANTHROPIC_API_KEY=sk-ant-<your-key>
# GOOGLE_API_KEY=<your-key>
# OPENAI_API_KEY=sk-<your-key>

# Optional: Master encryption key
# MASTER_ENCRYPTION_KEY=<generated-encryption-key>
```

### 5. Verify Setup

```bash
# Run security validation
python -c "from src.config import get_settings; s = get_settings(); print('Warnings:', s.validate_security())"
```

### 6. Start the Bot

```bash
# Development mode
python main.py

# Or run API server
python app.py
```

---

## Detailed Setup

### Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section
4. Click "Reset Token" to generate a new token
5. Copy token and set as `DISCORD_BOT_TOKEN`

**Security**:
- Never commit token to git
- Regenerate if exposed
- Use bot permissions carefully

### AI API Keys

#### Anthropic (Claude)

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create API key
3. Set as `ANTHROPIC_API_KEY=sk-ant-...`

#### Google (Gemini)

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Set as `GOOGLE_API_KEY=...`

#### OpenAI

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create API key
3. Set as `OPENAI_API_KEY=sk-...`

**Security**:
- Use separate keys per environment
- Set spending limits
- Monitor usage regularly
- Rotate keys periodically

### Password Security

#### Generate Strong Passwords

```bash
# Random password (16 chars)
python -c "import secrets; print(secrets.token_urlsafe(16))"

# Or use a password manager
```

#### Hash Admin Password

The password is hashed automatically on first login, but you can pre-hash:

```python
from src.auth.security import hash_password

hashed = hash_password("your-password")
print(hashed)
```

**Requirements**:
- Minimum 8 characters
- Mix of upper/lower case
- Include numbers and symbols
- Not in common password lists

---

## Advanced Security

### Encrypted Configuration

For maximum security, encrypt sensitive config:

```python
from src.secrets_manager import SecretsManager

# Initialize manager
manager = SecretsManager(master_key="your-master-key")

# Encrypt config
secrets = {
    "DISCORD_BOT_TOKEN": "your-token",
    "ANTHROPIC_API_KEY": "sk-ant-key"
}

manager.save_encrypted_config(secrets, ".env.encrypted")
```

Load encrypted config:

```python
# In your app startup
manager = SecretsManager()
secrets = manager.load_encrypted_config(".env.encrypted")

# Use decrypted values
os.environ.update(secrets)
```

### Secrets Management Services

For production, use a secrets manager:

#### AWS Secrets Manager

```python
import boto3
import json

client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='discord-bot/prod')
secrets = json.loads(response['SecretString'])

os.environ['DISCORD_BOT_TOKEN'] = secrets['discord_token']
```

#### HashiCorp Vault

```python
import hvac

client = hvac.Client(url='https://vault.example.com')
client.token = os.environ['VAULT_TOKEN']

secret = client.secrets.kv.v2.read_secret_version(path='discord-bot')
os.environ['DISCORD_BOT_TOKEN'] = secret['data']['data']['token']
```

#### Google Secret Manager

```python
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
name = "projects/PROJECT_ID/secrets/discord-token/versions/latest"

response = client.access_secret_version(request={"name": name})
os.environ['DISCORD_BOT_TOKEN'] = response.payload.data.decode('UTF-8')
```

### Environment-Based Configuration

Use different configs per environment:

```bash
# Development
ENVIRONMENT=development python app.py

# Staging
ENVIRONMENT=staging python app.py

# Production
ENVIRONMENT=production python app.py
```

Config files:
- `config.development.yaml` - Dev settings
- `config.staging.yaml` - Staging settings
- `config.production.yaml` - Production settings

---

## Security Checklist

### Development

- [ ] `.env` file created and configured
- [ ] `.env` in `.gitignore`
- [ ] Strong `SECRET_KEY` generated
- [ ] Admin password changed
- [ ] Discord bot token configured
- [ ] At least one AI API key configured
- [ ] No security warnings

### Staging

- [ ] Separate credentials from development
- [ ] `ENVIRONMENT=staging` set
- [ ] Production-like configuration tested
- [ ] Security validation passed
- [ ] HTTPS configured (if applicable)

### Production

- [ ] Separate credentials from staging
- [ ] `ENVIRONMENT=production` set
- [ ] `API_RELOAD=false`
- [ ] `LOG_LEVEL=INFO` or `WARNING`
- [ ] Strong admin credentials
- [ ] HTTPS enforced
- [ ] CORS configured properly
- [ ] Firewall rules active
- [ ] Secrets manager integrated (recommended)
- [ ] Monitoring enabled
- [ ] Backup configured

---

## Common Issues

### "No master encryption key found"

**Solution**: Set `MASTER_ENCRYPTION_KEY` in `.env`:

```bash
python -m src.secrets_manager generate-key
# Add output to .env
```

### "Security warning: Using default SECRET_KEY"

**Solution**: Generate and set new key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add to .env as SECRET_KEY
```

### "Discord bot token is not configured"

**Solution**: Get token from Discord Developer Portal and set in `.env`:

```env
DISCORD_BOT_TOKEN=MTExMjIyMzMz...
```

### "No AI API key configured"

**Solution**: Set at least one AI provider key:

```env
ANTHROPIC_API_KEY=sk-ant-...
# or
GOOGLE_API_KEY=...
# or
OPENAI_API_KEY=sk-...
```

---

## Testing Security

Run security tests:

```bash
# Basic validation
python -c "from src.config import get_settings; print(get_settings().validate_security())"

# Test password hashing
python -c "from src.auth.security import hash_password, verify_password; h = hash_password('test'); print(verify_password('test', h))"

# Test encryption
python examples/security_usage.py

# Run full test suite
pytest tests/test_security.py
```

---

## Rotating Credentials

### Rotate SECRET_KEY

1. Generate new key
2. Update `.env`
3. Restart application
4. All users need to re-login (JWT tokens invalidated)

### Rotate Discord Token

1. Go to Discord Developer Portal
2. Click "Reset Token"
3. Update `DISCORD_BOT_TOKEN` in `.env`
4. Restart bot

### Rotate AI API Keys

1. Generate new key at provider
2. Update `.env`
3. Test connection
4. Revoke old key at provider
5. Restart application

### Rotation Schedule

**Recommended**:
- `SECRET_KEY`: Every 90 days
- `DISCORD_BOT_TOKEN`: Every 180 days or if exposed
- `AI API keys`: Every 180 days or if exposed
- `ADMIN_PASSWORD`: Every 60 days

---

## Further Reading

- [Security Guide](SECURITY.md) - Comprehensive security documentation
- [API Documentation](API_README.md) - API security features
- [Deployment Guide](DEPLOYMENT.md) - Production deployment security

For security issues or questions, see [SECURITY.md](SECURITY.md).
