#!/usr/bin/env python3
"""
Credential migration utility for secure vault storage.

This script migrates credentials from .env files to encrypted vault storage
with full backup and rollback capabilities.
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from secrets_manager import SecretsManager, generate_master_key


@dataclass
class MigrationResult:
    """Result of migration operation."""

    success: bool
    message: str
    migrated_keys: List[str]
    backup_path: Optional[str] = None
    vault_path: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return asdict(self)


class CredentialMigrator:
    """
    Manages migration of credentials from .env to encrypted vault.

    Provides secure migration with backup and rollback capabilities.
    """

    # Sensitive keys that should be encrypted
    SENSITIVE_KEYS = {
        "DISCORD_BOT_TOKEN",
        "CLAUDE_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ADMIN_PASSWORD",
        "SECRET_KEY",
        "INITIAL_ADMIN_PASSWORD",
    }

    # Non-sensitive configuration keys
    NON_SENSITIVE_KEYS = {
        "DISCORD_CHANNEL_ID",
        "ADMIN_USERNAME",
        "BOT_PREFIX",
        "LOG_LEVEL",
        "ENVIRONMENT",
    }

    def __init__(
        self,
        env_file: Path,
        vault_file: Path,
        backup_dir: Optional[Path] = None,
        master_key: Optional[str] = None,
    ):
        """
        Initialize credential migrator.

        Args:
            env_file: Path to .env file to migrate from
            vault_file: Path to encrypted vault file
            backup_dir: Directory for backups (defaults to parent of vault_file)
            master_key: Master encryption key (optional, can use env var)

        Raises:
            ValueError: If master key is not provided or found
        """
        self.env_file = Path(env_file)
        self.vault_file = Path(vault_file)

        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = self.vault_file.parent / "backups"

        # Initialize secrets manager
        self.secrets_manager = SecretsManager(master_key=master_key)

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def parse_env_file(self) -> Dict[str, str]:
        """
        Parse .env file and extract key-value pairs.

        Returns:
            Dictionary of environment variables

        Raises:
            FileNotFoundError: If .env file doesn't exist
            ValueError: If .env file is malformed
        """
        if not self.env_file.exists():
            raise FileNotFoundError(f".env file not found: {self.env_file}")

        env_vars: Dict[str, str] = {}

        try:
            with open(self.env_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    # Skip empty lines and comments
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Parse KEY=VALUE format
                    if "=" not in line:
                        raise ValueError(
                            f"Malformed line {line_num}: {line}"
                        )

                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Skip empty values
                    if value:
                        env_vars[key] = value

        except Exception as e:
            raise ValueError(f"Failed to parse .env file: {e}")

        return env_vars

    def create_backup(self) -> Path:
        """
        Create backup of current vault and .env file.

        Returns:
            Path to backup directory

        Raises:
            IOError: If backup creation fails
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"

        try:
            backup_path.mkdir(parents=True, exist_ok=True)

            # Backup .env file
            if self.env_file.exists():
                shutil.copy2(
                    self.env_file,
                    backup_path / ".env.backup"
                )

            # Backup existing vault if it exists
            if self.vault_file.exists():
                shutil.copy2(
                    self.vault_file,
                    backup_path / "vault.json.backup"
                )

            # Create metadata file
            metadata = {
                "timestamp": timestamp,
                "env_file": str(self.env_file),
                "vault_file": str(self.vault_file),
            }

            with open(backup_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            # Set restrictive permissions
            os.chmod(backup_path, 0o700)

            return backup_path

        except Exception as e:
            raise IOError(f"Failed to create backup: {e}")

    def migrate(self, dry_run: bool = False) -> MigrationResult:
        """
        Migrate credentials from .env to encrypted vault.

        Args:
            dry_run: If True, simulate migration without writing

        Returns:
            MigrationResult with migration status

        Raises:
            Exception: If migration fails
        """
        try:
            # Parse .env file
            env_vars = self.parse_env_file()

            if not env_vars:
                return MigrationResult(
                    success=False,
                    message="No credentials found in .env file",
                    migrated_keys=[],
                )

            # Separate sensitive and non-sensitive data
            sensitive_data: Dict[str, str] = {}
            non_sensitive_data: Dict[str, str] = {}

            for key, value in env_vars.items():
                if key in self.SENSITIVE_KEYS:
                    sensitive_data[key] = value
                elif key in self.NON_SENSITIVE_KEYS:
                    non_sensitive_data[key] = value
                else:
                    # Unknown key - treat as sensitive by default
                    sensitive_data[key] = value

            if not sensitive_data:
                return MigrationResult(
                    success=False,
                    message="No sensitive credentials found to migrate",
                    migrated_keys=[],
                )

            if dry_run:
                return MigrationResult(
                    success=True,
                    message=f"Dry run: Would migrate {len(sensitive_data)} credentials",
                    migrated_keys=list(sensitive_data.keys()),
                )

            # Create backup
            backup_path = self.create_backup()

            # Load existing vault if it exists
            existing_config: Dict[str, Any] = {}
            if self.vault_file.exists():
                existing_config = self.secrets_manager.load_encrypted_config(
                    self.vault_file
                )

            # Merge with new data (new data takes precedence)
            vault_data = {
                **existing_config,
                "credentials": {
                    **existing_config.get("credentials", {}),
                    **sensitive_data,
                },
                "config": {
                    **existing_config.get("config", {}),
                    **non_sensitive_data,
                },
                "metadata": {
                    "migrated_at": datetime.utcnow().isoformat(),
                    "source": str(self.env_file),
                    "version": "1.0",
                },
            }

            # Save encrypted vault
            self.secrets_manager.save_encrypted_config(
                vault_data, self.vault_file
            )

            return MigrationResult(
                success=True,
                message=f"Successfully migrated {len(sensitive_data)} credentials",
                migrated_keys=list(sensitive_data.keys()),
                backup_path=str(backup_path),
                vault_path=str(self.vault_file),
            )

        except Exception as e:
            return MigrationResult(
                success=False,
                message=f"Migration failed: {e}",
                migrated_keys=[],
            )

    def rollback(self, backup_path: Path) -> bool:
        """
        Rollback to previous state from backup.

        Args:
            backup_path: Path to backup directory

        Returns:
            True if rollback successful

        Raises:
            FileNotFoundError: If backup doesn't exist
            IOError: If rollback fails
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        try:
            # Restore .env file
            env_backup = backup_path / ".env.backup"
            if env_backup.exists():
                shutil.copy2(env_backup, self.env_file)

            # Restore vault file
            vault_backup = backup_path / "vault.json.backup"
            if vault_backup.exists():
                shutil.copy2(vault_backup, self.vault_file)
            elif self.vault_file.exists():
                # Remove vault if no backup exists (new migration)
                self.vault_file.unlink()

            return True

        except Exception as e:
            raise IOError(f"Rollback failed: {e}")

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.

        Returns:
            List of backup metadata dictionaries
        """
        backups = []

        if not self.backup_dir.exists():
            return backups

        for backup_dir in sorted(self.backup_dir.iterdir(), reverse=True):
            if not backup_dir.is_dir():
                continue

            metadata_file = backup_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                        metadata["path"] = str(backup_dir)
                        backups.append(metadata)
                except Exception:
                    continue

        return backups

    def verify_vault(self) -> bool:
        """
        Verify vault can be decrypted and contains expected data.

        Returns:
            True if vault is valid

        Raises:
            ValueError: If vault is invalid
        """
        if not self.vault_file.exists():
            raise ValueError(f"Vault file not found: {self.vault_file}")

        try:
            # Try to load and decrypt
            data = self.secrets_manager.load_encrypted_config(
                self.vault_file
            )

            # Verify structure
            if "credentials" not in data:
                raise ValueError("Vault missing 'credentials' section")

            if "metadata" not in data:
                raise ValueError("Vault missing 'metadata' section")

            return True

        except Exception as e:
            raise ValueError(f"Vault verification failed: {e}")


def main() -> int:
    """
    Main entry point for migration script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Migrate credentials from .env to encrypted vault"
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        default=".env",
        help="Path to .env file (default: .env)",
    )

    parser.add_argument(
        "--vault-file",
        type=Path,
        default="data/vault.json",
        help="Path to vault file (default: data/vault.json)",
    )

    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Backup directory (default: vault_dir/backups)",
    )

    parser.add_argument(
        "--master-key",
        type=str,
        help="Master encryption key (or use MASTER_ENCRYPTION_KEY env var)",
    )

    parser.add_argument(
        "--generate-key",
        action="store_true",
        help="Generate new master encryption key and exit",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without writing files",
    )

    parser.add_argument(
        "--rollback",
        type=Path,
        help="Rollback to backup at specified path",
    )

    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="List all available backups",
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify vault integrity",
    )

    args = parser.parse_args()

    # Generate key and exit
    if args.generate_key:
        key = generate_master_key()
        print(f"Generated master encryption key:")
        print(f"MASTER_ENCRYPTION_KEY={key}")
        print("\nStore this key securely and set it as an environment variable")
        return 0

    try:
        # Initialize migrator
        migrator = CredentialMigrator(
            env_file=args.env_file,
            vault_file=args.vault_file,
            backup_dir=args.backup_dir,
            master_key=args.master_key,
        )

        # List backups
        if args.list_backups:
            backups = migrator.list_backups()
            if not backups:
                print("No backups found")
                return 0

            print(f"Found {len(backups)} backup(s):")
            for backup in backups:
                print(f"\n  Path: {backup['path']}")
                print(f"  Timestamp: {backup['timestamp']}")
                print(f"  Source: {backup.get('env_file', 'N/A')}")

            return 0

        # Verify vault
        if args.verify:
            if migrator.verify_vault():
                print("✓ Vault verification successful")
                return 0
            else:
                print("✗ Vault verification failed")
                return 1

        # Rollback
        if args.rollback:
            if migrator.rollback(args.rollback):
                print(f"✓ Rolled back to: {args.rollback}")
                return 0
            else:
                print("✗ Rollback failed")
                return 1

        # Migrate credentials
        result = migrator.migrate(dry_run=args.dry_run)

        # Print result
        print(json.dumps(result.to_dict(), indent=2))

        if result.success:
            if not args.dry_run:
                print(f"\n✓ Migration successful!")
                print(f"  Vault: {result.vault_path}")
                print(f"  Backup: {result.backup_path}")
                print(f"  Migrated: {', '.join(result.migrated_keys)}")
            return 0
        else:
            print(f"\n✗ Migration failed: {result.message}")
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
