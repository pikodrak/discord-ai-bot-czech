# Security Guide

This document describes the security features and best practices for the Discord AI Bot.

## Table of Contents

1. [Overview](#overview)
2. [Credential Storage](#credential-storage)
3. [Encryption](#encryption)
4. [Authentication](#authentication)
5. [Configuration Security](#configuration-security)
6. [Best Practices](#best-practices)
7. [Security Checklist](#security-checklist)

---

## Overview

The Discord AI Bot implements multiple layers of security to protect sensitive credentials and user data:

- **Environment Variables**: Secrets loaded from `.env` file (never committed to git)
- **Password Hashing**: Bcrypt hashing for admin passwords
- **JWT Authentication**: Secure token-based API authentication
- **AES-256-GCM Encryption**: Optional encryption for secrets at rest
- **Input Validation**: Pydantic models validate all configuration
- **Secure Defaults**: Conservative security settings out of the box

---

## Credential Storage

### Environment Variables

**Primary Method**: Store all sensitive credentials in environment variables.

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your credentials:
   ```bash
   # Generate secure SECRET_KEY
   openssl rand -hex 32

   # Or with Python
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. Set in `.env`:
   ```env
   SECRET_KEY=your-generated-secure-key-here
   DISCORD_BOT_TOKEN=your-discord-token
   ANTHROPIC_API_KEY=sk-ant-your-key
   ```

4. **CRITICAL**: Add `.env` to `.gitignore`:
   ```gitignore
   .env
   .env.local
   .env.*.local
   ```

### Encrypted Configuration Files

For additional security, use encrypted config files:

```python
from src.secrets_manager import get_secrets_manager

# Generate master encryption key
manager = get_secrets_manager()

# Encrypt sensitive configuration
secrets = {
    "DISCORD_BOT_TOKEN": "your-token",
    "ANTHROPIC_API_KEY": "sk-ant-key"
}

# Save encrypted
manager.save_encrypted_config(secrets, ".env.encrypted")

# Load encrypted
decrypted = manager.load_encrypted_config(".env.encrypted")
```

**Key Management**:
- Set `MASTER_ENCRYPTION_KEY` environment variable
- Or store in secure key file (not in git)
- Rotate keys periodically

---

## Encryption

### Secrets Manager

The `SecretsManager` class provides AES-256-GCM authenticated encryption:

```python
from src.secrets_manager import SecretsManager

# Initialize with master key
manager = SecretsManager(master_key="your-master-key")

# Encrypt a secret
encrypted = manager.encrypt("sensitive-data")

# Decrypt a secret
plaintext = manager.decrypt(encrypted)
```

**Features**:
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Derivation**: PBKDF2-HMAC-SHA256 (100,000 iterations)
- **Authentication**: Built-in authentication tags prevent tampering
- **Random Nonces**: Each encryption uses unique random nonce

### CLI Usage

Generate master encryption key:
```bash
python -m src.secrets_manager generate-key
```

Encrypt a value:
```bash
python -m src.secrets_manager encrypt "my-secret-value"
```

Decrypt a value:
```bash
python -m src.secrets_manager decrypt '{"ciphertext":"...", "nonce":"...", "salt":"..."}'
```

---

## Authentication

### Admin Password Initialization

The system uses a secure initialization mechanism for the default admin account:

**Method 1: Environment Variable (Recommended for Production)**
```env
# Set in .env file
ADMIN_PASSWORD=your-very-secure-password-here
```

**Method 2: Auto-Generated Password (Development/First Setup)**

If `ADMIN_PASSWORD` is not set, the system will:
1. Generate a cryptographically secure random password (20 characters)
2. Save credentials to `.admin_credentials` file with restrictive permissions
3. Log a warning with the file location

**After first startup**:
```bash
# Read the generated credentials
cat .admin_credentials

# Example output:
# ============================================================
# ADMIN CREDENTIALS - KEEP THIS FILE SECURE
# ============================================================
# Username: admin
# Password: xJ9#mK2@pL4$nR7&qT5*
# Email: admin@example.com
# ============================================================
```

**IMPORTANT**:
- Save the password securely (password manager)
- Delete `.admin_credentials` after retrieving the password
- Change the password after first login
- Never commit `.admin_credentials` to version control (already in `.gitignore`)

### Password Hashing

Admin passwords are hashed using bcrypt:

```python
from src.auth.security import hash_password, verify_password

# Hash password
hashed = hash_password("secure-password")

# Verify password
is_valid = verify_password("secure-password", hashed)
```

**Security Features**:
- **Bcrypt**: Industry-standard password hashing
- **Automatic Salt**: Random salt per password
- **Work Factor**: Configurable computational cost
- **Timing-Safe**: Comparison resistant to timing attacks

### Secure Password Generation

Generate cryptographically secure passwords:

```python
from src.auth.security import generate_secure_password

# Generate a secure password (default 16 chars)
password = generate_secure_password()

# Custom length (minimum 12)
password = generate_secure_password(length=20)
```

**Password Characteristics**:
- Minimum length: 12 characters
- Contains: uppercase, lowercase, digits, special characters
- Uses `secrets` module for cryptographic randomness
- Shuffled to avoid predictable patterns

### JWT Tokens

API authentication uses JSON Web Tokens (JWT):

```python
from src.auth.security import create_access_token, verify_token

# Create token
token = create_access_token(
    user_id=1,
    username="admin",
    is_admin=True
)

# Verify token
token_data = verify_token(token)
```

**Configuration**:
```env
SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**Security Features**:
- **HS256 Algorithm**: HMAC with SHA-256
- **Expiration**: Tokens expire after configured time
- **Claims**: User ID, username, admin flag, expiration
- **Signature**: Prevents token tampering

---

## Configuration Security

### Settings Validation

The `Settings` class validates all configuration:

```python
from src.config import get_settings

settings = get_settings()

# Check security warnings
warnings = settings.validate_security()
for warning in warnings:
    print(f"Security warning: {warning}")
```

**Validation Checks**:
- ✅ Secret key length (minimum 32 characters)
- ✅ Default credentials detection
- ✅ Production environment checks
- ✅ API key format validation
- ✅ Configuration completeness

### Sensitive Data Masking

Configuration values are automatically masked:

```python
from src.config import get_config_manager

manager = get_config_manager()

# Get safe config (secrets masked)
safe_config = manager.get_safe_dict()

# Example output:
# {
#   "secret_key": "chan...tion",
#   "discord_bot_token": "MTEx...xyz",
#   "api_host": "0.0.0.0"
# }
```

**Masked Fields**:
- `secret_key`
- `admin_password`
- `discord_bot_token`
- `anthropic_api_key`
- `google_api_key`
- `openai_api_key`
- `database_url`

---

## Best Practices

### Production Deployment

**Before deploying to production**:

1. ✅ Generate strong SECRET_KEY (32+ characters)
2. ✅ Change default admin username/password
3. ✅ Set `ENVIRONMENT=production`
4. ✅ Disable `API_RELOAD=false`
5. ✅ Set `LOG_LEVEL=INFO` or `WARNING`
6. ✅ Use HTTPS for API endpoints
7. ✅ Set restrictive CORS origins
8. ✅ Enable firewall rules
9. ✅ Use secrets management service (AWS Secrets Manager, HashiCorp Vault)
10. ✅ Regular security audits

### Environment-Specific Configs

Use different configurations per environment:

```yaml
# config.production.yaml
environment: production
log_level: WARNING
api_reload: false
enable_metrics: true
```

```yaml
# config.development.yaml
environment: development
log_level: DEBUG
api_reload: true
enable_metrics: false
```

### Secret Rotation

Rotate credentials regularly:

```bash
# 1. Generate new keys
openssl rand -hex 32 > new_secret.key

# 2. Update .env with new key
SECRET_KEY=new-key-here

# 3. Restart application
systemctl restart discord-bot

# 4. Revoke old keys at provider
# (Discord, Anthropic, etc.)
```

### File Permissions

Set restrictive permissions on sensitive files:

```bash
# .env file (owner read/write only)
chmod 600 .env

# Encrypted config (owner read/write only)
chmod 600 .env.encrypted

# Master key file (owner read only)
chmod 400 master.key
```

### Docker Security

When using Docker:

```bash
# Use secrets for sensitive data
docker secret create discord_token token.txt

# Mount as read-only
docker run -v $(pwd)/.env:/app/.env:ro discord-bot

# Don't expose unnecessary ports
# Only expose what's needed (e.g., 8000 for API)
```

### Logging Security

Prevent credentials from appearing in logs:

```python
# Good: Mask sensitive values
logger.info(f"API key configured: {key[:4]}...{key[-4:]}")

# Bad: Log full credentials
logger.info(f"API key: {key}")  # NEVER DO THIS
```

The logger automatically masks sensitive fields.

---

## Security Checklist

### Development

- [ ] `.env` file in `.gitignore`
- [ ] `.admin_credentials` file in `.gitignore`
- [ ] Strong `SECRET_KEY` set
- [ ] `ADMIN_PASSWORD` set in environment or retrieved from `.admin_credentials`
- [ ] `.admin_credentials` deleted after password retrieval
- [ ] Admin password changed after first login
- [ ] All API keys configured
- [ ] Security warnings checked

### Staging

- [ ] All development checks passed
- [ ] Environment set to `staging`
- [ ] Production-like configuration
- [ ] Security audit performed
- [ ] Penetration testing completed

### Production

- [ ] All staging checks passed
- [ ] Environment set to `production`
- [ ] API reload disabled
- [ ] Debug logging disabled
- [ ] HTTPS enabled
- [ ] CORS properly configured
- [ ] Firewall rules in place
- [ ] Secrets manager integrated
- [ ] Monitoring and alerting active
- [ ] Incident response plan ready
- [ ] Regular backups configured
- [ ] Disaster recovery tested

### Ongoing

- [ ] Regular dependency updates
- [ ] Security patches applied
- [ ] Credential rotation schedule
- [ ] Access logs reviewed
- [ ] Anomaly detection active
- [ ] Backup restoration tested

---

## Threat Model

### Threats Mitigated

| Threat | Mitigation |
|--------|------------|
| Credential theft from version control | Environment variables, `.gitignore` |
| Password compromise | Bcrypt hashing, strong password policy |
| Token tampering | JWT signatures, expiration |
| Man-in-the-middle attacks | HTTPS, secure token transmission |
| Unauthorized API access | JWT authentication, admin checks |
| Configuration injection | Input validation, Pydantic models |
| Secrets in logs | Automatic masking, log filtering |
| Data at rest exposure | AES-256-GCM encryption |

### Out of Scope

These threats require additional measures:

- **DDoS attacks**: Use rate limiting, CDN
- **SQL injection**: Use parameterized queries (SQLAlchemy ORM)
- **XSS attacks**: Frontend input sanitization
- **CSRF attacks**: CSRF tokens for web UI
- **Insider threats**: Access controls, audit logging

---

## Incident Response

If credentials are compromised:

1. **Immediate**:
   - Revoke compromised credentials at provider
   - Generate new credentials
   - Update `.env` with new credentials
   - Restart application

2. **Investigation**:
   - Check access logs for unauthorized access
   - Review recent configuration changes
   - Identify breach vector
   - Document incident

3. **Prevention**:
   - Patch vulnerability
   - Update security procedures
   - Rotate all related credentials
   - Notify affected users if needed

---

## Support

For security issues:

- **Public issues**: GitHub Issues
- **Security vulnerabilities**: Email maintainers privately
- **Production incidents**: Follow incident response plan

**DO NOT** disclose security vulnerabilities publicly before they are patched.
