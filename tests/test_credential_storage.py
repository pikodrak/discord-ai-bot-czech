"""
Tests for secure credential storage system.
"""

import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from src.credential_vault import (
    CredentialVault,
    CredentialType,
    CredentialMetadata,
    get_credential_vault
)
from src.secrets_manager import SecretsManager, generate_master_key
from src.credential_loader import (
    CredentialLoader,
    CredentialConfig,
    check_credential_health
)


@pytest.fixture
def temp_vault_dir():
    """Create temporary vault directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def secrets_manager():
    """Create secrets manager with temporary key."""
    key = generate_master_key()
    return SecretsManager(master_key=key)


@pytest.fixture
def vault(temp_vault_dir, secrets_manager):
    """Create credential vault instance."""
    return CredentialVault(
        vault_dir=temp_vault_dir,
        secrets_manager=secrets_manager
    )


class TestSecretsManager:
    """Test encryption and decryption functionality."""

    def test_generate_key(self):
        """Test master key generation."""
        key = generate_master_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_encrypt_decrypt(self, secrets_manager):
        """Test basic encryption and decryption."""
        plaintext = "my-secret-token"
        encrypted = secrets_manager.encrypt(plaintext)

        assert encrypted.ciphertext != plaintext
        assert encrypted.nonce is not None
        assert encrypted.salt is not None

        decrypted = secrets_manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_dict(self, secrets_manager):
        """Test dictionary encryption."""
        data = {
            "api_key": "secret-key-123",
            "password": "secure-password",
            "number": 42,
            "nested": {
                "token": "nested-token"
            }
        }

        encrypted = secrets_manager.encrypt_dict(data)
        decrypted = secrets_manager.decrypt_dict(encrypted)

        assert decrypted["api_key"] == "secret-key-123"
        assert decrypted["password"] == "secure-password"
        assert decrypted["number"] == 42
        assert decrypted["nested"]["token"] == "nested-token"

    def test_decrypt_wrong_key(self):
        """Test decryption with wrong key fails."""
        manager1 = SecretsManager(master_key=generate_master_key())
        manager2 = SecretsManager(master_key=generate_master_key())

        encrypted = manager1.encrypt("secret")

        with pytest.raises(ValueError, match="Failed to decrypt"):
            manager2.decrypt(encrypted)

    def test_save_load_encrypted_config(self, secrets_manager, temp_vault_dir):
        """Test saving and loading encrypted config files."""
        config = {
            "discord_token": "token-123",
            "api_key": "key-456"
        }

        config_file = temp_vault_dir / "config.enc.json"

        secrets_manager.save_encrypted_config(config, config_file)
        assert config_file.exists()

        loaded = secrets_manager.load_encrypted_config(config_file)
        assert loaded == config


class TestCredentialVault:
    """Test credential vault functionality."""

    def test_set_get_credential(self, vault):
        """Test storing and retrieving credentials."""
        vault.set_credential(
            name="TEST_TOKEN",
            value="secret-value-123",
            credential_type=CredentialType.TOKEN
        )

        value = vault.get_credential("TEST_TOKEN", env_var_override=False)
        assert value == "secret-value-123"

    def test_credential_metadata(self, vault):
        """Test credential metadata tracking."""
        vault.set_credential(
            name="TEST_API_KEY",
            value="key-123",
            credential_type=CredentialType.API_KEY,
            rotation_days=90,
            tags=["production", "critical"]
        )

        meta = vault.get_metadata("TEST_API_KEY")
        assert meta is not None
        assert meta.name == "TEST_API_KEY"
        assert meta.credential_type == CredentialType.API_KEY
        assert meta.rotation_days == 90
        assert "production" in meta.tags
        assert meta.access_count == 0

    def test_credential_access_tracking(self, vault):
        """Test access count tracking."""
        vault.set_credential("TEST", "value", CredentialType.SECRET)

        # Access multiple times
        for _ in range(3):
            vault.get_credential("TEST", env_var_override=False)

        meta = vault.get_metadata("TEST")
        assert meta.access_count == 3
        assert meta.last_accessed is not None

    def test_delete_credential(self, vault):
        """Test credential deletion."""
        vault.set_credential("TO_DELETE", "value", CredentialType.SECRET)
        assert vault.get_credential("TO_DELETE", env_var_override=False) == "value"

        deleted = vault.delete_credential("TO_DELETE")
        assert deleted is True

        value = vault.get_credential("TO_DELETE", env_var_override=False)
        assert value is None

    def test_list_credentials(self, vault):
        """Test listing credentials."""
        vault.set_credential("TOKEN1", "val1", CredentialType.TOKEN)
        vault.set_credential("TOKEN2", "val2", CredentialType.TOKEN)
        vault.set_credential("KEY1", "val3", CredentialType.API_KEY)

        all_creds = vault.list_credentials()
        assert len(all_creds) == 3
        assert "TOKEN1" in all_creds
        assert "TOKEN2" in all_creds
        assert "KEY1" in all_creds

        # Filter by type
        tokens = vault.list_credentials(CredentialType.TOKEN)
        assert len(tokens) == 2
        assert "TOKEN1" in tokens
        assert "TOKEN2" in tokens

    def test_credential_rotation(self, vault):
        """Test credential rotation."""
        vault.set_credential(
            "ROTATABLE",
            "old-value",
            CredentialType.PASSWORD,
            rotation_days=90
        )

        vault.rotate_credential("ROTATABLE", "new-value")

        value = vault.get_credential("ROTATABLE", env_var_override=False)
        assert value == "new-value"

        meta = vault.get_metadata("ROTATABLE")
        assert meta.last_rotated is not None

    def test_rotation_needed(self, vault):
        """Test rotation detection."""
        vault.set_credential(
            "OLD_CRED",
            "value",
            CredentialType.PASSWORD,
            rotation_days=1
        )

        meta = vault.get_metadata("OLD_CRED")

        # Simulate old credential
        meta.last_rotated = datetime.utcnow() - timedelta(days=2)
        vault._metadata["OLD_CRED"] = meta
        vault._save_metadata()

        needs_rotation = vault.credentials_needing_rotation()
        assert "OLD_CRED" in needs_rotation

    def test_env_var_override(self, vault):
        """Test environment variable priority."""
        os.environ["ENV_TEST"] = "from-environment"

        vault.set_credential(
            "ENV_TEST",
            "from-vault",
            CredentialType.SECRET
        )

        # With override (default)
        value = vault.get_credential("ENV_TEST", env_var_override=True)
        assert value == "from-environment"

        # Without override
        value = vault.get_credential("ENV_TEST", env_var_override=False)
        assert value == "from-vault"

        del os.environ["ENV_TEST"]

    def test_export_for_env(self, vault):
        """Test exporting credential structure."""
        vault.set_credential("TEST1", "val1", CredentialType.API_KEY)
        vault.set_credential("TEST2", "val2", CredentialType.PASSWORD)

        export = vault.export_for_env()
        assert "TEST1" in export
        assert "TEST2" in export
        assert "api_key" in export
        assert "password" in export
        # Values should not be in export
        assert "val1" not in export
        assert "val2" not in export


class TestCredentialLoader:
    """Test credential loading functionality."""

    def test_load_credential_from_env(self):
        """Test loading from environment variable."""
        os.environ["TEST_LOAD"] = "env-value"

        loader = CredentialLoader(strict_mode=False)
        config = CredentialConfig(
            name="test",
            env_var="TEST_LOAD",
            credential_type=CredentialType.SECRET,
            required=True
        )

        value = loader.load_credential(config)
        assert value == "env-value"

        del os.environ["TEST_LOAD"]

    def test_load_credential_from_vault(self, vault):
        """Test loading from vault."""
        vault.set_credential("VAULT_TEST", "vault-value", CredentialType.TOKEN)

        loader = CredentialLoader(vault=vault, strict_mode=False)
        config = CredentialConfig(
            name="test",
            env_var="VAULT_TEST",
            credential_type=CredentialType.TOKEN,
            required=True
        )

        value = loader.load_credential(config)
        assert value == "vault-value"

    def test_load_credential_default(self):
        """Test loading with default value."""
        loader = CredentialLoader(strict_mode=False)
        config = CredentialConfig(
            name="test",
            env_var="NONEXISTENT",
            credential_type=CredentialType.SECRET,
            required=False,
            default="default-value"
        )

        value = loader.load_credential(config)
        assert value == "default-value"

    def test_strict_mode_required(self):
        """Test strict mode enforces required credentials."""
        loader = CredentialLoader(strict_mode=True)
        config = CredentialConfig(
            name="test",
            env_var="MISSING_REQUIRED",
            credential_type=CredentialType.SECRET,
            required=True
        )

        with pytest.raises(ValueError, match="Required credential"):
            loader.load_credential(config)

    def test_load_multiple_credentials(self, vault):
        """Test loading multiple credentials."""
        vault.set_credential("CRED1", "val1", CredentialType.API_KEY)
        vault.set_credential("CRED2", "val2", CredentialType.TOKEN)

        loader = CredentialLoader(vault=vault, strict_mode=False)
        configs = [
            CredentialConfig("c1", "CRED1", CredentialType.API_KEY, required=True),
            CredentialConfig("c2", "CRED2", CredentialType.TOKEN, required=True),
            CredentialConfig("c3", "MISSING", CredentialType.SECRET, required=False)
        ]

        results = loader.load_credentials(configs)

        assert results["c1"] == "val1"
        assert results["c2"] == "val2"
        assert results["c3"] is None

    def test_validate_credentials(self, vault):
        """Test credential validation."""
        vault.set_credential("VALID1", "val1", CredentialType.SECRET)

        loader = CredentialLoader(vault=vault, strict_mode=False)
        configs = [
            CredentialConfig("v1", "VALID1", CredentialType.SECRET, required=True),
            CredentialConfig("v2", "MISSING", CredentialType.SECRET, required=False)
        ]

        loader.load_credentials(configs)
        assert loader.validate_credentials() is True

        # Test with missing required credential
        loader2 = CredentialLoader(vault=vault, strict_mode=False)
        configs2 = [
            CredentialConfig("v1", "MISSING", CredentialType.SECRET, required=True)
        ]

        loader2.load_credentials(configs2)
        assert loader2.validate_credentials() is False


class TestCredentialHealth:
    """Test credential health checking."""

    def test_health_check(self):
        """Test credential health check."""
        health = check_credential_health()

        assert "status" in health
        assert "total_credentials" in health
        assert "loaded_credentials" in health
        assert "missing_credentials" in health
        assert "coverage_percent" in health

    def test_health_with_vault(self, vault):
        """Test health check with populated vault."""
        vault.set_credential("DISCORD_BOT_TOKEN", "token", CredentialType.TOKEN)
        vault.set_credential("ANTHROPIC_API_KEY", "key", CredentialType.API_KEY)

        health = check_credential_health()

        assert health["status"] in ["healthy", "degraded"]
        assert health["total_credentials"] > 0
        assert isinstance(health["loaded_credentials"], int)


class TestCredentialMetadata:
    """Test credential metadata functionality."""

    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        meta = CredentialMetadata(
            name="TEST",
            credential_type=CredentialType.API_KEY,
            created_at=datetime.utcnow(),
            rotation_days=90,
            tags=["prod"]
        )

        data = meta.to_dict()
        assert data["name"] == "TEST"
        assert data["credential_type"] == "api_key"
        assert "created_at" in data
        assert data["rotation_days"] == 90

    def test_metadata_from_dict(self):
        """Test metadata deserialization."""
        data = {
            "name": "TEST",
            "credential_type": "api_key",
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": None,
            "last_rotated": None,
            "rotation_days": 90,
            "access_count": 0,
            "tags": ["prod"]
        }

        meta = CredentialMetadata.from_dict(data)
        assert meta.name == "TEST"
        assert meta.credential_type == CredentialType.API_KEY
        assert meta.rotation_days == 90

    def test_needs_rotation(self):
        """Test rotation detection logic."""
        # No rotation policy
        meta = CredentialMetadata(
            name="TEST",
            credential_type=CredentialType.SECRET,
            created_at=datetime.utcnow(),
            rotation_days=None
        )
        assert meta.needs_rotation() is False

        # Fresh credential
        meta = CredentialMetadata(
            name="TEST",
            credential_type=CredentialType.PASSWORD,
            created_at=datetime.utcnow(),
            rotation_days=90
        )
        assert meta.needs_rotation() is False

        # Old credential
        meta = CredentialMetadata(
            name="TEST",
            credential_type=CredentialType.PASSWORD,
            created_at=datetime.utcnow() - timedelta(days=100),
            rotation_days=90
        )
        assert meta.needs_rotation() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
