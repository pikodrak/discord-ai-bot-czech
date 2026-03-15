"""
Tests for credential migration utility.

Verifies migration, backup, rollback, and verification functionality.
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from secrets_manager import SecretsManager, generate_master_key
from migrate_credentials import CredentialMigrator, MigrationResult


@pytest.fixture
def master_key() -> str:
    """
    Generate test master encryption key.

    Returns:
        Base64-encoded master key
    """
    return generate_master_key()


@pytest.fixture
def temp_dir() -> Path:
    """
    Create temporary directory for tests.

    Yields:
        Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_env_file(temp_dir: Path) -> Path:
    """
    Create sample .env file for testing.

    Args:
        temp_dir: Temporary directory

    Returns:
        Path to created .env file
    """
    env_file = temp_dir / ".env"
    content = """# Discord Configuration
DISCORD_BOT_TOKEN=test_discord_token_123
DISCORD_CHANNEL_ID=123456789

# AI API Keys
CLAUDE_API_KEY=test_claude_key_456
GOOGLE_API_KEY=test_google_key_789
OPENAI_API_KEY=

# Admin Interface
ADMIN_USERNAME=admin
ADMIN_PASSWORD=test_admin_pass
SECRET_KEY=test_secret_key_xyz

# Bot Settings
BOT_PREFIX=!
LOG_LEVEL=INFO
"""
    env_file.write_text(content)
    return env_file


@pytest.fixture
def migrator(
    sample_env_file: Path,
    temp_dir: Path,
    master_key: str
) -> CredentialMigrator:
    """
    Create CredentialMigrator instance for testing.

    Args:
        sample_env_file: Path to sample .env file
        temp_dir: Temporary directory
        master_key: Master encryption key

    Returns:
        CredentialMigrator instance
    """
    vault_file = temp_dir / "vault.json"
    backup_dir = temp_dir / "backups"

    return CredentialMigrator(
        env_file=sample_env_file,
        vault_file=vault_file,
        backup_dir=backup_dir,
        master_key=master_key,
    )


class TestEnvParsing:
    """Test .env file parsing functionality."""

    def test_parse_valid_env_file(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test parsing valid .env file."""
        env_vars = migrator.parse_env_file()

        assert "DISCORD_BOT_TOKEN" in env_vars
        assert "CLAUDE_API_KEY" in env_vars
        assert "ADMIN_USERNAME" in env_vars
        assert env_vars["DISCORD_BOT_TOKEN"] == "test_discord_token_123"
        assert env_vars["BOT_PREFIX"] == "!"

    def test_parse_skips_comments(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test that comments are skipped."""
        env_vars = migrator.parse_env_file()

        # Comments should not be in parsed vars
        for key in env_vars.keys():
            assert not key.startswith("#")

    def test_parse_skips_empty_values(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test that empty values are skipped."""
        env_vars = migrator.parse_env_file()

        # OPENAI_API_KEY is empty in sample
        assert "OPENAI_API_KEY" not in env_vars

    def test_parse_missing_file(
        self,
        temp_dir: Path,
        master_key: str
    ) -> None:
        """Test error on missing .env file."""
        migrator = CredentialMigrator(
            env_file=temp_dir / "nonexistent.env",
            vault_file=temp_dir / "vault.json",
            master_key=master_key,
        )

        with pytest.raises(FileNotFoundError):
            migrator.parse_env_file()

    def test_parse_malformed_file(
        self,
        temp_dir: Path,
        master_key: str
    ) -> None:
        """Test error on malformed .env file."""
        env_file = temp_dir / ".env"
        env_file.write_text("INVALID_LINE_WITHOUT_EQUALS")

        migrator = CredentialMigrator(
            env_file=env_file,
            vault_file=temp_dir / "vault.json",
            master_key=master_key,
        )

        with pytest.raises(ValueError, match="Malformed line"):
            migrator.parse_env_file()


class TestMigration:
    """Test migration functionality."""

    def test_migrate_success(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test successful migration."""
        result = migrator.migrate()

        assert result.success
        assert len(result.migrated_keys) > 0
        assert "DISCORD_BOT_TOKEN" in result.migrated_keys
        assert "CLAUDE_API_KEY" in result.migrated_keys
        assert result.vault_path is not None
        assert result.backup_path is not None

    def test_migrate_creates_vault_file(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test that migration creates vault file."""
        assert not migrator.vault_file.exists()

        migrator.migrate()

        assert migrator.vault_file.exists()

    def test_migrate_encrypts_sensitive_data(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test that sensitive data is encrypted."""
        migrator.migrate()

        # Read raw vault file
        with open(migrator.vault_file, "r") as f:
            raw_data = json.load(f)

        # Sensitive data should be encrypted (dict with ciphertext, nonce, salt)
        credentials = raw_data["credentials"]
        assert "DISCORD_BOT_TOKEN" in credentials
        assert isinstance(credentials["DISCORD_BOT_TOKEN"], dict)
        assert "ciphertext" in credentials["DISCORD_BOT_TOKEN"]
        assert "nonce" in credentials["DISCORD_BOT_TOKEN"]
        assert "salt" in credentials["DISCORD_BOT_TOKEN"]

    def test_migrate_preserves_non_sensitive_data(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test that non-sensitive data is not encrypted."""
        migrator.migrate()

        # Load decrypted vault
        vault_data = migrator.secrets_manager.load_encrypted_config(
            migrator.vault_file
        )

        # Non-sensitive config should be plain text
        config = vault_data.get("config", {})
        assert config.get("BOT_PREFIX") == "!"
        assert config.get("ADMIN_USERNAME") == "admin"

    def test_migrate_dry_run(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test dry run mode."""
        result = migrator.migrate(dry_run=True)

        assert result.success
        assert "Dry run" in result.message
        assert len(result.migrated_keys) > 0
        assert not migrator.vault_file.exists()  # No file created

    def test_migrate_creates_backup(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test that backup is created."""
        result = migrator.migrate()

        assert result.backup_path is not None
        backup_path = Path(result.backup_path)
        assert backup_path.exists()
        assert (backup_path / ".env.backup").exists()
        assert (backup_path / "metadata.json").exists()

    def test_migrate_merges_existing_vault(
        self,
        migrator: CredentialMigrator,
        master_key: str
    ) -> None:
        """Test that existing vault data is merged."""
        # Create existing vault with some data
        existing_data = {
            "credentials": {
                "EXISTING_KEY": "existing_value"
            },
            "config": {
                "EXISTING_CONFIG": "config_value"
            }
        }

        secrets_manager = SecretsManager(master_key=master_key)
        secrets_manager.save_encrypted_config(
            existing_data,
            migrator.vault_file
        )

        # Migrate
        migrator.migrate()

        # Load vault
        vault_data = secrets_manager.load_encrypted_config(
            migrator.vault_file
        )

        # Should have both old and new data
        assert "EXISTING_KEY" in vault_data["credentials"]
        assert "DISCORD_BOT_TOKEN" in vault_data["credentials"]


class TestBackupAndRollback:
    """Test backup and rollback functionality."""

    def test_create_backup(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test backup creation."""
        backup_path = migrator.create_backup()

        assert backup_path.exists()
        assert (backup_path / ".env.backup").exists()
        assert (backup_path / "metadata.json").exists()

    def test_backup_metadata(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test backup metadata is correct."""
        backup_path = migrator.create_backup()

        with open(backup_path / "metadata.json", "r") as f:
            metadata = json.load(f)

        assert "timestamp" in metadata
        assert "env_file" in metadata
        assert "vault_file" in metadata

    def test_list_backups(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test listing backups."""
        # Create multiple backups
        migrator.create_backup()
        migrator.create_backup()

        backups = migrator.list_backups()

        assert len(backups) >= 2
        assert all("timestamp" in b for b in backups)
        assert all("path" in b for b in backups)

    def test_rollback_success(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test successful rollback."""
        # Perform migration
        result = migrator.migrate()
        backup_path = Path(result.backup_path)

        # Modify vault
        migrator.vault_file.write_text("modified")

        # Rollback
        success = migrator.rollback(backup_path)

        assert success
        # Vault should be restored or removed

    def test_rollback_missing_backup(
        self,
        migrator: CredentialMigrator,
        temp_dir: Path
    ) -> None:
        """Test rollback with missing backup."""
        with pytest.raises(FileNotFoundError):
            migrator.rollback(temp_dir / "nonexistent_backup")


class TestVerification:
    """Test vault verification functionality."""

    def test_verify_valid_vault(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test verification of valid vault."""
        migrator.migrate()

        assert migrator.verify_vault()

    def test_verify_missing_vault(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test verification fails for missing vault."""
        with pytest.raises(ValueError, match="not found"):
            migrator.verify_vault()

    def test_verify_invalid_vault(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test verification fails for invalid vault."""
        # Create invalid vault
        migrator.vault_file.write_text("not valid json")

        with pytest.raises(ValueError, match="verification failed"):
            migrator.verify_vault()

    def test_verify_wrong_key(
        self,
        migrator: CredentialMigrator,
        temp_dir: Path
    ) -> None:
        """Test verification fails with wrong master key."""
        # Migrate with original key
        migrator.migrate()

        # Try to verify with different key
        wrong_migrator = CredentialMigrator(
            env_file=migrator.env_file,
            vault_file=migrator.vault_file,
            master_key=generate_master_key(),  # Different key
        )

        with pytest.raises(ValueError, match="verification failed"):
            wrong_migrator.verify_vault()


class TestMigrationResult:
    """Test MigrationResult dataclass."""

    def test_result_creation(self) -> None:
        """Test MigrationResult creation."""
        result = MigrationResult(
            success=True,
            message="Test message",
            migrated_keys=["KEY1", "KEY2"],
        )

        assert result.success
        assert result.message == "Test message"
        assert len(result.migrated_keys) == 2
        assert result.timestamp  # Auto-generated

    def test_result_to_dict(self) -> None:
        """Test MigrationResult to_dict conversion."""
        result = MigrationResult(
            success=True,
            message="Test",
            migrated_keys=["KEY1"],
            backup_path="/path/to/backup",
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["message"] == "Test"
        assert result_dict["backup_path"] == "/path/to/backup"


class TestEndToEnd:
    """End-to-end migration tests."""

    def test_full_migration_cycle(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test complete migration, verify, and rollback cycle."""
        # 1. Migrate
        result = migrator.migrate()
        assert result.success

        backup_path = Path(result.backup_path)

        # 2. Verify
        assert migrator.verify_vault()

        # 3. Load and check data
        vault_data = migrator.secrets_manager.load_encrypted_config(
            migrator.vault_file
        )

        assert vault_data["credentials"]["DISCORD_BOT_TOKEN"] == "test_discord_token_123"
        assert vault_data["credentials"]["ADMIN_PASSWORD"] == "test_admin_pass"

        # 4. Rollback
        assert migrator.rollback(backup_path)

    def test_multiple_migrations(
        self,
        migrator: CredentialMigrator
    ) -> None:
        """Test multiple migrations don't corrupt data."""
        # First migration
        result1 = migrator.migrate()
        assert result1.success

        # Second migration (should merge/update)
        result2 = migrator.migrate()
        assert result2.success

        # Verify still works
        assert migrator.verify_vault()

        # Check backups were created
        backups = migrator.list_backups()
        assert len(backups) >= 2


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_env_file(
        self,
        temp_dir: Path,
        master_key: str
    ) -> None:
        """Test migration with empty .env file."""
        env_file = temp_dir / ".env"
        env_file.write_text("")

        migrator = CredentialMigrator(
            env_file=env_file,
            vault_file=temp_dir / "vault.json",
            master_key=master_key,
        )

        result = migrator.migrate()
        assert not result.success
        assert "No credentials" in result.message

    def test_only_comments_env_file(
        self,
        temp_dir: Path,
        master_key: str
    ) -> None:
        """Test migration with only comments in .env."""
        env_file = temp_dir / ".env"
        env_file.write_text("# Comment 1\n# Comment 2\n")

        migrator = CredentialMigrator(
            env_file=env_file,
            vault_file=temp_dir / "vault.json",
            master_key=master_key,
        )

        result = migrator.migrate()
        assert not result.success

    def test_no_sensitive_keys(
        self,
        temp_dir: Path,
        master_key: str
    ) -> None:
        """Test migration with only non-sensitive keys."""
        env_file = temp_dir / ".env"
        env_file.write_text("BOT_PREFIX=!\nLOG_LEVEL=INFO")

        migrator = CredentialMigrator(
            env_file=env_file,
            vault_file=temp_dir / "vault.json",
            master_key=master_key,
        )

        result = migrator.migrate()
        assert not result.success
        assert "No sensitive credentials" in result.message
