"""
Security features usage examples.

This module demonstrates how to use the security and credential
management features of the Discord AI Bot.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def example_basic_config():
    """Example: Loading configuration securely."""
    print("\n=== Basic Configuration Loading ===\n")

    from src.config import get_settings

    # Load settings (from .env and environment)
    settings = get_settings()

    print(f"Environment: {settings.environment}")
    print(f"API Host: {settings.api_host}")
    print(f"API Port: {settings.api_port}")

    # Check if credentials are configured
    print(f"\nDiscord configured: {settings.has_discord_config()}")
    print(f"AI providers available: {settings.get_available_llm_providers()}")
    print(f"Preferred AI provider: {settings.get_preferred_ai_provider()}")

    # Validate security configuration
    warnings = settings.validate_security()
    if warnings:
        print("\n⚠️  Security Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\n✅ No security warnings")


def example_config_manager():
    """Example: Using configuration manager."""
    print("\n=== Configuration Manager ===\n")

    from src.config import get_config_manager

    manager = get_config_manager()

    # Get safe config (sensitive values masked)
    safe_config = manager.get_safe_dict()

    print("Safe configuration (secrets masked):")
    print(f"  Secret Key: {safe_config['secret_key']}")
    print(f"  Discord Token: {safe_config.get('discord_bot_token', 'Not set')}")
    print(f"  Anthropic Key: {safe_config.get('anthropic_api_key', 'Not set')}")

    # Update configuration at runtime
    print("\nUpdating bot language to English...")
    manager.update(bot_language="en")

    settings = manager.get_settings()
    print(f"New bot language: {settings.bot_language}")


def example_password_hashing():
    """Example: Password hashing with bcrypt."""
    print("\n=== Password Hashing ===\n")

    from src.auth.security import hash_password, verify_password

    # Hash a password
    password = "SecurePassword123!"
    hashed = hash_password(password)

    print(f"Original password: {password}")
    print(f"Hashed password: {hashed}")

    # Verify password
    is_valid = verify_password(password, hashed)
    print(f"\nPassword verification: {is_valid}")

    # Try wrong password
    is_valid_wrong = verify_password("WrongPassword", hashed)
    print(f"Wrong password verification: {is_valid_wrong}")


def example_jwt_tokens():
    """Example: Creating and verifying JWT tokens."""
    print("\n=== JWT Token Management ===\n")

    from src.auth.security import create_access_token, verify_token
    from datetime import timedelta

    # Create access token
    token = create_access_token(
        user_id=1,
        username="admin",
        is_admin=True,
        expires_delta=timedelta(hours=1)
    )

    print(f"Generated JWT token:")
    print(f"{token[:50]}...{token[-20:]}")

    # Verify and decode token
    token_data = verify_token(token)

    if token_data:
        print(f"\nToken verified successfully:")
        print(f"  User ID: {token_data.user_id}")
        print(f"  Username: {token_data.username}")
        print(f"  Is Admin: {token_data.is_admin}")
        print(f"  Expires: {token_data.exp}")
    else:
        print("\nToken verification failed")


def example_secrets_encryption():
    """Example: Encrypting and decrypting secrets."""
    print("\n=== Secrets Encryption ===\n")

    from src.secrets_manager import SecretsManager

    # Initialize secrets manager
    # In production, master key comes from environment variable
    manager = SecretsManager(master_key="development-master-key-change-in-prod")

    # Encrypt a secret
    secret_value = "my-api-key-sk-123456789"
    encrypted = manager.encrypt(secret_value)

    print("Encrypted secret:")
    print(f"  Ciphertext: {encrypted.ciphertext[:40]}...")
    print(f"  Nonce: {encrypted.nonce}")
    print(f"  Salt: {encrypted.salt}")

    # Decrypt the secret
    decrypted = manager.decrypt(encrypted)
    print(f"\nDecrypted secret: {decrypted}")
    print(f"Match: {decrypted == secret_value}")


def example_encrypt_config_file():
    """Example: Encrypting configuration to file."""
    print("\n=== Encrypted Configuration Files ===\n")

    from src.secrets_manager import SecretsManager
    import tempfile

    # Initialize secrets manager
    manager = SecretsManager(master_key="development-master-key")

    # Configuration with secrets
    config = {
        "discord_bot_token": "MTExMjIyMzMz.GHI789.xyz-abc-123",
        "anthropic_api_key": "sk-ant-api03-1234567890",
        "database_url": "postgresql://user:pass@localhost/db",
        "non_secret_value": "public-data"
    }

    # Create temp file for demo
    with tempfile.NamedTemporaryFile(mode='w', suffix='.encrypted', delete=False) as f:
        temp_path = f.name

    try:
        # Save encrypted config
        manager.save_encrypted_config(config, temp_path)
        print(f"✅ Saved encrypted config to: {temp_path}")

        # Load encrypted config
        decrypted_config = manager.load_encrypted_config(temp_path)

        print("\nDecrypted configuration:")
        for key, value in decrypted_config.items():
            if 'token' in key or 'key' in key or 'password' in key:
                # Mask for display
                print(f"  {key}: {value[:10]}...{value[-5:]}")
            else:
                print(f"  {key}: {value}")

        # Verify all values match
        print(f"\nAll values match: {config == decrypted_config}")

    finally:
        # Cleanup temp file
        if Path(temp_path).exists():
            Path(temp_path).unlink()
            print(f"\n🗑️  Cleaned up temp file")


def example_generate_secure_key():
    """Example: Generating secure keys."""
    print("\n=== Generate Secure Keys ===\n")

    from src.secrets_manager import generate_master_key
    import secrets

    # Generate master encryption key
    master_key = generate_master_key()
    print("Generated master encryption key:")
    print(f"MASTER_ENCRYPTION_KEY={master_key}")

    # Generate SECRET_KEY for JWT
    secret_key = secrets.token_urlsafe(32)
    print("\nGenerated SECRET_KEY for JWT:")
    print(f"SECRET_KEY={secret_key}")

    # Generate random password
    password = secrets.token_urlsafe(16)
    print("\nGenerated random password:")
    print(f"ADMIN_PASSWORD={password}")


def example_complete_workflow():
    """Example: Complete security workflow."""
    print("\n=== Complete Security Workflow ===\n")

    from src.config import get_settings
    from src.auth.security import hash_password
    from src.secrets_manager import SecretsManager

    # 1. Load configuration
    print("1️⃣  Loading configuration...")
    settings = get_settings()

    # 2. Validate security
    print("2️⃣  Validating security...")
    warnings = settings.validate_security()
    if warnings:
        for warning in warnings:
            print(f"   ⚠️  {warning}")

    # 3. Hash admin password (first-time setup)
    print("\n3️⃣  Hashing admin password...")
    admin_password = settings.admin_password
    hashed_password = hash_password(admin_password)
    print(f"   Hashed: {hashed_password[:30]}...")

    # 4. Setup secrets encryption (optional)
    if settings.is_production():
        print("\n4️⃣  Setting up secrets encryption (production)...")
        # In production, load from environment
        master_key = os.getenv("MASTER_ENCRYPTION_KEY")
        if master_key:
            manager = SecretsManager(master_key=master_key)
            print("   ✅ Secrets manager initialized")
        else:
            print("   ⚠️  No MASTER_ENCRYPTION_KEY set")
    else:
        print("\n4️⃣  Skipping encryption (development mode)")

    # 5. Display final status
    print("\n5️⃣  Final status:")
    print(f"   Environment: {settings.environment}")
    print(f"   Discord: {'✅' if settings.has_discord_config() else '❌'}")
    print(f"   AI Providers: {', '.join(settings.get_available_llm_providers()) or 'None'}")
    print(f"   Security warnings: {len(warnings)}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Security Features Usage Examples")
    print("=" * 60)

    try:
        example_basic_config()
        example_config_manager()
        example_password_hashing()
        example_jwt_tokens()
        example_secrets_encryption()
        example_encrypt_config_file()
        example_generate_secure_key()
        example_complete_workflow()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
