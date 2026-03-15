"""
Secure credential vault for encrypted storage and retrieval of sensitive data.

Provides a comprehensive system for storing, retrieving, rotating, and managing
encrypted credentials with metadata tracking and rotation policies.
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict

from src.secrets_manager import SecretsManager, EncryptedData, get_secrets_manager


class CredentialType(Enum):
    """Types of credentials with different rotation policies."""

    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    SECRET = "secret"
    DATABASE_URL = "database_url"
    WEBHOOK_URL = "webhook_url"


@dataclass
class CredentialMetadata:
    """Metadata for tracking credential lifecycle."""

    name: str
    credential_type: CredentialType
    created_at: datetime
    last_accessed: Optional[datetime] = None
    last_rotated: Optional[datetime] = None
    rotation_days: Optional[int] = None
    access_count: int = 0
    tags: List[str] = None

    def __post_init__(self) -> None:
        """Initialize tags if None."""
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "credential_type": self.credential_type.value,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "last_rotated": self.last_rotated.isoformat() if self.last_rotated else None,
            "rotation_days": self.rotation_days,
            "access_count": self.access_count,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CredentialMetadata":
        """
        Create metadata from dictionary.

        Args:
            data: Dictionary with metadata fields

        Returns:
            CredentialMetadata instance
        """
        return cls(
            name=data["name"],
            credential_type=CredentialType(data["credential_type"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            last_rotated=datetime.fromisoformat(data["last_rotated"]) if data.get("last_rotated") else None,
            rotation_days=data.get("rotation_days"),
            access_count=data.get("access_count", 0),
            tags=data.get("tags", [])
        )

    def needs_rotation(self) -> bool:
        """
        Check if credential needs rotation based on policy.

        Returns:
            True if rotation is needed
        """
        if not self.rotation_days:
            return False

        last_change = self.last_rotated or self.created_at
        age_days = (datetime.utcnow() - last_change).days

        return age_days >= self.rotation_days


class CredentialVault:
    """
    Secure encrypted credential storage vault.

    Manages encrypted credentials with metadata tracking, rotation policies,
    and access logging.

    Example:
        ```python
        vault = CredentialVault()

        # Store credential
        vault.set_credential(
            name="API_KEY",
            value="secret-value",
            credential_type=CredentialType.API_KEY,
            rotation_days=180
        )

        # Retrieve credential
        value = vault.get_credential("API_KEY")
        ```
    """

    def __init__(
        self,
        vault_dir: Optional[Path] = None,
        secrets_manager: Optional[SecretsManager] = None
    ):
        """
        Initialize credential vault.

        Args:
            vault_dir: Directory for storing encrypted credentials.
                      Defaults to data/vault/
            secrets_manager: SecretsManager instance. If None, creates new instance.

        Raises:
            IOError: If vault directory cannot be created
        """
        self.vault_dir = vault_dir or Path("data/vault")
        self.vault_dir.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions
        os.chmod(self.vault_dir, 0o700)

        self.secrets_manager = secrets_manager or get_secrets_manager()
        self._metadata: Dict[str, CredentialMetadata] = {}
        self._load_metadata()

    def _get_credential_path(self, name: str) -> Path:
        """
        Get file path for credential.

        Args:
            name: Credential name

        Returns:
            Path to credential file
        """
        return self.vault_dir / f"{name}.enc.json"

    def _get_metadata_path(self) -> Path:
        """
        Get path to metadata file.

        Returns:
            Path to metadata file
        """
        return self.vault_dir / "metadata.json"

    def _load_metadata(self) -> None:
        """Load metadata from disk."""
        metadata_path = self._get_metadata_path()

        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._metadata = {
                    name: CredentialMetadata.from_dict(meta_data)
                    for name, meta_data in data.items()
                }
            except Exception as e:
                # If metadata is corrupted, start fresh
                self._metadata = {}

    def _save_metadata(self) -> None:
        """Save metadata to disk."""
        metadata_path = self._get_metadata_path()

        try:
            data = {
                name: meta.to_dict()
                for name, meta in self._metadata.items()
            }

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            os.chmod(metadata_path, 0o600)

        except Exception as e:
            raise IOError(f"Failed to save metadata: {e}")

    def set_credential(
        self,
        name: str,
        value: str,
        credential_type: CredentialType,
        rotation_days: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Store encrypted credential in vault.

        Args:
            name: Credential identifier (e.g., "DISCORD_BOT_TOKEN")
            value: Credential value to encrypt and store
            credential_type: Type of credential
            rotation_days: Days until rotation needed (None = no rotation)
            tags: Optional tags for organization

        Raises:
            IOError: If file operations fail
        """
        try:
            # Encrypt credential
            encrypted = self.secrets_manager.encrypt(value)

            # Save to file
            credential_path = self._get_credential_path(name)
            with open(credential_path, 'w', encoding='utf-8') as f:
                json.dump(encrypted.to_dict(), f, indent=2)

            os.chmod(credential_path, 0o600)

            # Update metadata
            if name in self._metadata:
                # Update existing
                meta = self._metadata[name]
                meta.last_rotated = datetime.utcnow()
            else:
                # Create new
                meta = CredentialMetadata(
                    name=name,
                    credential_type=credential_type,
                    created_at=datetime.utcnow(),
                    rotation_days=rotation_days,
                    tags=tags or []
                )
                self._metadata[name] = meta

            self._save_metadata()

        except Exception as e:
            raise IOError(f"Failed to store credential '{name}': {e}")

    def get_credential(
        self,
        name: str,
        env_var_override: bool = True
    ) -> Optional[str]:
        """
        Retrieve credential from vault or environment.

        Args:
            name: Credential identifier
            env_var_override: If True, check environment variable first

        Returns:
            Decrypted credential value or None if not found

        Raises:
            ValueError: If decryption fails
        """
        # Check environment variable first if enabled
        if env_var_override:
            env_value = os.getenv(name)
            if env_value:
                return env_value

        # Load from vault
        credential_path = self._get_credential_path(name)

        if not credential_path.exists():
            return None

        try:
            with open(credential_path, 'r', encoding='utf-8') as f:
                encrypted_data = json.load(f)

            encrypted = EncryptedData.from_dict(encrypted_data)
            value = self.secrets_manager.decrypt(encrypted)

            # Update access metadata
            if name in self._metadata:
                meta = self._metadata[name]
                meta.last_accessed = datetime.utcnow()
                meta.access_count += 1
                self._save_metadata()

            return value

        except Exception as e:
            raise ValueError(f"Failed to retrieve credential '{name}': {e}")

    def delete_credential(self, name: str) -> bool:
        """
        Delete credential from vault.

        Args:
            name: Credential identifier

        Returns:
            True if deleted, False if not found
        """
        credential_path = self._get_credential_path(name)

        if not credential_path.exists():
            return False

        try:
            credential_path.unlink()

            if name in self._metadata:
                del self._metadata[name]
                self._save_metadata()

            return True

        except Exception:
            return False

    def rotate_credential(self, name: str, new_value: str) -> None:
        """
        Rotate credential with new value.

        Args:
            name: Credential identifier
            new_value: New credential value

        Raises:
            ValueError: If credential doesn't exist
            IOError: If rotation fails
        """
        if name not in self._metadata:
            raise ValueError(f"Credential '{name}' not found")

        meta = self._metadata[name]

        self.set_credential(
            name=name,
            value=new_value,
            credential_type=meta.credential_type,
            rotation_days=meta.rotation_days,
            tags=meta.tags
        )

    def list_credentials(
        self,
        credential_type: Optional[CredentialType] = None
    ) -> List[str]:
        """
        List credential names in vault.

        Args:
            credential_type: Optional filter by credential type

        Returns:
            List of credential names
        """
        if credential_type:
            return [
                name for name, meta in self._metadata.items()
                if meta.credential_type == credential_type
            ]

        return list(self._metadata.keys())

    def get_metadata(self, name: str) -> Optional[CredentialMetadata]:
        """
        Get metadata for credential.

        Args:
            name: Credential identifier

        Returns:
            CredentialMetadata or None if not found
        """
        return self._metadata.get(name)

    def credentials_needing_rotation(self) -> List[str]:
        """
        Get list of credentials that need rotation.

        Returns:
            List of credential names needing rotation
        """
        return [
            name for name, meta in self._metadata.items()
            if meta.needs_rotation()
        ]

    def export_for_env(self) -> Dict[str, str]:
        """
        Export credential structure (without values) for environment setup.

        Returns:
            Dictionary mapping credential names to types
        """
        return {
            meta.name: meta.credential_type.value
            for meta in self._metadata.values()
        }


# Global vault instance
_vault_instance: Optional[CredentialVault] = None


def get_credential_vault(
    vault_dir: Optional[Path] = None,
    secrets_manager: Optional[SecretsManager] = None
) -> CredentialVault:
    """
    Get or create singleton credential vault instance.

    Args:
        vault_dir: Optional vault directory
        secrets_manager: Optional secrets manager

    Returns:
        CredentialVault instance
    """
    global _vault_instance

    if _vault_instance is None:
        _vault_instance = CredentialVault(
            vault_dir=vault_dir,
            secrets_manager=secrets_manager
        )

    return _vault_instance
