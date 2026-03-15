"""
Comprehensive test suite for key rotation system.

Tests rotation history, zero-downtime rotation, and automated scheduling.
"""

import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import time

from src.rotation_history import (
    RotationHistory,
    RotationEvent,
    RotationStatus,
    RotationReason
)
from src.key_rotation import (
    KeyRotationManager,
    RotationConfig,
    RotationStrategy,
    CredentialVersion
)
from src.rotation_scheduler import (
    RotationScheduler,
    RotationPolicy,
    RotationFrequency
)
from src.credential_vault import CredentialVault, CredentialType
from src.secrets_manager import SecretsManager


class TestRotationHistory(unittest.TestCase):
    """Test rotation history tracking."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.history = RotationHistory(history_dir=self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_add_event(self):
        """Test adding rotation event."""
        event = RotationEvent(
            credential_name="TEST_KEY",
            rotation_id="rot_123",
            status=RotationStatus.COMPLETED,
            reason=RotationReason.MANUAL,
            initiated_at=datetime.utcnow()
        )

        self.history.add_event(event)

        # Verify event was saved
        history = self.history.get_history("TEST_KEY")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].rotation_id, "rot_123")

    def test_update_event(self):
        """Test updating rotation event."""
        event = RotationEvent(
            credential_name="TEST_KEY",
            rotation_id="rot_123",
            status=RotationStatus.INITIATED,
            reason=RotationReason.MANUAL,
            initiated_at=datetime.utcnow()
        )

        self.history.add_event(event)

        # Update status
        success = self.history.update_event(
            "TEST_KEY",
            "rot_123",
            status=RotationStatus.COMPLETED,
            completed_at=datetime.utcnow()
        )

        self.assertTrue(success)

        # Verify update
        history = self.history.get_history("TEST_KEY")
        self.assertEqual(history[0].status, RotationStatus.COMPLETED)
        self.assertIsNotNone(history[0].completed_at)

    def test_get_history_with_filters(self):
        """Test getting history with filters."""
        # Add multiple events
        for i in range(5):
            status = RotationStatus.COMPLETED if i % 2 == 0 else RotationStatus.FAILED
            event = RotationEvent(
                credential_name="TEST_KEY",
                rotation_id=f"rot_{i}",
                status=status,
                reason=RotationReason.SCHEDULED,
                initiated_at=datetime.utcnow() - timedelta(days=i)
            )
            self.history.add_event(event)

        # Test status filter
        completed = self.history.get_history(
            "TEST_KEY",
            status_filter=RotationStatus.COMPLETED
        )
        self.assertEqual(len(completed), 3)

        # Test limit
        limited = self.history.get_history("TEST_KEY", limit=2)
        self.assertEqual(len(limited), 2)

    def test_get_failed_rotations(self):
        """Test getting failed rotations."""
        event = RotationEvent(
            credential_name="TEST_KEY",
            rotation_id="rot_fail",
            status=RotationStatus.FAILED,
            reason=RotationReason.MANUAL,
            initiated_at=datetime.utcnow(),
            error_message="Test error"
        )

        self.history.add_event(event)

        failed = self.history.get_failed_rotations("TEST_KEY")
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].error_message, "Test error")

    def test_get_statistics(self):
        """Test rotation statistics."""
        # Add successful rotation
        event1 = RotationEvent(
            credential_name="TEST_KEY",
            rotation_id="rot_1",
            status=RotationStatus.COMPLETED,
            reason=RotationReason.SCHEDULED,
            initiated_at=datetime.utcnow() - timedelta(seconds=10),
            completed_at=datetime.utcnow()
        )
        self.history.add_event(event1)

        # Add failed rotation
        event2 = RotationEvent(
            credential_name="TEST_KEY",
            rotation_id="rot_2",
            status=RotationStatus.FAILED,
            reason=RotationReason.SCHEDULED,
            initiated_at=datetime.utcnow()
        )
        self.history.add_event(event2)

        stats = self.history.get_statistics("TEST_KEY")

        self.assertEqual(stats["total_rotations"], 2)
        self.assertEqual(stats["successful_rotations"], 1)
        self.assertEqual(stats["failed_rotations"], 1)
        self.assertIsNotNone(stats["average_duration_seconds"])

    def test_cleanup_old_events(self):
        """Test cleaning up old events."""
        # Add 10 events
        for i in range(10):
            event = RotationEvent(
                credential_name="TEST_KEY",
                rotation_id=f"rot_{i}",
                status=RotationStatus.COMPLETED,
                reason=RotationReason.SCHEDULED,
                initiated_at=datetime.utcnow() - timedelta(days=i)
            )
            self.history.add_event(event)

        # Keep only 5 most recent
        removed = self.history.cleanup_old_events("TEST_KEY", keep_count=5)

        self.assertEqual(removed, 5)

        # Verify only 5 remain
        history = self.history.get_history("TEST_KEY")
        self.assertEqual(len(history), 5)


class TestKeyRotation(unittest.TestCase):
    """Test zero-downtime key rotation."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.vault_dir = self.test_dir / "vault"
        self.versions_dir = self.test_dir / "versions"
        self.history_dir = self.test_dir / "history"

        # Create secrets manager
        import os
        os.environ["MASTER_ENCRYPTION_KEY"] = "test_key_for_rotation_tests"
        self.secrets_manager = SecretsManager()

        # Create vault and rotation manager
        self.vault = CredentialVault(
            vault_dir=self.vault_dir,
            secrets_manager=self.secrets_manager
        )
        self.history = RotationHistory(history_dir=self.history_dir)
        self.rotation_manager = KeyRotationManager(
            vault=self.vault,
            history=self.history,
            versions_dir=self.versions_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        import os
        if "MASTER_ENCRYPTION_KEY" in os.environ:
            del os.environ["MASTER_ENCRYPTION_KEY"]

    def test_immediate_rotation(self):
        """Test immediate rotation strategy."""
        # Set initial credential
        self.vault.set_credential(
            name="TEST_API_KEY",
            value="initial_value",
            credential_type=CredentialType.API_KEY
        )

        # Configure immediate rotation
        config = RotationConfig(strategy=RotationStrategy.IMMEDIATE)
        self.rotation_manager.set_rotation_config("TEST_API_KEY", config)

        # Rotate
        rotation_id = self.rotation_manager.rotate(
            credential_name="TEST_API_KEY",
            new_value="new_value",
            reason=RotationReason.MANUAL
        )

        self.assertIsNotNone(rotation_id)

        # Verify new value is active
        value = self.rotation_manager.get_credential("TEST_API_KEY")
        self.assertEqual(value, "new_value")

        # Verify only one active version
        active_versions = self.rotation_manager.get_active_versions("TEST_API_KEY")
        self.assertEqual(len(active_versions), 1)

    def test_gradual_rotation(self):
        """Test gradual rotation strategy."""
        # Set initial credential
        self.vault.set_credential(
            name="TEST_TOKEN",
            value="old_token",
            credential_type=CredentialType.TOKEN
        )

        # Configure gradual rotation with 1-hour transition
        config = RotationConfig(
            strategy=RotationStrategy.GRADUAL,
            transition_period_hours=1
        )
        self.rotation_manager.set_rotation_config("TEST_TOKEN", config)

        # Rotate
        rotation_id = self.rotation_manager.rotate(
            credential_name="TEST_TOKEN",
            new_value="new_token",
            reason=RotationReason.SCHEDULED
        )

        self.assertIsNotNone(rotation_id)

        # Verify new value is primary
        value = self.rotation_manager.get_credential("TEST_TOKEN")
        self.assertEqual(value, "new_token")

        # Verify both versions are active during transition
        active_versions = self.rotation_manager.get_active_versions("TEST_TOKEN")
        self.assertEqual(len(active_versions), 2)

    def test_versioned_rotation(self):
        """Test versioned rotation strategy."""
        # Set initial credential
        self.vault.set_credential(
            name="TEST_SECRET",
            value="secret_v1",
            credential_type=CredentialType.SECRET
        )

        # Configure versioned rotation
        config = RotationConfig(
            strategy=RotationStrategy.VERSIONED,
            max_active_versions=3
        )
        self.rotation_manager.set_rotation_config("TEST_SECRET", config)

        # Rotate multiple times
        for i in range(4):
            self.rotation_manager.rotate(
                credential_name="TEST_SECRET",
                new_value=f"secret_v{i+2}",
                reason=RotationReason.MANUAL
            )

        # Verify max active versions is enforced
        active_versions = self.rotation_manager.get_active_versions("TEST_SECRET")
        self.assertLessEqual(len(active_versions), 3)

    def test_rotation_validation(self):
        """Test rotation with validation callback."""
        # Set initial credential
        self.vault.set_credential(
            name="TEST_KEY",
            value="valid_key",
            credential_type=CredentialType.API_KEY
        )

        # Configure with validation
        def validate(value: str) -> bool:
            return len(value) >= 10

        config = RotationConfig(
            strategy=RotationStrategy.IMMEDIATE,
            validation_callback=validate
        )
        self.rotation_manager.set_rotation_config("TEST_KEY", config)

        # Try to rotate with invalid value
        with self.assertRaises(ValueError):
            self.rotation_manager.rotate(
                credential_name="TEST_KEY",
                new_value="short",
                reason=RotationReason.MANUAL
            )

        # Rotate with valid value
        rotation_id = self.rotation_manager.rotate(
            credential_name="TEST_KEY",
            new_value="valid_long_key",
            reason=RotationReason.MANUAL
        )

        self.assertIsNotNone(rotation_id)

    def test_version_deprecation(self):
        """Test manual version deprecation."""
        # Set credential
        self.vault.set_credential(
            name="TEST_KEY",
            value="value",
            credential_type=CredentialType.API_KEY
        )

        # Rotate to create version
        self.rotation_manager.rotate(
            credential_name="TEST_KEY",
            new_value="new_value",
            reason=RotationReason.MANUAL
        )

        # Get versions
        versions = self.rotation_manager.get_active_versions("TEST_KEY")
        self.assertGreater(len(versions), 0)

        # Deprecate a version
        version_id = versions[0].version_id
        success = self.rotation_manager.deprecate_version(
            "TEST_KEY",
            version_id,
            graceful_period_hours=0
        )

        self.assertTrue(success)

        # Verify version is deprecated
        updated_versions = self.rotation_manager.get_active_versions("TEST_KEY")
        self.assertEqual(len(updated_versions), len(versions) - 1)

    def test_rotation_status(self):
        """Test getting rotation status."""
        # Set and rotate credential
        self.vault.set_credential(
            name="TEST_KEY",
            value="value",
            credential_type=CredentialType.API_KEY
        )

        self.rotation_manager.rotate(
            credential_name="TEST_KEY",
            new_value="new_value",
            reason=RotationReason.SCHEDULED
        )

        # Get status
        status = self.rotation_manager.get_rotation_status("TEST_KEY")

        self.assertEqual(status["credential_name"], "TEST_KEY")
        self.assertIsNotNone(status["primary_version_id"])
        self.assertIsNotNone(status["latest_rotation_status"])
        self.assertGreater(status["total_versions"], 0)


class TestRotationScheduler(unittest.TestCase):
    """Test automated rotation scheduler."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.vault_dir = self.test_dir / "vault"
        self.policies_dir = self.test_dir / "policies"

        # Create secrets manager
        import os
        os.environ["MASTER_ENCRYPTION_KEY"] = "test_key_for_scheduler_tests"
        self.secrets_manager = SecretsManager()

        # Create components
        self.vault = CredentialVault(
            vault_dir=self.vault_dir,
            secrets_manager=self.secrets_manager
        )
        self.rotation_manager = KeyRotationManager(vault=self.vault)
        self.scheduler = RotationScheduler(
            rotation_manager=self.rotation_manager,
            policies_dir=self.policies_dir,
            check_interval_seconds=1  # Fast for testing
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        import os
        if "MASTER_ENCRYPTION_KEY" in os.environ:
            del os.environ["MASTER_ENCRYPTION_KEY"]

    def test_add_policy(self):
        """Test adding rotation policy."""
        policy = RotationPolicy(
            credential_name="TEST_KEY",
            frequency=RotationFrequency.DAILY,
            rotation_config=RotationConfig(strategy=RotationStrategy.IMMEDIATE)
        )

        self.scheduler.add_policy(policy)

        # Verify policy was added
        retrieved = self.scheduler.get_policy("TEST_KEY")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.frequency, RotationFrequency.DAILY)

    def test_policy_persistence(self):
        """Test policy persistence across instances."""
        policy = RotationPolicy(
            credential_name="TEST_KEY",
            frequency=RotationFrequency.WEEKLY
        )

        self.scheduler.add_policy(policy)

        # Create new scheduler instance
        new_scheduler = RotationScheduler(
            rotation_manager=self.rotation_manager,
            policies_dir=self.policies_dir
        )

        # Verify policy was loaded
        retrieved = new_scheduler.get_policy("TEST_KEY")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.frequency, RotationFrequency.WEEKLY)

    def test_enable_disable_policy(self):
        """Test enabling and disabling policies."""
        policy = RotationPolicy(
            credential_name="TEST_KEY",
            enabled=True
        )

        self.scheduler.add_policy(policy)

        # Disable
        success = self.scheduler.disable_policy("TEST_KEY")
        self.assertTrue(success)

        retrieved = self.scheduler.get_policy("TEST_KEY")
        self.assertFalse(retrieved.enabled)

        # Enable
        success = self.scheduler.enable_policy("TEST_KEY")
        self.assertTrue(success)

        retrieved = self.scheduler.get_policy("TEST_KEY")
        self.assertTrue(retrieved.enabled)

    def test_policy_is_due(self):
        """Test checking if policy is due."""
        # Create policy with past next_rotation
        policy = RotationPolicy(
            credential_name="TEST_KEY",
            frequency=RotationFrequency.DAILY,
            next_rotation=datetime.utcnow() - timedelta(hours=1)
        )

        self.assertTrue(policy.is_due())

        # Update to future
        policy.next_rotation = datetime.utcnow() + timedelta(hours=1)
        self.assertFalse(policy.is_due())

    def test_get_next_rotations(self):
        """Test getting upcoming rotations."""
        # Add multiple policies
        for i in range(5):
            policy = RotationPolicy(
                credential_name=f"KEY_{i}",
                frequency=RotationFrequency.DAILY,
                next_rotation=datetime.utcnow() + timedelta(days=i)
            )
            self.scheduler.add_policy(policy)

        # Get next rotations
        next_rotations = self.scheduler.get_next_rotations(limit=3)

        self.assertEqual(len(next_rotations), 3)
        # Verify sorted by time
        for i in range(len(next_rotations) - 1):
            self.assertLess(next_rotations[i][1], next_rotations[i+1][1])

    def test_scheduler_status(self):
        """Test getting scheduler status."""
        # Add policies
        policy1 = RotationPolicy(credential_name="KEY_1", enabled=True)
        policy2 = RotationPolicy(credential_name="KEY_2", enabled=False)

        self.scheduler.add_policy(policy1)
        self.scheduler.add_policy(policy2)

        status = self.scheduler.get_status()

        self.assertEqual(status["total_policies"], 2)
        self.assertEqual(status["enabled_policies"], 1)
        self.assertFalse(status["running"])


if __name__ == '__main__':
    unittest.main()
