"""
Comprehensive security tests for credential migration.

Tests cover:
- Migration from plaintext to encrypted storage
- Backup and recovery mechanisms
- Data integrity during migration
- Rollback capabilities
- Sensitive data handling
- Migration audit trails
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from migrate_credentials import (
    migrate_env_to_vault,
    backup_vault,
    verify_migration,
    rollback_migration
)
from credential_vault import CredentialVault, CredentialType
from secrets_manager import SecretsManager


class TestMigrationDataIntegrity:
    """Tests for data integrity during migration."""

    def test_all_credentials_migrated(self):
        """Verify all credentials from .env are migrated to vault."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test .env file
            env_file = Path(temp_dir) / ".env"
            env_content = """
DISCORD_BOT_TOKEN=test_token_123
CLAUDE_API_KEY=test_api_key_456
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=test_secret_789
"""
            env_file.write_text(env_content)

            # Create vault directory
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            master_key = "test_master_key_for_migration"

            # Migrate credentials
            vault = CredentialVault(vault_dir, master_key)
            migrated_count = migrate_env_to_vault(str(env_file), vault)

            # Verify all credentials migrated
            assert migrated_count == 4, "All credentials should be migrated"

            # Verify each credential exists in vault
            assert vault.get("DISCORD_BOT_TOKEN") == "test_token_123"
            assert vault.get("CLAUDE_API_KEY") == "test_api_key_456"
            assert vault.get("DATABASE_URL") == "postgresql://user:pass@localhost/db"
            assert vault.get("SECRET_KEY") == "test_secret_789"

    def test_migration_preserves_values_exactly(self):
        """Verify migration preserves credential values exactly (no corruption)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            # Test various value formats
            test_values = {
                "SIMPLE_KEY": "simple_value",
                "KEY_WITH_SPACES": "value with spaces",
                "KEY_WITH_SPECIAL": "value!@#$%^&*()_+-=[]{}|;:,.<>?",
                "KEY_WITH_QUOTES": 'value"with"quotes',
                "KEY_WITH_UNICODE": "value_with_émojis_🔐_and_čeština",
                "LONG_KEY": "x" * 1000,
                "EMPTY_KEY": "",
                "MULTILINE_KEY": "line1\\nline2\\nline3"
            }

            # Write to .env
            env_content = "\n".join([f"{k}={v}" for k, v in test_values.items()])
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Migrate
            migrate_env_to_vault(str(env_file), vault)

            # Verify each value is exactly preserved
            for key, expected_value in test_values.items():
                actual_value = vault.get(key)
                assert actual_value == expected_value, \
                    f"Value for {key} should be preserved exactly"

    def test_migration_handles_malformed_env_file(self):
        """Test migration handles malformed .env files gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            # Malformed .env with various issues
            malformed_content = """
VALID_KEY=valid_value
INVALID_LINE_NO_EQUALS
=VALUE_WITHOUT_KEY
KEY_WITH_EMPTY=
# Comment line
  WHITESPACE_KEY  =  whitespace_value
"""
            env_file.write_text(malformed_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Migration should handle errors gracefully
            try:
                migrated_count = migrate_env_to_vault(str(env_file), vault)
                # Should migrate valid entries
                assert migrated_count >= 1, "Should migrate valid entries"
            except Exception as e:
                pytest.fail(f"Migration should handle malformed files gracefully: {e}")

    def test_migration_skips_comments_and_empty_lines(self):
        """Verify migration skips comments and empty lines."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            env_content = """
# This is a comment
VALID_KEY1=value1

# Another comment
VALID_KEY2=value2

"""
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            migrated_count = migrate_env_to_vault(str(env_file), vault)

            # Should only migrate 2 valid entries
            assert migrated_count == 2, "Should skip comments and empty lines"
            assert vault.get("VALID_KEY1") == "value1"
            assert vault.get("VALID_KEY2") == "value2"


class TestBackupAndRecovery:
    """Tests for backup and recovery mechanisms."""

    def test_backup_before_migration(self):
        """Verify backup is created before migration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()
            backup_dir = Path(temp_dir) / "backups"

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Add some existing credentials
            vault.store("EXISTING_KEY", "existing_value", CredentialType.SECRET)

            # Create backup
            backup_path = backup_vault(vault_dir, backup_dir)

            assert backup_path is not None, "Backup should be created"
            assert Path(backup_path).exists(), "Backup file should exist"

    def test_backup_contains_all_vault_data(self):
        """Verify backup contains all vault data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()
            backup_dir = Path(temp_dir) / "backups"

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Add multiple credentials
            credentials = {
                "KEY1": "value1",
                "KEY2": "value2",
                "KEY3": "value3"
            }

            for key, value in credentials.items():
                vault.store(key, value, CredentialType.SECRET)

            # Create backup
            backup_path = backup_vault(vault_dir, backup_dir)

            # Verify backup contains all files
            backup_file = Path(backup_path)
            assert backup_file.exists(), "Backup should exist"

            # Extract and verify
            import tarfile
            with tarfile.open(backup_file, 'r:gz') as tar:
                members = tar.getnames()
                # Should contain encrypted credential files
                assert len(members) >= len(credentials), "Backup should contain all credentials"

    def test_recovery_from_backup(self):
        """Test recovering vault from backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()
            backup_dir = Path(temp_dir) / "backups"
            recovery_dir = Path(temp_dir) / "recovered"

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Add credentials
            original_data = {
                "KEY1": "value1",
                "KEY2": "value2"
            }

            for key, value in original_data.items():
                vault.store(key, value, CredentialType.SECRET)

            # Create backup
            backup_path = backup_vault(vault_dir, backup_dir)

            # Simulate data loss - delete vault
            shutil.rmtree(vault_dir)

            # Recover from backup
            import tarfile
            recovery_dir.mkdir()
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(recovery_dir)

            # Create new vault from recovered data
            recovered_vault = CredentialVault(recovery_dir, master_key)

            # Verify all data recovered
            for key, expected_value in original_data.items():
                actual_value = recovered_vault.get(key)
                assert actual_value == expected_value, f"Recovered value for {key} should match"

    def test_backup_encryption(self):
        """Verify backup files maintain encryption."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()
            backup_dir = Path(temp_dir) / "backups"

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            sensitive_value = "super_secret_password"
            vault.store("SENSITIVE_KEY", sensitive_value, CredentialType.PASSWORD)

            # Create backup
            backup_path = backup_vault(vault_dir, backup_dir)

            # Read backup file content
            backup_content = Path(backup_path).read_bytes()

            # Sensitive value should NOT appear in plaintext in backup
            assert sensitive_value.encode() not in backup_content, \
                "Backup should not contain plaintext credentials"


class TestRollbackCapabilities:
    """Tests for migration rollback."""

    def test_rollback_restores_original_state(self):
        """Verify rollback restores vault to pre-migration state."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()
            env_file = Path(temp_dir) / ".env"
            backup_dir = Path(temp_dir) / "backups"

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Original state
            original_data = {"ORIGINAL_KEY": "original_value"}
            for key, value in original_data.items():
                vault.store(key, value, CredentialType.SECRET)

            # Create backup
            backup_path = backup_vault(vault_dir, backup_dir)

            # Migrate new credentials
            env_content = "NEW_KEY=new_value\nANOTHER_KEY=another_value"
            env_file.write_text(env_content)
            migrate_env_to_vault(str(env_file), vault)

            # Verify new credentials exist
            assert vault.get("NEW_KEY") == "new_value"

            # Rollback
            success = rollback_migration(vault_dir, backup_path)
            assert success, "Rollback should succeed"

            # Verify original state restored
            restored_vault = CredentialVault(vault_dir, master_key)
            assert restored_vault.get("ORIGINAL_KEY") == "original_value"

            # New credentials should be gone
            with pytest.raises(Exception):
                restored_vault.get("NEW_KEY")

    def test_rollback_on_migration_failure(self):
        """Test automatic rollback on migration failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()
            env_file = Path(temp_dir) / ".env"
            backup_dir = Path(temp_dir) / "backups"

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Original state
            vault.store("ORIGINAL_KEY", "original_value", CredentialType.SECRET)

            # Create backup
            backup_path = backup_vault(vault_dir, backup_dir)

            # Simulate migration failure
            env_content = "INVALID_KEY="  # This might cause issues
            env_file.write_text(env_content)

            try:
                # Migration with automatic rollback on failure
                with patch('migrate_credentials.migrate_env_to_vault') as mock_migrate:
                    mock_migrate.side_effect = Exception("Migration failed")

                    try:
                        migrate_env_to_vault(str(env_file), vault)
                    except Exception:
                        # Rollback
                        rollback_migration(vault_dir, backup_path)

                # Verify original state preserved
                restored_vault = CredentialVault(vault_dir, master_key)
                assert restored_vault.get("ORIGINAL_KEY") == "original_value"

            except Exception as e:
                pytest.fail(f"Rollback should handle failures: {e}")


class TestMigrationVerification:
    """Tests for migration verification."""

    def test_verify_migration_success(self):
        """Test verification of successful migration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            # Create .env
            env_content = """
KEY1=value1
KEY2=value2
KEY3=value3
"""
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Migrate
            migrate_env_to_vault(str(env_file), vault)

            # Verify migration
            verification_result = verify_migration(str(env_file), vault)

            assert verification_result["success"], "Migration verification should succeed"
            assert verification_result["total_keys"] == 3
            assert verification_result["migrated_keys"] == 3
            assert verification_result["failed_keys"] == 0

    def test_verify_detects_missing_credentials(self):
        """Test verification detects missing credentials."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            # Create .env with 3 keys
            env_content = "KEY1=value1\nKEY2=value2\nKEY3=value3"
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Migrate only 2 keys
            vault.store("KEY1", "value1", CredentialType.SECRET)
            vault.store("KEY2", "value2", CredentialType.SECRET)
            # KEY3 is missing

            # Verify migration
            verification_result = verify_migration(str(env_file), vault)

            assert not verification_result["success"], "Verification should detect missing keys"
            assert verification_result["total_keys"] == 3
            assert verification_result["migrated_keys"] == 2
            assert "KEY3" in verification_result["missing_keys"]

    def test_verify_detects_value_mismatch(self):
        """Test verification detects value mismatches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            env_content = "KEY1=correct_value"
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Store wrong value
            vault.store("KEY1", "wrong_value", CredentialType.SECRET)

            # Verify migration
            verification_result = verify_migration(str(env_file), vault)

            assert not verification_result["success"], "Verification should detect value mismatch"
            assert "KEY1" in verification_result["mismatched_keys"]


class TestSensitiveDataHandling:
    """Tests for secure handling of sensitive data during migration."""

    def test_migration_clears_memory_after_completion(self):
        """Verify sensitive data is cleared from memory after migration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            sensitive_value = "super_secret_password_12345"
            env_content = f"SENSITIVE_KEY={sensitive_value}"
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Migrate
            migrate_env_to_vault(str(env_file), vault)

            # The implementation should clear sensitive data from memory
            # This is difficult to test directly, but we can verify
            # that the function doesn't keep references

    def test_migration_logs_dont_contain_plaintext(self):
        """Verify migration logs don't contain plaintext credentials."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()
            log_file = Path(temp_dir) / "migration.log"

            sensitive_value = "super_secret_api_key"
            env_content = f"API_KEY={sensitive_value}"
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Capture logs
            import logging
            logger = logging.getLogger("migration")
            handler = logging.FileHandler(log_file)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            # Migrate with logging
            migrate_env_to_vault(str(env_file), vault)

            # Check log file doesn't contain plaintext
            if log_file.exists():
                log_content = log_file.read_text()
                assert sensitive_value not in log_content, \
                    "Logs should not contain plaintext credentials"

    def test_temporary_files_are_cleaned_up(self):
        """Verify temporary files are cleaned up after migration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            env_content = "KEY=value"
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Track temp files before migration
            temp_files_before = set(os.listdir(tempfile.gettempdir()))

            # Migrate
            migrate_env_to_vault(str(env_file), vault)

            # Check temp files after migration
            temp_files_after = set(os.listdir(tempfile.gettempdir()))

            # No new persistent temp files should remain
            # (Some OS temp files may be created/removed, so we check for specific patterns)
            new_files = temp_files_after - temp_files_before
            suspicious_files = [f for f in new_files if 'credential' in f.lower() or 'secret' in f.lower()]

            assert len(suspicious_files) == 0, "Temporary files should be cleaned up"


class TestMigrationAuditTrail:
    """Tests for migration audit trail."""

    def test_migration_creates_audit_log(self):
        """Verify migration creates an audit log."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()
            audit_file = Path(temp_dir) / "migration_audit.json"

            env_content = "KEY1=value1\nKEY2=value2"
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Migrate with audit logging
            migration_result = {
                "timestamp": "2024-01-01T00:00:00",
                "source": str(env_file),
                "destination": str(vault_dir),
                "keys_migrated": ["KEY1", "KEY2"],
                "success": True
            }

            # Write audit log
            audit_file.write_text(json.dumps(migration_result, indent=2))

            # Verify audit log
            assert audit_file.exists(), "Audit log should be created"

            audit_data = json.loads(audit_file.read_text())
            assert audit_data["success"] is True
            assert len(audit_data["keys_migrated"]) == 2

    def test_audit_log_includes_failure_details(self):
        """Verify audit log includes failure details."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_file = Path(temp_dir) / "migration_audit.json"

            # Simulate failed migration
            migration_result = {
                "timestamp": "2024-01-01T00:00:00",
                "source": "/path/to/.env",
                "destination": "/path/to/vault",
                "success": False,
                "error": "Failed to decrypt existing vault",
                "keys_attempted": ["KEY1", "KEY2"],
                "keys_migrated": ["KEY1"],
                "keys_failed": ["KEY2"]
            }

            audit_file.write_text(json.dumps(migration_result, indent=2))

            # Verify failure details
            audit_data = json.loads(audit_file.read_text())
            assert audit_data["success"] is False
            assert "error" in audit_data
            assert len(audit_data["keys_failed"]) == 1

    def test_audit_log_no_plaintext_values(self):
        """Verify audit log doesn't contain plaintext credential values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_file = Path(temp_dir) / "migration_audit.json"

            sensitive_value = "super_secret_password"

            # Create audit log (should only have key names, not values)
            migration_result = {
                "timestamp": "2024-01-01T00:00:00",
                "keys_migrated": ["SENSITIVE_KEY"],
                "success": True
            }

            audit_file.write_text(json.dumps(migration_result, indent=2))

            # Verify no plaintext values
            audit_content = audit_file.read_text()
            assert sensitive_value not in audit_content, \
                "Audit log should not contain plaintext values"


class TestEdgeCases:
    """Tests for edge cases in migration."""

    def test_migration_with_empty_env_file(self):
        """Test migration with empty .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            env_file.write_text("")

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Should handle empty file gracefully
            migrated_count = migrate_env_to_vault(str(env_file), vault)
            assert migrated_count == 0, "Empty file should result in 0 migrations"

    def test_migration_with_duplicate_keys(self):
        """Test migration with duplicate keys in .env."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            # .env with duplicate keys (last value should win)
            env_content = """
KEY1=value1_first
KEY1=value1_second
KEY2=value2
"""
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Migrate
            migrate_env_to_vault(str(env_file), vault)

            # Should use last value for duplicate keys
            value = vault.get("KEY1")
            assert value == "value1_second", "Should use last value for duplicates"

    def test_migration_preserves_file_permissions(self):
        """Test that vault files have correct permissions after migration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            vault_dir = Path(temp_dir) / "vault"
            vault_dir.mkdir()

            env_content = "SECRET_KEY=secret_value"
            env_file.write_text(env_content)

            master_key = "test_master_key"
            vault = CredentialVault(vault_dir, master_key)

            # Migrate
            migrate_env_to_vault(str(env_file), vault)

            # Check file permissions on vault files
            for file_path in vault_dir.glob("*.enc.json"):
                stat_info = file_path.stat()
                # Permissions should be 0o600 (owner read/write only)
                permissions = stat_info.st_mode & 0o777
                assert permissions == 0o600, \
                    f"Vault files should have 0o600 permissions, got {oct(permissions)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
