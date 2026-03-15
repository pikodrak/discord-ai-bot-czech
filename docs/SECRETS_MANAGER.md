# Secrets Manager Documentation

## Overview

The Secrets Manager provides secure encryption and decryption of sensitive credentials at rest using industry-standard cryptographic practices.

## Security Features

### Encryption

- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Size**: 256 bits
- **Authentication**: Built-in authentication tags for integrity verification
- **Nonce**: 96-bit random nonce for each encryption operation

### Key Derivation

- **Algorithm**: PBKDF2-HMAC-SHA256
- **Iterations**: 600,000 (OWASP 2023 recommendation)
- **Salt Size**: 256 bits (randomly generated per operation)

### Security Best Practices

- Random salts prevent rainbow table attacks
- Random nonces prevent nonce reuse vulnerabilities
- Authenticated encryption prevents tampering
- Secure key derivation prevents brute-force attacks
- File permissions (0600) protect key files

## Installation

The secrets manager requires the `cryptography` library:

```bash
pip install cryptography
```

## Quick Start

### Basic Usage

```python
from src.secrets_manager import SecretsManager

# Initialize with a master password
manager = SecretsManager(master_key="your-secure-password")

# Encrypt a value
encrypted = manager.encrypt_value("sensitive-data")
print(f"Encrypted: {encrypted}")

# Decrypt the value
decrypted = manager.decrypt_value(encrypted)
print(f"Decrypted: {decrypted}")
```

### Using a Key File

```python
from src.secrets_manager import SecretsManager
from pathlib import Path

# Generate a random master key
manager = SecretsManager()
key_file = Path(".secrets/master.key")
generated_key = manager.generate_master_key(output_file=key_file)

# Load from key file
manager2 = SecretsManager(key_file=key_file)
encrypted = manager2.encrypt_value("secret-data")
```

## API Reference

### SecretsManager Class

#### Initialization

```python
SecretsManager(
    master_key: Optional[str] = None,
    key_file: Optional[Path] = None
)
```

**Parameters:**
- `master_key`: Master password for encryption (string)
- `key_file`: Path to file containing master key

**Raises:**
- `MasterKeyError`: If both `master_key` and `key_file` are provided

#### Methods

##### set_master_key(password: str) -> None

Set the master password for encryption/decryption.

```python
manager = SecretsManager()
manager.set_master_key("my-secure-password")
```

##### generate_master_key(output_file: Optional[Path] = None) -> str

Generate a cryptographically secure random master key.

```python
manager = SecretsManager()
key = manager.generate_master_key(output_file=Path("master.key"))
print(f"Generated key: {key}")
```

**Returns:** Base64-encoded master key

##### load_master_key_from_file(key_file: Path) -> None

Load master key from a file.

```python
manager = SecretsManager()
manager.load_master_key_from_file(Path("master.key"))
```

**Security Note:** Key file must have 0600 permissions (owner read/write only).

##### encrypt_value(plaintext: str, password: Optional[str] = None) -> str

Encrypt a string value using AES-256-GCM.

```python
encrypted = manager.encrypt_value("secret-token")
```

**Parameters:**
- `plaintext`: Value to encrypt
- `password`: Optional password (uses master key if not provided)

**Returns:** Base64-encoded encrypted data (format: salt:nonce:ciphertext)

##### decrypt_value(encrypted: str, password: Optional[str] = None) -> str

Decrypt an encrypted value.

```python
decrypted = manager.decrypt_value(encrypted)
```

**Parameters:**
- `encrypted`: Base64-encoded encrypted data
- `password`: Optional password (uses master key if not provided)

**Returns:** Decrypted plaintext string

##### encrypt_dict(data: Dict[str, Any], keys_to_encrypt: list[str]) -> Dict[str, Any]

Encrypt specific keys in a dictionary.

```python
config = {
    "api_key": "secret123",
    "app_name": "MyApp",
    "token": "abc789"
}

encrypted_config = manager.encrypt_dict(
    config,
    keys_to_encrypt=["api_key", "token"]
)
```

##### decrypt_dict(data: Dict[str, Any], keys_to_decrypt: list[str]) -> Dict[str, Any]

Decrypt specific keys in a dictionary.

```python
decrypted_config = manager.decrypt_dict(
    encrypted_config,
    keys_to_decrypt=["api_key", "token"]
)
```

##### save_encrypted_config(config: Dict[str, Any], output_file: Union[str, Path], keys_to_encrypt: Optional[list[str]] = None) -> None

Save configuration to an encrypted JSON file.

```python
config = {
    "discord_token": "MTIzNDU2...",
    "api_key": "sk-ant-...",
    "app_name": "Bot"
}

manager.save_encrypted_config(
    config,
    "config.encrypted.json",
    keys_to_encrypt=["discord_token", "api_key"]
)
```

**Parameters:**
- `config`: Configuration dictionary
- `output_file`: Path to output file
- `keys_to_encrypt`: List of keys to encrypt (encrypts all if None)

##### load_encrypted_config(input_file: Union[str, Path]) -> Dict[str, Any]

Load configuration from an encrypted JSON file.

```python
config = manager.load_encrypted_config("config.encrypted.json")
```

##### rotate_encryption(encrypted_value: str, old_password: Optional[str] = None, new_password: Optional[str] = None) -> str

Re-encrypt a value with a new password (key rotation).

```python
# Rotate from old password to new password
re_encrypted = manager.rotate_encryption(
    encrypted_value,
    old_password="old-pass-2024",
    new_password="new-pass-2025"
)
```

##### is_encrypted(value: str) -> bool

Check if a value appears to be encrypted.

```python
if manager.is_encrypted(some_value):
    decrypted = manager.decrypt_value(some_value)
else:
    # Value is plaintext
    pass
```

##### clear_master_key() -> None

Clear the master key from memory for security.

```python
manager.clear_master_key()
```

### Factory Function

#### create_secrets_manager(...)

Factory function to create a SecretsManager instance.

```python
from src.secrets_manager import create_secrets_manager

# Create with password
manager1 = create_secrets_manager(password="my-password")

# Create with key file
manager2 = create_secrets_manager(key_file="master.key")

# Generate new key
manager3 = create_secrets_manager(
    generate_key=True,
    key_output_file="new_master.key"
)
```

## Exception Hierarchy

```
SecretsManagerError (base)
├── EncryptionError
├── DecryptionError
└── MasterKeyError
```

### Exception Handling

```python
from src.secrets_manager import (
    SecretsManager,
    EncryptionError,
    DecryptionError,
    MasterKeyError
)

manager = SecretsManager(master_key="password")

try:
    encrypted = manager.encrypt_value("data")
    decrypted = manager.decrypt_value(encrypted)
except EncryptionError as e:
    print(f"Encryption failed: {e}")
except DecryptionError as e:
    print(f"Decryption failed: {e}")
except MasterKeyError as e:
    print(f"Master key error: {e}")
```

## Use Cases

### 1. Environment Variables Encryption

```python
import os
from src.secrets_manager import SecretsManager

manager = SecretsManager(master_key=os.getenv("MASTER_PASSWORD"))

# Encrypt sensitive env vars
discord_token = os.getenv("DISCORD_TOKEN")
encrypted_token = manager.encrypt_value(discord_token)

# Store encrypted value
with open(".env.encrypted", "w") as f:
    f.write(f"DISCORD_TOKEN_ENCRYPTED={encrypted_token}\n")
```

### 2. Configuration File Encryption

```python
from src.secrets_manager import SecretsManager
from pathlib import Path

manager = SecretsManager(key_file=Path(".secrets/master.key"))

config = {
    "discord": {
        "token": "MTIzNDU2Nzg5...",
        "client_id": "123456789"
    },
    "anthropic": {
        "api_key": "sk-ant-api03-..."
    },
    "app": {
        "name": "Discord Bot",
        "debug": False
    }
}

# Flatten and encrypt sensitive values
sensitive_config = {
    "discord_token": config["discord"]["token"],
    "anthropic_api_key": config["anthropic"]["api_key"],
    "app_name": config["app"]["name"],
    "debug": config["app"]["debug"]
}

manager.save_encrypted_config(
    sensitive_config,
    "config.encrypted.json",
    keys_to_encrypt=["discord_token", "anthropic_api_key"]
)
```

### 3. Database Credential Storage

```python
from src.secrets_manager import SecretsManager

manager = SecretsManager(master_key="db-encryption-key")

db_credentials = {
    "host": "localhost",
    "port": 5432,
    "database": "myapp",
    "username": "admin",
    "password": "super_secret_password"
}

encrypted_creds = manager.encrypt_dict(
    db_credentials,
    keys_to_encrypt=["password"]
)

# Save to file
import json
with open("db_config.json", "w") as f:
    json.dump(encrypted_creds, f)
```

### 4. API Key Rotation

```python
from src.secrets_manager import SecretsManager

manager = SecretsManager()

# Old encrypted key
old_encrypted = "base64_encrypted_data..."

# Rotate to new password
new_encrypted = manager.rotate_encryption(
    old_encrypted,
    old_password="2024-password",
    new_password="2025-password"
)

# Update storage with new encrypted value
print(f"Rotated key: {new_encrypted}")
```

### 5. Secure Credential Sharing

```python
from src.secrets_manager import SecretsManager
from pathlib import Path

# Generate a shared key
manager = SecretsManager()
shared_key = manager.generate_master_key(
    output_file=Path("shared_team_key.key")
)

# Team member can use the same key
team_manager = SecretsManager(key_file=Path("shared_team_key.key"))

# Encrypt credentials for sharing
credentials = {
    "service": "production_api",
    "api_key": "sk-prod-xyz123",
    "endpoint": "https://api.example.com"
}

team_manager.save_encrypted_config(
    credentials,
    "shared_credentials.encrypted.json"
)
```

## Security Best Practices

### 1. Master Key Management

**Do:**
- Use a strong, random password (minimum 20 characters)
- Store key files with 0600 permissions
- Use environment variables or secure vaults for production
- Rotate keys periodically

**Don't:**
- Hardcode master keys in source code
- Share master keys via insecure channels
- Use weak or predictable passwords
- Commit key files to version control

### 2. Key Storage

```python
# ✓ Good: Key file with restricted permissions
manager = SecretsManager(key_file=Path(".secrets/master.key"))

# ✓ Good: Environment variable
import os
manager = SecretsManager(master_key=os.getenv("MASTER_KEY"))

# ✗ Bad: Hardcoded in source
manager = SecretsManager(master_key="password123")
```

### 3. Error Handling

Always handle decryption errors gracefully:

```python
try:
    decrypted = manager.decrypt_value(encrypted_value)
except DecryptionError:
    # Handle error without exposing sensitive info
    logger.error("Failed to decrypt credential")
    raise
```

### 4. Key Rotation

Implement periodic key rotation:

```python
def rotate_all_credentials(old_password: str, new_password: str):
    manager = SecretsManager()

    # Load all encrypted credentials
    with open("credentials.json") as f:
        creds = json.load(f)

    # Rotate each credential
    for key, encrypted_value in creds.items():
        creds[key] = manager.rotate_encryption(
            encrypted_value,
            old_password=old_password,
            new_password=new_password
        )

    # Save rotated credentials
    with open("credentials.json", "w") as f:
        json.dump(creds, f)
```

### 5. File Permissions

Always check and set secure file permissions:

```python
import os
from pathlib import Path

key_file = Path("master.key")

# Set secure permissions (owner read/write only)
key_file.touch(mode=0o600)
os.chmod(key_file, 0o600)

# Verify permissions
file_mode = key_file.stat().st_mode & 0o777
assert file_mode == 0o600, "Insecure file permissions"
```

## Integration Examples

### With Discord Bot

```python
from discord.ext import commands
from src.secrets_manager import SecretsManager
from pathlib import Path

# Load encrypted config
manager = SecretsManager(key_file=Path(".secrets/master.key"))
config = manager.load_encrypted_config("bot_config.encrypted.json")

# Initialize bot with decrypted token
bot = commands.Bot(command_prefix="!")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(config["discord_token"])
```

### With Environment Variables

```python
import os
from dotenv import load_dotenv
from src.secrets_manager import SecretsManager

# Load .env file
load_dotenv()

# Initialize secrets manager
manager = SecretsManager(master_key=os.getenv("MASTER_KEY"))

# Decrypt environment variables
encrypted_token = os.getenv("DISCORD_TOKEN_ENCRYPTED")
discord_token = manager.decrypt_value(encrypted_token)

# Use decrypted token
print(f"Token: {discord_token[:10]}...")
```

### With Configuration Classes

```python
from dataclasses import dataclass
from src.secrets_manager import SecretsManager
from pathlib import Path

@dataclass
class BotConfig:
    discord_token: str
    anthropic_api_key: str
    app_name: str
    debug: bool

def load_config(config_file: Path, master_key: str) -> BotConfig:
    manager = SecretsManager(master_key=master_key)
    config_data = manager.load_encrypted_config(config_file)
    return BotConfig(**config_data)

# Usage
config = load_config(Path("config.encrypted.json"), "my-password")
```

## Performance Considerations

### Encryption Performance

- **PBKDF2 iterations**: 600,000 iterations take ~100-200ms on modern hardware
- **Use case**: Suitable for configuration loading and credential storage
- **Not suitable**: High-frequency operations (use cached keys instead)

### Optimization Tips

```python
# Cache the manager instance
manager = SecretsManager(master_key="password")

# Reuse for multiple operations
encrypted1 = manager.encrypt_value("data1")
encrypted2 = manager.encrypt_value("data2")
encrypted3 = manager.encrypt_value("data3")

# Don't create new instances for each operation
# ✗ Bad: Creates new instance each time
for data in values:
    manager = SecretsManager(master_key="password")  # Slow!
    encrypted = manager.encrypt_value(data)
```

## Testing

Run the example script to verify functionality:

```bash
python examples/secrets_manager_usage.py
```

## Troubleshooting

### Common Issues

#### 1. MasterKeyError: No master key set

**Solution:** Set a master key before encryption/decryption
```python
manager = SecretsManager()
manager.set_master_key("your-password")
```

#### 2. DecryptionError: Decryption failed

**Causes:**
- Wrong password
- Corrupted encrypted data
- Invalid base64 encoding

**Solution:** Verify password and data integrity

#### 3. MasterKeyError: Insecure file permissions

**Solution:** Set correct permissions
```bash
chmod 600 master.key
```

#### 4. EncryptionError: Encryption failed

**Causes:**
- Invalid input data
- Memory issues
- System limitations

**Solution:** Check input data and system resources

## Migration Guide

### From Plain Text to Encrypted Config

```python
import json
from src.secrets_manager import SecretsManager
from pathlib import Path

# Load plain text config
with open("config.json") as f:
    plain_config = json.load(f)

# Initialize secrets manager
manager = SecretsManager(master_key="new-secure-password")

# Define sensitive keys
sensitive_keys = [
    "discord_token",
    "anthropic_api_key",
    "database_password"
]

# Save encrypted version
manager.save_encrypted_config(
    plain_config,
    "config.encrypted.json",
    keys_to_encrypt=sensitive_keys
)

# Remove plain text config (after verifying encrypted version works)
# Path("config.json").unlink()
```

## References

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [AES-GCM Specification](https://csrc.nist.gov/publications/detail/sp/800-38d/final)
- [PBKDF2 RFC 2898](https://www.rfc-editor.org/rfc/rfc2898)
- [Python Cryptography Library](https://cryptography.io/)

## License

This module is part of the Discord AI Bot project.
