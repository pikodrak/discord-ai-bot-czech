# Secure Credential Storage Guide

This guide explains how to securely manage credentials in the Discord AI Bot application.

## Table of Contents

- [Overview](#overview)
- [Security Features](#security-features)
- [Quick Start](#quick-start)
- [Storage Methods](#storage-methods)
- [Credential Management CLI](#credential-management-cli)
- [Credential Rotation](#credential-rotation)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The application provides a multi-layered credential management system:

1. **Environment Variables** - Primary method for production
2. **Encrypted Credential Vault** - Secure encrypted storage
3. **`.env` Files** - Development and testing
4. **Secrets Manager** - AES-256-GCM encryption layer

## Security Features

### Encryption
- **AES-256-GCM** authenticated encryption
- **PBKDF2** key derivation with 100,000 iterations
- Random salts and nonces for each encrypted value
- Authentication tags to prevent tampering

### Password Security
- **bcrypt** hashing for passwords
- Automatic salt generation
- Configurable work factor

### JWT Tokens
- HS256 algorithm
- Configurable expiration
- Secure secret key management

### Audit Logging
- All credential access logged
- Timestamp and action tracking
- Rotation history

### Access Control
- Restrictive file permissions (0600/0700)
- Environment-based strict mode
- Metadata tracking for rotation policies

## Quick Start

### 1. Generate Master Encryption Key

```bash
python scripts/manage_credentials.py generate-key
```

Output:
```
MASTER_ENCRYPTION_KEY=AbC123...XyZ789==
```

### 2. Add to Environment

**For Development (.env file):**
```bash
echo "MASTER_ENCRYPTION_KEY=AbC123...XyZ789==" >> .env
```

**For Production (environment variable):**
```bash
export MASTER_ENCRYPTION_KEY=AbC123...XyZ789==
```

### 3. Store Credentials

```bash
# Store Discord token
python scripts/manage_credentials.py set DISCORD_BOT_TOKEN "your-token-here" token

# Store admin password
python scripts/manage_credentials.py set ADMIN_PASSWORD "secure-password" password

# Store API keys
python scripts/manage_credentials.py set ANTHROPIC_API_KEY "sk-ant-..." api_key
```

### 4. Verify Setup

```bash
python scripts/manage_credentials.py health
```

## Storage Methods

### Priority Order

When loading credentials, the system checks in this order:

1. **Environment Variables** (highest priority)
2. **Encrypted Vault Files** (data/vault/*.enc.json)
3. **Default Values** (development only)

### Method Comparison

| Method | Use Case | Security | Rotation |
|--------|----------|----------|----------|
| Environment Variables | Production, CI/CD | High | Manual |
| Encrypted Vault | Development, Staging | Very High | Automated |
| .env Files | Local Development | Medium | Manual |
| Defaults | Quick Testing | Low | N/A |

## Credential Management CLI

### Generate Encryption Key

```bash
python scripts/manage_credentials.py generate-key
```

### Store Credentials

```bash
# Syntax: set NAME VALUE [TYPE]
python scripts/manage_credentials.py set DISCORD_BOT_TOKEN "your-token" token
python scripts/manage_credentials.py set ADMIN_PASSWORD "password123" password
python scripts/manage_credentials.py set ANTHROPIC_API_KEY "sk-ant-..." api_key
```

**Credential Types:**
- `api_key` - API keys (rotation: 180 days)
- `password` - Passwords (rotation: 90 days)
- `token` - Authentication tokens (rotation: 180 days)
- `secret` - Generic secrets (no rotation)
- `database_url` - Database connections (no rotation)
- `webhook_url` - Webhook URLs (no rotation)

### Retrieve Credentials

```bash
# Get credential value
python scripts/manage_credentials.py get DISCORD_BOT_TOKEN

# List all credentials
python scripts/manage_credentials.py list

# List by type
python scripts/manage_credentials.py list api_key
```

### Rotate Credentials

```bash
# Rotate with new value
python scripts/manage_credentials.py rotate ADMIN_PASSWORD "new-secure-password"

# Check which credentials need rotation
python scripts/manage_credentials.py check-rotation
```

### Delete Credentials

```bash
python scripts/manage_credentials.py delete OLD_CREDENTIAL
```

### Health Check

```bash
python scripts/manage_credentials.py health
```

Output:
```
Credential System Health Check
==================================================

Status: ✓ HEALTHY

Total credentials configured: 10
Successfully loaded: 10
Missing: 0
Coverage: 100.0%

Vault credentials: 5
✓ No credentials need rotation
```

### Export Structure

```bash
python scripts/manage_credentials.py export
```

## Credential Rotation

### Automatic Rotation Policies

The system tracks credential age and rotation requirements:

- **Passwords**: 90 days
- **API Keys**: 180 days
- **Tokens**: 180 days

### Check Rotation Status

```bash
python scripts/manage_credentials.py check-rotation
```

### Rotate Credentials

```bash
# 1. Generate new credential (e.g., new API key from provider)
# 2. Rotate in vault
python scripts/manage_credentials.py rotate ANTHROPIC_API_KEY "new-key-here"

# 3. Restart application to use new credential
```

### Rotation Best Practices

1. **Test new credential** before rotation
2. **Keep old credential active** during transition
3. **Monitor logs** after rotation
4. **Document rotation** in changelog
5. **Update backup systems** with new credentials

## Best Practices

### Production Deployment

#### 1. Use Environment Variables

```bash
# Set in your deployment platform
export DISCORD_BOT_TOKEN="..."
export ANTHROPIC_API_KEY="..."
export SECRET_KEY="..."
export MASTER_ENCRYPTION_KEY="..."
```

#### 2. Enable Strict Mode

Set environment to production:
```bash
export ENVIRONMENT=production
```

This enforces:
- All required credentials must be present
- No default values accepted
- Validation on startup

#### 3. Separate Keys Per Environment

```bash
# Development
MASTER_ENCRYPTION_KEY=dev-key-here

# Staging
MASTER_ENCRYPTION_KEY=staging-key-here

# Production
MASTER_ENCRYPTION_KEY=prod-key-here
```

### Development Workflow

#### 1. Copy Example Environment

```bash
cp .env.example .env
```

#### 2. Generate Keys

```bash
python scripts/manage_credentials.py generate-key
```

#### 3. Add to .env

Edit `.env` and add:
- `MASTER_ENCRYPTION_KEY`
- `SECRET_KEY`
- `DISCORD_BOT_TOKEN`
- API keys

#### 4. Store in Vault (Optional)

```bash
python scripts/manage_credentials.py set DISCORD_BOT_TOKEN "token" token
```

### Security Checklist

- [ ] Generate unique `SECRET_KEY` for JWT signing
- [ ] Generate unique `MASTER_ENCRYPTION_KEY` for encryption
- [ ] Use different keys for each environment
- [ ] Never commit `.env` or keys to version control
- [ ] Set restrictive file permissions (0600)
- [ ] Rotate credentials regularly
- [ ] Monitor audit logs
- [ ] Use strong passwords (12+ characters)
- [ ] Enable 2FA on API provider accounts
- [ ] Backup encryption keys securely

### CI/CD Integration

#### GitHub Actions

```yaml
env:
  DISCORD_BOT_TOKEN: ${{ secrets.DISCORD_BOT_TOKEN }}
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  SECRET_KEY: ${{ secrets.SECRET_KEY }}
  MASTER_ENCRYPTION_KEY: ${{ secrets.MASTER_ENCRYPTION_KEY }}
```

#### Docker

```dockerfile
ENV DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
ENV SECRET_KEY=${SECRET_KEY}
ENV MASTER_ENCRYPTION_KEY=${MASTER_ENCRYPTION_KEY}
```

Or use Docker secrets:
```bash
docker secret create discord_token token.txt
docker service create --secret discord_token myapp
```

## Troubleshooting

### Credential Not Found

**Error:**
```
Credential 'DISCORD_BOT_TOKEN' not found
```

**Solutions:**
1. Check environment variables: `echo $DISCORD_BOT_TOKEN`
2. Check .env file: `cat .env | grep DISCORD_BOT_TOKEN`
3. List vault credentials: `python scripts/manage_credentials.py list`
4. Store in vault: `python scripts/manage_credentials.py set DISCORD_BOT_TOKEN "token" token`

### Decryption Failed

**Error:**
```
Failed to decrypt secret - wrong key or corrupted data
```

**Solutions:**
1. Verify `MASTER_ENCRYPTION_KEY` matches the key used to encrypt
2. Check environment: `echo $MASTER_ENCRYPTION_KEY`
3. Regenerate vault if keys are lost (credentials will need to be re-entered)

### Permission Denied

**Error:**
```
Permission denied: data/vault/credential.enc.json
```

**Solutions:**
```bash
# Fix vault directory permissions
chmod 700 data/vault
chmod 600 data/vault/*.enc.json
```

### Missing Master Key (Development)

**Warning:**
```
No master key found - generating temporary key for development
```

**Solution:**
This is normal in development. For production:
```bash
python scripts/manage_credentials.py generate-key
export MASTER_ENCRYPTION_KEY=<generated-key>
```

### Credentials Need Rotation

**Warning:**
```
⚠ WARNING: This credential needs rotation!
```

**Solution:**
```bash
# Check which credentials need rotation
python scripts/manage_credentials.py check-rotation

# Rotate credential
python scripts/manage_credentials.py rotate CREDENTIAL_NAME "new-value"
```

## API Usage

### Python Code Example

```python
from src.credential_vault import get_credential_vault, CredentialType
from src.credential_loader import CredentialLoader, CredentialConfig

# Using vault directly
vault = get_credential_vault()

# Store credential
vault.set_credential(
    name="MY_API_KEY",
    value="secret-key",
    credential_type=CredentialType.API_KEY,
    rotation_days=180
)

# Retrieve credential
api_key = vault.get_credential("MY_API_KEY")

# Using loader
loader = CredentialLoader()

config = CredentialConfig(
    name="my_api_key",
    env_var="MY_API_KEY",
    credential_type=CredentialType.API_KEY,
    required=True
)

value = loader.load_credential(config)
```

### FastAPI Integration

```python
from fastapi import Depends, HTTPException
from src.credential_vault import get_credential_vault

def get_api_key():
    vault = get_credential_vault()
    key = vault.get_credential("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="API key not configured")
    return key

@app.get("/chat")
async def chat(api_key: str = Depends(get_api_key)):
    # Use api_key securely
    ...
```

## Additional Resources

- [AES-GCM Encryption](https://en.wikipedia.org/wiki/Galois/Counter_Mode)
- [PBKDF2 Key Derivation](https://en.wikipedia.org/wiki/PBKDF2)
- [bcrypt Password Hashing](https://en.wikipedia.org/wiki/Bcrypt)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [OWASP Credential Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review audit logs: `cat data/vault/audit.log`
3. Run health check: `python scripts/manage_credentials.py health`
4. Check application logs: `cat logs/bot.log`
