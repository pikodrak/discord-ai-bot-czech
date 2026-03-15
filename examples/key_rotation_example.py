"""
Example usage of the key rotation system.

Demonstrates basic rotation, automated scheduling, and monitoring.
"""

import asyncio
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.key_rotation import (
    KeyRotationManager,
    RotationConfig,
    RotationStrategy,
    get_rotation_manager
)
from src.rotation_history import (
    RotationHistory,
    RotationReason,
    RotationStatus,
    get_rotation_history
)
from src.rotation_scheduler import (
    RotationScheduler,
    RotationPolicy,
    RotationFrequency,
    get_rotation_scheduler
)
from src.credential_vault import CredentialType, get_credential_vault


def example_1_basic_rotation():
    """Example 1: Basic credential rotation."""
    print("\n=== Example 1: Basic Credential Rotation ===\n")

    # Initialize rotation manager
    manager = get_rotation_manager()

    # First, ensure the credential exists in vault
    vault = get_credential_vault()
    vault.set_credential(
        name="EXAMPLE_API_KEY",
        value="initial_api_key_value_123",
        credential_type=CredentialType.API_KEY,
        rotation_days=90
    )

    # Configure gradual rotation with 24-hour transition
    config = RotationConfig(
        strategy=RotationStrategy.GRADUAL,
        transition_period_hours=24,
        max_active_versions=2,
        auto_cleanup_expired=True
    )
    manager.set_rotation_config("EXAMPLE_API_KEY", config)

    # Perform rotation
    print("Rotating EXAMPLE_API_KEY...")
    rotation_id = manager.rotate(
        credential_name="EXAMPLE_API_KEY",
        new_value="new_api_key_value_456",
        reason=RotationReason.MANUAL,
        initiated_by="admin",
        metadata={"environment": "production"}
    )

    print(f"✓ Rotation completed: {rotation_id}")

    # Get rotation status
    status = manager.get_rotation_status("EXAMPLE_API_KEY")
    print(f"\nRotation Status:")
    print(f"  Primary version: {status['primary_version_id']}")
    print(f"  Active versions: {status['active_versions']}")
    print(f"  Total versions: {status['total_versions']}")

    # Get credential (returns primary version)
    value = manager.get_credential("EXAMPLE_API_KEY")
    print(f"\nCurrent credential value: {value}")


def example_2_rotation_history():
    """Example 2: Query rotation history."""
    print("\n=== Example 2: Rotation History ===\n")

    history = get_rotation_history()

    # Get recent rotations
    recent = history.get_history("EXAMPLE_API_KEY", limit=5)
    print(f"Recent rotations for EXAMPLE_API_KEY: {len(recent)}")

    for event in recent:
        duration = event.duration_seconds()
        print(f"\n  Rotation {event.rotation_id}:")
        print(f"    Status: {event.status.value}")
        print(f"    Reason: {event.reason.value}")
        print(f"    Initiated: {event.initiated_at.isoformat()}")
        if duration:
            print(f"    Duration: {duration:.2f}s")
        if event.initiated_by:
            print(f"    By: {event.initiated_by}")

    # Get statistics
    stats = history.get_statistics("EXAMPLE_API_KEY")
    print(f"\nRotation Statistics:")
    print(f"  Total rotations: {stats['total_rotations']}")
    print(f"  Successful: {stats['successful_rotations']}")
    print(f"  Failed: {stats['failed_rotations']}")
    if stats['average_duration_seconds']:
        print(f"  Average duration: {stats['average_duration_seconds']:.2f}s")


def example_3_version_management():
    """Example 3: Version management."""
    print("\n=== Example 3: Version Management ===\n")

    manager = get_rotation_manager()

    # Get active versions
    versions = manager.get_active_versions("EXAMPLE_API_KEY")
    print(f"Active versions: {len(versions)}")

    for version in versions:
        age_days = (datetime.utcnow() - version.created_at).days
        print(f"\n  Version {version.version_id}:")
        print(f"    Primary: {version.is_primary}")
        print(f"    Age: {age_days} days")
        print(f"    Usage count: {version.usage_count}")
        if version.expires_at:
            print(f"    Expires: {version.expires_at.isoformat()}")

    # Deprecate old version with graceful period
    if len(versions) > 1:
        old_version = [v for v in versions if not v.is_primary][0]
        print(f"\nDeprecating version {old_version.version_id} with 1-hour grace period...")

        success = manager.deprecate_version(
            "EXAMPLE_API_KEY",
            old_version.version_id,
            graceful_period_hours=1
        )

        if success:
            print("✓ Version deprecated")


async def example_4_automated_rotation():
    """Example 4: Automated rotation with scheduler."""
    print("\n=== Example 4: Automated Rotation ===\n")

    # Initialize scheduler
    scheduler = get_rotation_scheduler(check_interval_seconds=10)

    # Define value generator
    def generate_api_key():
        """Generate new API key."""
        return f"api_key_{secrets.token_urlsafe(32)}"

    # Define validation callback
    def validate_api_key(value: str) -> bool:
        """Validate new API key."""
        # Check minimum length
        if len(value) < 20:
            print("  ✗ Validation failed: too short")
            return False

        # Check format
        if not value.startswith("api_key_"):
            print("  ✗ Validation failed: invalid format")
            return False

        print("  ✓ Validation passed")
        return True

    # Define pre-rotation hook
    def pre_rotation_check(credential_name: str) -> bool:
        """Pre-rotation health check."""
        print(f"  Running pre-rotation check for {credential_name}...")
        # Simulate health check
        # In production, check system health, load, etc.
        return True

    # Define post-rotation hook
    def post_rotation_notify(credential_name: str, rotation_id: str):
        """Post-rotation notification."""
        print(f"  Rotation completed for {credential_name}: {rotation_id}")
        # In production, send notifications to Slack, email, etc.

    # Create rotation policy
    policy = RotationPolicy(
        credential_name="EXAMPLE_API_KEY",
        enabled=True,
        frequency=RotationFrequency.CUSTOM_DAYS,
        custom_days=1,  # Daily for demo (use appropriate interval in production)
        rotation_config=RotationConfig(
            strategy=RotationStrategy.GRADUAL,
            transition_period_hours=24,
            validation_callback=validate_api_key
        ),
        value_generator=generate_api_key,
        pre_rotation_hook=pre_rotation_check,
        post_rotation_hook=post_rotation_notify,
        metadata={"criticality": "high", "team": "security"}
    )

    # Add policy
    print("Adding rotation policy...")
    scheduler.add_policy(policy)

    # Get scheduler status
    status = scheduler.get_status()
    print(f"\nScheduler Status:")
    print(f"  Running: {status['running']}")
    print(f"  Total policies: {status['total_policies']}")
    print(f"  Enabled policies: {status['enabled_policies']}")

    # Get upcoming rotations
    next_rotations = scheduler.get_next_rotations(limit=3)
    print(f"\nUpcoming Rotations:")
    for cred_name, rotation_time in next_rotations:
        time_until = rotation_time - datetime.utcnow()
        print(f"  {cred_name}: {rotation_time.isoformat()} ({time_until})")

    # Force immediate rotation for demo
    print("\nForcing immediate rotation for demonstration...")
    success = await scheduler.rotate_now("EXAMPLE_API_KEY")

    if success:
        print("✓ Immediate rotation completed")
    else:
        print("✗ Immediate rotation failed")


def example_5_rotation_strategies():
    """Example 5: Different rotation strategies."""
    print("\n=== Example 5: Rotation Strategies ===\n")

    manager = get_rotation_manager()
    vault = get_credential_vault()

    # Strategy 1: Immediate rotation
    print("1. Immediate Rotation Strategy")
    print("   - Old credential invalidated immediately")
    print("   - Use for: compromised credentials, dev environments")

    vault.set_credential(
        name="IMMEDIATE_KEY",
        value="old_value",
        credential_type=CredentialType.API_KEY
    )

    config = RotationConfig(strategy=RotationStrategy.IMMEDIATE)
    manager.set_rotation_config("IMMEDIATE_KEY", config)

    manager.rotate(
        credential_name="IMMEDIATE_KEY",
        new_value="new_value",
        reason=RotationReason.COMPROMISED
    )

    versions = manager.get_active_versions("IMMEDIATE_KEY")
    print(f"   Active versions after rotation: {len(versions)}")

    # Strategy 2: Gradual rotation
    print("\n2. Gradual Rotation Strategy")
    print("   - Both credentials valid during transition")
    print("   - Use for: production services, zero-downtime requirement")

    vault.set_credential(
        name="GRADUAL_KEY",
        value="old_value",
        credential_type=CredentialType.TOKEN
    )

    config = RotationConfig(
        strategy=RotationStrategy.GRADUAL,
        transition_period_hours=48
    )
    manager.set_rotation_config("GRADUAL_KEY", config)

    manager.rotate(
        credential_name="GRADUAL_KEY",
        new_value="new_value",
        reason=RotationReason.SCHEDULED
    )

    versions = manager.get_active_versions("GRADUAL_KEY")
    print(f"   Active versions after rotation: {len(versions)}")

    # Strategy 3: Versioned rotation
    print("\n3. Versioned Rotation Strategy")
    print("   - Multiple versions tracked")
    print("   - Use for: complex migrations, canary deployments")

    vault.set_credential(
        name="VERSIONED_KEY",
        value="v1",
        credential_type=CredentialType.SECRET
    )

    config = RotationConfig(
        strategy=RotationStrategy.VERSIONED,
        max_active_versions=3
    )
    manager.set_rotation_config("VERSIONED_KEY", config)

    # Rotate multiple times
    for i in range(4):
        manager.rotate(
            credential_name="VERSIONED_KEY",
            new_value=f"v{i+2}",
            reason=RotationReason.MANUAL
        )

    versions = manager.get_active_versions("VERSIONED_KEY")
    print(f"   Active versions after 4 rotations: {len(versions)}")
    print(f"   (max_active_versions enforced: 3)")


def example_6_error_handling():
    """Example 6: Error handling and recovery."""
    print("\n=== Example 6: Error Handling ===\n")

    manager = get_rotation_manager()
    history = get_rotation_history()

    # Set up validation that will fail
    def strict_validation(value: str) -> bool:
        return len(value) >= 50  # Requires 50+ chars

    config = RotationConfig(
        strategy=RotationStrategy.IMMEDIATE,
        validation_callback=strict_validation
    )
    manager.set_rotation_config("EXAMPLE_API_KEY", config)

    # Try to rotate with invalid value
    print("Attempting rotation with invalid value...")
    try:
        manager.rotate(
            credential_name="EXAMPLE_API_KEY",
            new_value="short",  # Too short
            reason=RotationReason.MANUAL
        )
        print("✗ Should have failed validation")
    except ValueError as e:
        print(f"✓ Validation failed as expected: {e}")

    # Check failed rotations
    failed = history.get_failed_rotations("EXAMPLE_API_KEY")
    if failed:
        print(f"\nFailed rotations found: {len(failed)}")
        for event in failed[:3]:  # Show first 3
            print(f"  {event.rotation_id}: {event.error_message}")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Key Rotation System - Usage Examples")
    print("="*60)

    # Ensure master encryption key is set
    if not os.getenv("MASTER_ENCRYPTION_KEY"):
        print("\n⚠ MASTER_ENCRYPTION_KEY not set. Using demo key.")
        os.environ["MASTER_ENCRYPTION_KEY"] = "demo_key_for_examples_only_do_not_use_in_production"

    # Run examples
    try:
        example_1_basic_rotation()
        example_2_rotation_history()
        example_3_version_management()
        await example_4_automated_rotation()
        example_5_rotation_strategies()
        example_6_error_handling()

        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
