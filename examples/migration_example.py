#!/usr/bin/env python3
"""
Example demonstrating credential migration workflow.

This script shows the complete migration process from .env to encrypted vault.
"""

import sys
from pathlib import Path

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from secrets_manager import generate_master_key, SecretsManager
from migrate_credentials import CredentialMigrator


def example_migration_workflow() -> None:
    """
    Demonstrate complete migration workflow.

    This example shows:
    1. Generating master key
    2. Creating migrator
    3. Running dry run
    4. Performing migration
    5. Verifying vault
    6. Loading credentials
    7. Listing backups
    """
    print("=" * 60)
    print("Credential Migration Example")
    print("=" * 60)

    # Step 1: Generate master key
    print("\n1. Generating master encryption key...")
    master_key = generate_master_key()
    print(f"   Generated key: {master_key[:20]}...")
    print("   (Store this securely!)")

    # Step 2: Setup paths
    print("\n2. Setting up paths...")
    env_file = Path(".env")
    vault_file = Path("data/vault.json")
    backup_dir = Path("data/backups")

    print(f"   .env file: {env_file}")
    print(f"   Vault file: {vault_file}")
    print(f"   Backup dir: {backup_dir}")

    # Step 3: Create migrator
    print("\n3. Creating migrator...")
    migrator = CredentialMigrator(
        env_file=env_file,
        vault_file=vault_file,
        backup_dir=backup_dir,
        master_key=master_key,
    )
    print("   Migrator created successfully")

    # Step 4: Dry run
    print("\n4. Running dry-run migration...")
    dry_result = migrator.migrate(dry_run=True)

    if dry_result.success:
        print(f"   ✓ Dry run successful")
        print(f"   Keys to migrate: {', '.join(dry_result.migrated_keys)}")
    else:
        print(f"   ✗ Dry run failed: {dry_result.message}")
        return

    # Step 5: Actual migration
    print("\n5. Performing actual migration...")
    result = migrator.migrate()

    if result.success:
        print(f"   ✓ Migration successful")
        print(f"   Vault: {result.vault_path}")
        print(f"   Backup: {result.backup_path}")
        print(f"   Migrated keys: {', '.join(result.migrated_keys)}")
    else:
        print(f"   ✗ Migration failed: {result.message}")
        return

    # Step 6: Verify vault
    print("\n6. Verifying vault integrity...")
    try:
        if migrator.verify_vault():
            print("   ✓ Vault verification successful")
    except ValueError as e:
        print(f"   ✗ Vault verification failed: {e}")
        return

    # Step 7: Load and use credentials
    print("\n7. Loading credentials from vault...")
    secrets_manager = SecretsManager(master_key=master_key)

    try:
        vault_data = secrets_manager.load_encrypted_config(vault_file)

        print("   ✓ Vault loaded successfully")
        print("\n   Credentials available:")
        for key in vault_data.get("credentials", {}).keys():
            print(f"     - {key}")

        print("\n   Configuration values:")
        for key, value in vault_data.get("config", {}).items():
            print(f"     - {key}: {value}")

    except Exception as e:
        print(f"   ✗ Failed to load vault: {e}")
        return

    # Step 8: List backups
    print("\n8. Listing available backups...")
    backups = migrator.list_backups()

    if backups:
        print(f"   Found {len(backups)} backup(s):")
        for backup in backups[:3]:  # Show first 3
            print(f"     - {backup['timestamp']}")
            print(f"       Path: {backup['path']}")
    else:
        print("   No backups found")

    print("\n" + "=" * 60)
    print("Migration workflow completed successfully!")
    print("=" * 60)


def example_rollback_workflow() -> None:
    """
    Demonstrate rollback workflow.

    Shows how to rollback to a previous state.
    """
    print("\n" + "=" * 60)
    print("Rollback Example")
    print("=" * 60)

    master_key = generate_master_key()
    env_file = Path(".env")
    vault_file = Path("data/vault.json")

    migrator = CredentialMigrator(
        env_file=env_file,
        vault_file=vault_file,
        master_key=master_key,
    )

    # List backups
    print("\n1. Listing available backups...")
    backups = migrator.list_backups()

    if not backups:
        print("   No backups available for rollback")
        return

    # Get most recent backup
    latest_backup = backups[0]
    print(f"   Latest backup: {latest_backup['timestamp']}")
    print(f"   Path: {latest_backup['path']}")

    # Perform rollback
    print("\n2. Rolling back to latest backup...")
    try:
        backup_path = Path(latest_backup['path'])
        if migrator.rollback(backup_path):
            print("   ✓ Rollback successful")
            print(f"   Restored from: {backup_path}")
        else:
            print("   ✗ Rollback failed")

    except Exception as e:
        print(f"   ✗ Rollback error: {e}")

    print("\n" + "=" * 60)


def example_programmatic_usage() -> None:
    """
    Demonstrate programmatic usage in application code.

    Shows how to use SecretsManager in application.
    """
    print("\n" + "=" * 60)
    print("Programmatic Usage Example")
    print("=" * 60)

    # Assume master key from environment
    master_key = generate_master_key()  # In practice: os.getenv("MASTER_ENCRYPTION_KEY")

    print("\n1. Initialize SecretsManager...")
    manager = SecretsManager(master_key=master_key)
    print("   ✓ Manager initialized")

    print("\n2. Load encrypted configuration...")
    try:
        config = manager.load_encrypted_config("data/vault.json")
        print("   ✓ Configuration loaded")

        # Access credentials
        print("\n3. Accessing credentials...")

        discord_token = config["credentials"].get("DISCORD_BOT_TOKEN")
        if discord_token:
            print(f"   Discord token: {discord_token[:20]}...")

        admin_password = config["credentials"].get("ADMIN_PASSWORD")
        if admin_password:
            print(f"   Admin password: {'*' * len(admin_password)}")

        # Access config
        print("\n4. Accessing configuration...")
        bot_prefix = config["config"].get("BOT_PREFIX", "!")
        log_level = config["config"].get("LOG_LEVEL", "INFO")

        print(f"   Bot prefix: {bot_prefix}")
        print(f"   Log level: {log_level}")

    except FileNotFoundError:
        print("   ✗ Vault file not found")
        print("   Run migration first!")
    except Exception as e:
        print(f"   ✗ Error loading config: {e}")

    print("\n" + "=" * 60)


def example_manual_encryption() -> None:
    """
    Demonstrate manual encryption/decryption.

    Shows low-level encryption operations.
    """
    print("\n" + "=" * 60)
    print("Manual Encryption Example")
    print("=" * 60)

    master_key = generate_master_key()
    manager = SecretsManager(master_key=master_key)

    # Encrypt single value
    print("\n1. Encrypting single value...")
    plaintext = "super_secret_api_key"
    encrypted = manager.encrypt(plaintext)

    print(f"   Plaintext: {plaintext}")
    print(f"   Ciphertext: {encrypted.ciphertext[:40]}...")
    print(f"   Nonce: {encrypted.nonce}")
    print(f"   Salt: {encrypted.salt}")

    # Decrypt value
    print("\n2. Decrypting value...")
    decrypted = manager.decrypt(encrypted)
    print(f"   Decrypted: {decrypted}")
    print(f"   Match: {decrypted == plaintext}")

    # Encrypt dictionary
    print("\n3. Encrypting dictionary...")
    data = {
        "api_key": "secret123",
        "password": "pass456",
        "username": "admin",  # Won't be encrypted
    }

    encrypted_dict = manager.encrypt_dict(
        data,
        keys_to_encrypt=["api_key", "password"]
    )

    print(f"   Original: {data}")
    print(f"   Encrypted keys: api_key, password")
    print(f"   Username (not encrypted): {encrypted_dict['username']}")

    # Decrypt dictionary
    print("\n4. Decrypting dictionary...")
    decrypted_dict = manager.decrypt_dict(encrypted_dict)
    print(f"   Decrypted: {decrypted_dict}")
    print(f"   Match: {decrypted_dict == data}")

    print("\n" + "=" * 60)


def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 70)
    print(" " * 15 + "CREDENTIAL MIGRATION EXAMPLES")
    print("=" * 70)

    try:
        # Run examples
        example_migration_workflow()
        example_programmatic_usage()
        example_manual_encryption()
        example_rollback_workflow()

        print("\n" + "=" * 70)
        print(" " * 20 + "ALL EXAMPLES COMPLETED")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
