"""
Secrets Manager Usage Examples

Demonstrates how to use the SecretsManager for secure credential storage.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from secrets_manager import (
    SecretsManager,
    create_secrets_manager,
    EncryptionError,
    DecryptionError,
    MasterKeyError
)


def example_basic_encryption():
    """Example 1: Basic encryption and decryption."""
    print("=" * 60)
    print("Example 1: Basic Encryption/Decryption")
    print("=" * 60)

    # Initialize with a master password
    manager = SecretsManager(master_key="my-secure-password-123")

    # Encrypt a value
    secret_token = "discord_token_abc123xyz"
    encrypted = manager.encrypt_value(secret_token)
    print(f"Original: {secret_token}")
    print(f"Encrypted: {encrypted[:50]}...")

    # Decrypt the value
    decrypted = manager.decrypt_value(encrypted)
    print(f"Decrypted: {decrypted}")
    print(f"Match: {decrypted == secret_token}")
    print()


def example_master_key_from_file():
    """Example 2: Generate and use master key from file."""
    print("=" * 60)
    print("Example 2: Master Key File Management")
    print("=" * 60)

    # Generate a random master key and save to file
    manager = SecretsManager()
    key_file = Path("temp_master.key")

    try:
        generated_key = manager.generate_master_key(output_file=key_file)
        print(f"Generated master key: {generated_key[:20]}...")
        print(f"Saved to: {key_file}")
        print(f"File permissions: {oct(key_file.stat().st_mode)[-3:]}")

        # Load from file
        manager2 = SecretsManager(key_file=key_file)
        encrypted = manager2.encrypt_value("secret-data")
        print(f"Encrypted with file-based key: {encrypted[:50]}...")
        print()

    finally:
        # Cleanup
        if key_file.exists():
            key_file.unlink()


def example_encrypt_config():
    """Example 3: Encrypt configuration files."""
    print("=" * 60)
    print("Example 3: Encrypted Configuration Files")
    print("=" * 60)

    manager = SecretsManager(master_key="config-password")

    # Sample configuration with sensitive data
    config = {
        "discord_token": "MTIzNDU2Nzg5.ABCDEF.xyz123",
        "anthropic_api_key": "sk-ant-api03-abc123",
        "database_url": "postgresql://user:pass@localhost/db",
        "app_name": "Discord Bot",
        "debug": True
    }

    # Save encrypted config (only encrypt sensitive keys)
    output_file = Path("temp_config.encrypted.json")

    try:
        sensitive_keys = ["discord_token", "anthropic_api_key", "database_url"]
        manager.save_encrypted_config(config, output_file, sensitive_keys)
        print(f"Saved encrypted config to: {output_file}")

        # Read the encrypted file
        with open(output_file) as f:
            print("\nEncrypted file content (first 200 chars):")
            print(f.read()[:200] + "...")

        # Load and decrypt
        decrypted_config = manager.load_encrypted_config(output_file)
        print("\nDecrypted config:")
        for key, value in decrypted_config.items():
            if key in sensitive_keys:
                print(f"  {key}: {value[:20]}... (decrypted)")
            else:
                print(f"  {key}: {value}")
        print()

    finally:
        # Cleanup
        if output_file.exists():
            output_file.unlink()


def example_dict_encryption():
    """Example 4: Encrypt dictionary values."""
    print("=" * 60)
    print("Example 4: Dictionary Encryption")
    print("=" * 60)

    manager = SecretsManager(master_key="dict-password")

    # Dictionary with mixed sensitive/non-sensitive data
    credentials = {
        "service": "discord",
        "username": "my_bot",
        "password": "super_secret_password",
        "api_key": "sk-1234567890abcdef",
        "enabled": True
    }

    # Encrypt only sensitive fields
    encrypted_creds = manager.encrypt_dict(
        credentials,
        keys_to_encrypt=["password", "api_key"]
    )

    print("Original credentials:")
    for k, v in credentials.items():
        print(f"  {k}: {v}")

    print("\nEncrypted credentials:")
    for k, v in encrypted_creds.items():
        if k in ["password", "api_key"]:
            print(f"  {k}: {str(v)[:40]}... (encrypted)")
        else:
            print(f"  {k}: {v}")

    # Decrypt
    decrypted_creds = manager.decrypt_dict(
        encrypted_creds,
        keys_to_decrypt=["password", "api_key"]
    )

    print("\nDecrypted credentials:")
    for k, v in decrypted_creds.items():
        print(f"  {k}: {v}")
    print()


def example_key_rotation():
    """Example 5: Key rotation."""
    print("=" * 60)
    print("Example 5: Key Rotation")
    print("=" * 60)

    manager = SecretsManager()

    # Encrypt with old password
    old_password = "old-password-2024"
    secret = "sensitive-data-to-protect"

    encrypted_old = manager.encrypt_value(secret, password=old_password)
    print(f"Encrypted with old password: {encrypted_old[:50]}...")

    # Rotate to new password
    new_password = "new-password-2025"
    encrypted_new = manager.rotate_encryption(
        encrypted_old,
        old_password=old_password,
        new_password=new_password
    )
    print(f"Re-encrypted with new password: {encrypted_new[:50]}...")

    # Verify decryption works with new password
    decrypted = manager.decrypt_value(encrypted_new, password=new_password)
    print(f"Decrypted with new password: {decrypted}")
    print(f"Match: {decrypted == secret}")
    print()


def example_error_handling():
    """Example 6: Error handling."""
    print("=" * 60)
    print("Example 6: Error Handling")
    print("=" * 60)

    # Wrong password
    manager = SecretsManager(master_key="correct-password")
    encrypted = manager.encrypt_value("secret")

    manager2 = SecretsManager(master_key="wrong-password")
    try:
        manager2.decrypt_value(encrypted)
    except DecryptionError as e:
        print(f"✓ Caught DecryptionError: {str(e)[:60]}...")

    # No master key set
    manager3 = SecretsManager()
    try:
        manager3.encrypt_value("data")
    except MasterKeyError as e:
        print(f"✓ Caught MasterKeyError: {e}")

    # Invalid encrypted data
    try:
        manager.decrypt_value("not-encrypted-data")
    except DecryptionError as e:
        print(f"✓ Caught DecryptionError: {str(e)[:60]}...")

    print()


def example_factory_function():
    """Example 7: Using factory function."""
    print("=" * 60)
    print("Example 7: Factory Function")
    print("=" * 60)

    # Create with password
    manager1 = create_secrets_manager(password="my-password")
    print("✓ Created manager with password")

    # Create with generated key
    key_file = Path("temp_generated.key")
    try:
        manager2 = create_secrets_manager(generate_key=True, key_output_file=key_file)
        print(f"✓ Created manager with generated key: {key_file}")

        # Test encryption
        encrypted = manager2.encrypt_value("test-data")
        print(f"✓ Encrypted: {encrypted[:40]}...")

    finally:
        if key_file.exists():
            key_file.unlink()

    print()


def example_is_encrypted_check():
    """Example 8: Check if value is encrypted."""
    print("=" * 60)
    print("Example 8: Check Encryption Status")
    print("=" * 60)

    manager = SecretsManager(master_key="password")

    plain_text = "not-encrypted"
    encrypted_text = manager.encrypt_value("encrypted-data")

    print(f"Is '{plain_text}' encrypted? {manager.is_encrypted(plain_text)}")
    print(f"Is encrypted value encrypted? {manager.is_encrypted(encrypted_text)}")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "SECRETS MANAGER EXAMPLES" + " " * 19 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    examples = [
        example_basic_encryption,
        example_master_key_from_file,
        example_encrypt_config,
        example_dict_encryption,
        example_key_rotation,
        example_error_handling,
        example_factory_function,
        example_is_encrypted_check,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"❌ Example failed: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
