# Credential Migration Guide

This guide explains how to migrate credentials from `.env` files to encrypted vault storage using the migration utility.

## Overview

The migration utility (`migrate_credentials.py`) provides:

- **Secure Migration**: Encrypts sensitive credentials using AES-256-GCM
- **Automatic Backup**: Creates timestamped backups before migration
- **Rollback Capability**: Restore previous state if needed
- **Dry Run Mode**: Preview migration without making changes
- **Verification**: Validate vault integrity after migration

## Prerequisites

1. **Master Encryption Key**: Required for encryption/decryption
2. **Existing .env File**: Source credentials to migrate
3. **Python Dependencies**: `cryptography` library installed

## Quick Start

### 1. Generate Master Encryption Key

```bash
python scripts/migrate_credentials.py --generate-key
```

This outputs a secure random key:
```
MASTER_ENCRYPTION_KEY=<base64-encoded-key>
```

**IMPORTANT**: Store this key securely! Without it, you cannot decrypt the vault.

### 2. Set Environment Variable

```bash
export MASTER_ENCRYPTION_KEY=<your-generated-key>
```

Or add to your secure environment configuration.

### 3. Run Migration (Dry Run First)

Preview what will be migrated:

```bash
python scripts/migrate_credentials.py --dry-run
```

### 4. Perform Migration

```bash
python scripts/migrate_credentials.py
```

## Usage Examples

### Basic Migration

Migrate from default `.env` to default vault location:

```bash
python scripts/migrate_credentials.py
```

### Custom Paths

Specify custom .env and vault paths:

```bash
python scripts/migrate_credentials.py \
  --env-file /path/to/.env \
  --vault-file /path/to/vault.json \
  --backup-dir /path/to/backups
```

### Provide Master Key Directly

```bash
python scripts/migrate_credentials.py --master-key "your-key-here"
```

### List Available Backups

```bash
python scripts/migrate_credentials.py --list-backups
```

### Verify Vault Integrity

```bash
python scripts/migrate_credentials.py --verify
```

### Rollback to Previous State

```bash
python scripts/migrate_credentials.py --rollback /path/to/backup_20260315_120000
```

## Migration Process

### What Gets Migrated

**Sensitive Keys** (encrypted in vault):
- `DISCORD_BOT_TOKEN`
- `CLAUDE_API_KEY`
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `ADMIN_PASSWORD`
- `SECRET_KEY`
- `INITIAL_ADMIN_PASSWORD`

**Non-Sensitive Keys** (stored in config section):
- `DISCORD_CHANNEL_ID`
- `ADMIN_USERNAME`
- `BOT_PREFIX`
- `LOG_LEVEL`
- `ENVIRONMENT`

Unknown keys are treated as sensitive by default.

### Vault Structure

The encrypted vault contains:

```json
{
  "credentials": {
    "DISCORD_BOT_TOKEN": {
      "ciphertext": "...",
      "nonce": "...",
      "salt": "..."
    },
    ...
  },
  "config": {
    "BOT_PREFIX": "!",
    "LOG_LEVEL": "INFO"
  },
  "metadata": {
    "migrated_at": "2026-03-15T12:00:00",
    "source": "/path/to/.env",
    "version": "1.0"
  }
}
```

### Backup Structure

Backups are created in `data/backups/backup_YYYYMMDD_HHMMSS/`:

```
backup_20260315_120000/
├── .env.backup           # Original .env file
├── vault.json.backup     # Previous vault (if exists)
└── metadata.json         # Backup metadata
```

## Security Considerations

### Master Key Storage

**DO NOT**:
- Commit the master key to version control
- Store in plain text files
- Share via insecure channels

**DO**:
- Use environment variables in production
- Use secret management services (AWS Secrets Manager, HashiCorp Vault)
- Store securely in password managers for development

### File Permissions

The migration utility automatically sets restrictive permissions:
- Vault file: `0o600` (read/write owner only)
- Backup directory: `0o700` (full access owner only)

### After Migration

1. **Verify** the vault works correctly
2. **Test** your application with vault credentials
3. **Archive** or securely delete the old `.env` file
4. **Update** `.gitignore` to exclude vault files
5. **Document** key management procedures for your team

## Rollback Procedure

If migration causes issues:

### 1. List Available Backups

```bash
python scripts/migrate_credentials.py --list-backups
```

### 2. Choose Backup

Note the backup path (e.g., `data/backups/backup_20260315_120000`)

### 3. Rollback

```bash
python scripts/migrate_credentials.py --rollback data/backups/backup_20260315_120000
```

This restores:
- Original `.env` file
- Previous vault state (or removes vault if new migration)

## Troubleshooting

### "Master encryption key required"

**Solution**: Set `MASTER_ENCRYPTION_KEY` environment variable or use `--master-key` flag.

### "Failed to parse .env file"

**Causes**:
- Malformed KEY=VALUE format
- Invalid characters
- Missing file

**Solution**: Validate `.env` file format. Each line should be `KEY=VALUE` or comment `#`.

### "Vault verification failed"

**Causes**:
- Wrong master key
- Corrupted vault file
- Invalid vault structure

**Solution**:
1. Verify correct master key is set
2. Check vault file permissions
3. Rollback to last known good backup

### Migration Succeeds but App Fails

**Solution**:
1. Verify vault with `--verify` flag
2. Check application has access to master key
3. Ensure application uses `SecretsManager` to load credentials
4. Rollback if needed and investigate

## Integration with Application

After migration, update your application to use the vault:

```python
from secrets_manager import SecretsManager

# Initialize secrets manager
manager = SecretsManager()

# Load encrypted credentials
config = manager.load_encrypted_config("data/vault.json")

# Access credentials
discord_token = config["credentials"]["DISCORD_BOT_TOKEN"]
bot_prefix = config["config"]["BOT_PREFIX"]
```

## Command Reference

### Options

| Option | Description |
|--------|-------------|
| `--env-file PATH` | Path to .env file (default: `.env`) |
| `--vault-file PATH` | Path to vault file (default: `data/vault.json`) |
| `--backup-dir PATH` | Backup directory (default: `vault_dir/backups`) |
| `--master-key KEY` | Master encryption key (or use env var) |
| `--generate-key` | Generate new master key and exit |
| `--dry-run` | Simulate migration without writing |
| `--rollback PATH` | Rollback to backup at path |
| `--list-backups` | List all available backups |
| `--verify` | Verify vault integrity |

### Exit Codes

- `0`: Success
- `1`: Failure (error message printed to stderr)

## Best Practices

1. **Always dry run first**: Use `--dry-run` to preview changes
2. **Verify after migration**: Use `--verify` to ensure vault integrity
3. **Keep backups**: Don't delete backups immediately after migration
4. **Rotate keys periodically**: Generate new master keys on schedule
5. **Monitor access**: Log vault access in production
6. **Use secrets manager**: Don't hardcode master key in deployment scripts

## Migration Checklist

- [ ] Generate master encryption key
- [ ] Store key securely
- [ ] Run dry-run migration
- [ ] Review migration output
- [ ] Perform actual migration
- [ ] Verify vault integrity
- [ ] Test application with vault
- [ ] Update deployment configuration
- [ ] Archive/delete old .env file
- [ ] Document key location for team
- [ ] Set up key rotation schedule

## Support

For issues or questions:
1. Check this guide
2. Verify vault with `--verify`
3. Review backup timestamps with `--list-backups`
4. Test rollback in non-production first
