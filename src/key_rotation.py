"""
Zero-downtime key rotation system with versioned credentials and multiple rotation strategies.

Provides comprehensive credential rotation with support for immediate, gradual,
and versioned rotation strategies for zero-downtime credential updates.
"""

import json
import uuid
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from src.credential_vault import get_credential_vault, CredentialVault
from src.rotation_history import (
    get_rotation_history,
    RotationHistory,
    RotationReason,
    RotationStatus
)


class RotationStrategy(Enum):
    """Strategy for rotating credentials."""

    IMMEDIATE = "immediate"  # Old credential invalidated immediately
    GRADUAL = "gradual"      # Both credentials valid during transition
    VERSIONED = "versioned"  # Multiple versions tracked


@dataclass
class RotationConfig:
    """Configuration for credential rotation behavior."""

    strategy: RotationStrategy = RotationStrategy.GRADUAL
    transition_period_hours: int = 24
    max_active_versions: int = 2
    auto_cleanup_expired: bool = True
    validation_callback: Optional[Callable[[str], bool]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation (excludes callbacks)
        """
        return {
            "strategy": self.strategy.value,
            "transition_period_hours": self.transition_period_hours,
            "max_active_versions": self.max_active_versions,
            "auto_cleanup_expired": self.auto_cleanup_expired
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RotationConfig":
        """
        Create from dictionary.

        Args:
            data: Dictionary with config data

        Returns:
            RotationConfig instance
        """
        return cls(
            strategy=RotationStrategy(data["strategy"]),
            transition_period_hours=data.get("transition_period_hours", 24),
            max_active_versions=data.get("max_active_versions", 2),
            auto_cleanup_expired=data.get("auto_cleanup_expired", True)
        )


@dataclass
class CredentialVersion:
    """Single version of a credential."""

    version_id: str
    credential_name: str
    value_hash: str  # Hash of value for comparison (not the actual value)
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_primary: bool = False
    usage_count: int = 0
    deprecated: bool = False

    def is_expired(self) -> bool:
        """
        Check if version has expired.

        Returns:
            True if expired
        """
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "version_id": self.version_id,
            "credential_name": self.credential_name,
            "value_hash": self.value_hash,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_primary": self.is_primary,
            "usage_count": self.usage_count,
            "deprecated": self.deprecated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CredentialVersion":
        """
        Create from dictionary.

        Args:
            data: Dictionary with version data

        Returns:
            CredentialVersion instance
        """
        return cls(
            version_id=data["version_id"],
            credential_name=data["credential_name"],
            value_hash=data["value_hash"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            is_primary=data.get("is_primary", False),
            usage_count=data.get("usage_count", 0),
            deprecated=data.get("deprecated", False)
        )


class KeyRotationManager:
    """
    Manages credential rotation with versioning and multiple strategies.

    Provides zero-downtime credential rotation with support for gradual
    transitions, version management, and automatic cleanup.

    Example:
        ```python
        manager = KeyRotationManager()

        # Configure rotation
        config = RotationConfig(
            strategy=RotationStrategy.GRADUAL,
            transition_period_hours=24
        )
        manager.set_rotation_config("API_KEY", config)

        # Rotate credential
        rotation_id = manager.rotate(
            credential_name="API_KEY",
            new_value="new_value",
            reason=RotationReason.SCHEDULED
        )
        ```
    """

    def __init__(
        self,
        vault: Optional[CredentialVault] = None,
        history: Optional[RotationHistory] = None,
        rotation_dir: Optional[Path] = None
    ):
        """
        Initialize key rotation manager.

        Args:
            vault: CredentialVault instance
            history: RotationHistory instance
            rotation_dir: Directory for storing rotation data
        """
        self.vault = vault or get_credential_vault()
        self.history = history or get_rotation_history()
        self.rotation_dir = rotation_dir or Path("data/rotation")
        self.rotation_dir.mkdir(parents=True, exist_ok=True)

        self._configs: Dict[str, RotationConfig] = {}
        self._versions: Dict[str, List[CredentialVersion]] = {}

        self._load_rotation_data()

    def _get_config_path(self) -> Path:
        """Get path to rotation configs file."""
        return self.rotation_dir / "rotation_configs.json"

    def _get_versions_path(self) -> Path:
        """Get path to versions file."""
        return self.rotation_dir / "credential_versions.json"

    def _load_rotation_data(self) -> None:
        """Load rotation configs and versions from disk."""
        # Load configs
        config_path = self._get_config_path()
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._configs = {
                    name: RotationConfig.from_dict(config_data)
                    for name, config_data in data.items()
                }
            except Exception:
                self._configs = {}

        # Load versions
        versions_path = self._get_versions_path()
        if versions_path.exists():
            try:
                with open(versions_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._versions = {
                    cred_name: [CredentialVersion.from_dict(v) for v in versions]
                    for cred_name, versions in data.items()
                }
            except Exception:
                self._versions = {}

    def _save_rotation_data(self) -> None:
        """Save rotation configs and versions to disk."""
        # Save configs
        config_path = self._get_config_path()
        try:
            data = {
                name: config.to_dict()
                for name, config in self._configs.items()
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise IOError(f"Failed to save rotation configs: {e}")

        # Save versions
        versions_path = self._get_versions_path()
        try:
            data = {
                cred_name: [v.to_dict() for v in versions]
                for cred_name, versions in self._versions.items()
            }
            with open(versions_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise IOError(f"Failed to save credential versions: {e}")

    def _hash_value(self, value: str) -> str:
        """
        Create hash of credential value.

        Args:
            value: Credential value

        Returns:
            Hash string
        """
        import hashlib
        return hashlib.sha256(value.encode()).hexdigest()

    def set_rotation_config(
        self,
        credential_name: str,
        config: RotationConfig
    ) -> None:
        """
        Set rotation configuration for a credential.

        Args:
            credential_name: Name of credential
            config: Rotation configuration
        """
        self._configs[credential_name] = config
        self._save_rotation_data()

    def get_rotation_config(
        self,
        credential_name: str
    ) -> Optional[RotationConfig]:
        """
        Get rotation configuration for a credential.

        Args:
            credential_name: Name of credential

        Returns:
            RotationConfig or None if not configured
        """
        return self._configs.get(credential_name)

    def rotate(
        self,
        credential_name: str,
        new_value: str,
        reason: RotationReason,
        initiated_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Rotate a credential to a new value.

        Args:
            credential_name: Name of credential to rotate
            new_value: New credential value
            reason: Reason for rotation
            initiated_by: User or system initiating rotation
            metadata: Additional metadata

        Returns:
            Rotation event ID

        Raises:
            ValueError: If validation fails or rotation fails
        """
        # Get or create default config
        config = self._configs.get(credential_name, RotationConfig())

        # Validate new value if callback provided
        if config.validation_callback:
            if not config.validation_callback(new_value):
                # Record failed rotation
                rotation_id = self.history.record_rotation(
                    credential_name=credential_name,
                    reason=reason,
                    initiated_by=initiated_by,
                    metadata=metadata
                )
                self.history.update_status(
                    rotation_id,
                    RotationStatus.FAILED,
                    error_message="Validation callback failed"
                )
                raise ValueError("New credential value failed validation")

        # Get current versions
        current_versions = self._versions.get(credential_name, [])
        old_version = next((v for v in current_versions if v.is_primary), None)

        # Create new version
        new_version_id = str(uuid.uuid4())
        new_version = CredentialVersion(
            version_id=new_version_id,
            credential_name=credential_name,
            value_hash=self._hash_value(new_value),
            created_at=datetime.utcnow(),
            is_primary=True
        )

        # Record rotation start
        rotation_id = self.history.record_rotation(
            credential_name=credential_name,
            reason=reason,
            initiated_by=initiated_by,
            metadata=metadata,
            old_version_id=old_version.version_id if old_version else None,
            new_version_id=new_version_id
        )

        try:
            # Update status to in progress
            self.history.update_status(rotation_id, RotationStatus.IN_PROGRESS)

            # Store new credential value in vault
            metadata_obj = self.vault.get_metadata(credential_name)
            if metadata_obj:
                self.vault.set_credential(
                    name=credential_name,
                    value=new_value,
                    credential_type=metadata_obj.credential_type,
                    rotation_days=metadata_obj.rotation_days,
                    tags=metadata_obj.tags
                )
            else:
                # Credential doesn't exist in vault yet
                from src.credential_vault import CredentialType
                self.vault.set_credential(
                    name=credential_name,
                    value=new_value,
                    credential_type=CredentialType.SECRET
                )

            # Handle rotation strategy
            if config.strategy == RotationStrategy.IMMEDIATE:
                # Remove all old versions immediately
                current_versions = [new_version]

            elif config.strategy == RotationStrategy.GRADUAL:
                # Mark old primary as non-primary with expiry
                if old_version:
                    old_version.is_primary = False
                    old_version.expires_at = datetime.utcnow() + timedelta(
                        hours=config.transition_period_hours
                    )
                    current_versions = [v for v in current_versions if v.version_id != old_version.version_id]
                    current_versions.append(old_version)

                current_versions.append(new_version)

            elif config.strategy == RotationStrategy.VERSIONED:
                # Mark old primary as non-primary
                if old_version:
                    old_version.is_primary = False
                    current_versions = [v for v in current_versions if v.version_id != old_version.version_id]
                    current_versions.append(old_version)

                current_versions.append(new_version)

                # Enforce max_active_versions
                if len(current_versions) > config.max_active_versions:
                    # Sort by created_at, keep newest
                    current_versions.sort(key=lambda v: v.created_at, reverse=True)
                    current_versions = current_versions[:config.max_active_versions]

            # Clean up expired versions if enabled
            if config.auto_cleanup_expired:
                current_versions = [v for v in current_versions if not v.is_expired()]

            # Update versions
            self._versions[credential_name] = current_versions
            self._save_rotation_data()

            # Mark rotation as completed
            self.history.update_status(rotation_id, RotationStatus.COMPLETED)

            return rotation_id

        except Exception as e:
            # Mark rotation as failed
            self.history.update_status(
                rotation_id,
                RotationStatus.FAILED,
                error_message=str(e)
            )
            raise ValueError(f"Rotation failed: {e}")

    def get_credential(self, credential_name: str) -> Optional[str]:
        """
        Get current (primary) credential value.

        Args:
            credential_name: Name of credential

        Returns:
            Credential value or None if not found
        """
        # Get from vault (which has the actual encrypted value)
        value = self.vault.get_credential(credential_name)

        # Update usage count for primary version
        versions = self._versions.get(credential_name, [])
        primary = next((v for v in versions if v.is_primary), None)
        if primary:
            primary.usage_count += 1
            self._save_rotation_data()

        return value

    def get_active_versions(self, credential_name: str) -> List[CredentialVersion]:
        """
        Get all active (non-expired, non-deprecated) versions.

        Args:
            credential_name: Name of credential

        Returns:
            List of active credential versions
        """
        versions = self._versions.get(credential_name, [])

        # Filter out expired and deprecated
        active = [
            v for v in versions
            if not v.is_expired() and not v.deprecated
        ]

        return active

    def deprecate_version(
        self,
        credential_name: str,
        version_id: str,
        graceful_period_hours: Optional[int] = None
    ) -> bool:
        """
        Deprecate a credential version.

        Args:
            credential_name: Name of credential
            version_id: Version ID to deprecate
            graceful_period_hours: Hours until version expires (if None, expires immediately)

        Returns:
            True if deprecated, False if version not found
        """
        versions = self._versions.get(credential_name, [])
        version = next((v for v in versions if v.version_id == version_id), None)

        if not version:
            return False

        version.deprecated = True

        if graceful_period_hours is not None:
            version.expires_at = datetime.utcnow() + timedelta(hours=graceful_period_hours)
        else:
            version.expires_at = datetime.utcnow()

        self._save_rotation_data()
        return True

    def get_rotation_status(self, credential_name: str) -> Dict[str, Any]:
        """
        Get rotation status for a credential.

        Args:
            credential_name: Name of credential

        Returns:
            Dictionary with rotation status information
        """
        versions = self._versions.get(credential_name, [])
        primary = next((v for v in versions if v.is_primary), None)
        active_versions = self.get_active_versions(credential_name)

        return {
            "credential_name": credential_name,
            "primary_version_id": primary.version_id if primary else None,
            "active_versions": len(active_versions),
            "total_versions": len(versions),
            "has_expired_versions": any(v.is_expired() for v in versions),
            "has_deprecated_versions": any(v.deprecated for v in versions)
        }


# Global manager instance
_manager_instance: Optional[KeyRotationManager] = None


def get_rotation_manager(
    vault: Optional[CredentialVault] = None,
    history: Optional[RotationHistory] = None,
    rotation_dir: Optional[Path] = None
) -> KeyRotationManager:
    """
    Get or create singleton key rotation manager instance.

    Args:
        vault: Optional credential vault
        history: Optional rotation history
        rotation_dir: Optional rotation directory

    Returns:
        KeyRotationManager instance
    """
    global _manager_instance

    if _manager_instance is None:
        _manager_instance = KeyRotationManager(
            vault=vault,
            history=history,
            rotation_dir=rotation_dir
        )

    return _manager_instance
