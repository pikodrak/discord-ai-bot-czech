"""
Automated rotation policy scheduler with configurable frequencies and hooks.

Provides automated credential rotation based on policies with support for
custom schedules, validation hooks, and rotation callbacks.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import json

from src.key_rotation import (
    KeyRotationManager,
    RotationConfig,
    get_rotation_manager
)
from src.rotation_history import RotationReason, RotationStatus


class RotationFrequency(Enum):
    """Predefined rotation frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM_DAYS = "custom_days"


@dataclass
class RotationPolicy:
    """
    Policy defining automated rotation behavior for a credential.
    """

    credential_name: str
    enabled: bool = True
    frequency: RotationFrequency = RotationFrequency.MONTHLY
    custom_days: Optional[int] = None
    rotation_config: Optional[RotationConfig] = None
    value_generator: Optional[Callable[[], str]] = None
    pre_rotation_hook: Optional[Callable[[str], bool]] = None
    post_rotation_hook: Optional[Callable[[str, str], None]] = None
    metadata: Optional[Dict[str, Any]] = None
    last_rotation: Optional[datetime] = None
    next_rotation: Optional[datetime] = None

    def get_rotation_interval_days(self) -> int:
        """
        Get rotation interval in days.

        Returns:
            Number of days between rotations
        """
        if self.frequency == RotationFrequency.DAILY:
            return 1
        elif self.frequency == RotationFrequency.WEEKLY:
            return 7
        elif self.frequency == RotationFrequency.MONTHLY:
            return 30
        elif self.frequency == RotationFrequency.QUARTERLY:
            return 90
        elif self.frequency == RotationFrequency.YEARLY:
            return 365
        elif self.frequency == RotationFrequency.CUSTOM_DAYS:
            return self.custom_days or 30
        return 30

    def calculate_next_rotation(self) -> datetime:
        """
        Calculate next rotation time.

        Returns:
            Datetime for next rotation
        """
        if self.last_rotation:
            base_time = self.last_rotation
        else:
            base_time = datetime.utcnow()

        interval_days = self.get_rotation_interval_days()
        return base_time + timedelta(days=interval_days)

    def is_due(self) -> bool:
        """
        Check if rotation is due.

        Returns:
            True if rotation should occur
        """
        if not self.enabled:
            return False

        if not self.next_rotation:
            return True  # Never rotated, do it now

        return datetime.utcnow() >= self.next_rotation

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation (excludes callbacks)
        """
        return {
            "credential_name": self.credential_name,
            "enabled": self.enabled,
            "frequency": self.frequency.value,
            "custom_days": self.custom_days,
            "rotation_config": self.rotation_config.to_dict() if self.rotation_config else None,
            "metadata": self.metadata,
            "last_rotation": self.last_rotation.isoformat() if self.last_rotation else None,
            "next_rotation": self.next_rotation.isoformat() if self.next_rotation else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RotationPolicy":
        """
        Create from dictionary.

        Args:
            data: Dictionary with policy data

        Returns:
            RotationPolicy instance
        """
        rotation_config = None
        if data.get("rotation_config"):
            from src.key_rotation import RotationConfig
            rotation_config = RotationConfig.from_dict(data["rotation_config"])

        return cls(
            credential_name=data["credential_name"],
            enabled=data.get("enabled", True),
            frequency=RotationFrequency(data["frequency"]),
            custom_days=data.get("custom_days"),
            rotation_config=rotation_config,
            metadata=data.get("metadata"),
            last_rotation=datetime.fromisoformat(data["last_rotation"]) if data.get("last_rotation") else None,
            next_rotation=datetime.fromisoformat(data["next_rotation"]) if data.get("next_rotation") else None
        )


class RotationScheduler:
    """
    Automated credential rotation scheduler.

    Manages rotation policies and executes scheduled rotations based on
    configured frequencies and hooks.

    Example:
        ```python
        scheduler = RotationScheduler(check_interval_seconds=60)

        # Define policy
        policy = RotationPolicy(
            credential_name="API_KEY",
            frequency=RotationFrequency.MONTHLY,
            value_generator=lambda: generate_new_key()
        )

        scheduler.add_policy(policy)
        await scheduler.start()
        ```
    """

    def __init__(
        self,
        rotation_manager: Optional[KeyRotationManager] = None,
        check_interval_seconds: int = 60,
        scheduler_dir: Optional[Path] = None
    ):
        """
        Initialize rotation scheduler.

        Args:
            rotation_manager: KeyRotationManager instance
            check_interval_seconds: Interval for checking due rotations
            scheduler_dir: Directory for storing scheduler data
        """
        self.rotation_manager = rotation_manager or get_rotation_manager()
        self.check_interval_seconds = check_interval_seconds
        self.scheduler_dir = scheduler_dir or Path("data/scheduler")
        self.scheduler_dir.mkdir(parents=True, exist_ok=True)

        self._policies: Dict[str, RotationPolicy] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        self._load_policies()

    def _get_policies_path(self) -> Path:
        """Get path to policies file."""
        return self.scheduler_dir / "rotation_policies.json"

    def _load_policies(self) -> None:
        """Load policies from disk."""
        policies_path = self._get_policies_path()

        if policies_path.exists():
            try:
                with open(policies_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._policies = {
                    name: RotationPolicy.from_dict(policy_data)
                    for name, policy_data in data.items()
                }
            except Exception:
                self._policies = {}

    def _save_policies(self) -> None:
        """Save policies to disk."""
        policies_path = self._get_policies_path()

        try:
            data = {
                name: policy.to_dict()
                for name, policy in self._policies.items()
            }

            with open(policies_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            raise IOError(f"Failed to save rotation policies: {e}")

    def add_policy(self, policy: RotationPolicy) -> None:
        """
        Add or update rotation policy.

        Args:
            policy: RotationPolicy to add
        """
        # Calculate next rotation if not set
        if not policy.next_rotation:
            policy.next_rotation = policy.calculate_next_rotation()

        # Apply rotation config to manager if provided
        if policy.rotation_config:
            self.rotation_manager.set_rotation_config(
                policy.credential_name,
                policy.rotation_config
            )

        self._policies[policy.credential_name] = policy
        self._save_policies()

    def remove_policy(self, credential_name: str) -> bool:
        """
        Remove rotation policy.

        Args:
            credential_name: Name of credential

        Returns:
            True if removed, False if not found
        """
        if credential_name in self._policies:
            del self._policies[credential_name]
            self._save_policies()
            return True
        return False

    def get_policy(self, credential_name: str) -> Optional[RotationPolicy]:
        """
        Get rotation policy for a credential.

        Args:
            credential_name: Name of credential

        Returns:
            RotationPolicy or None if not found
        """
        return self._policies.get(credential_name)

    def enable_policy(self, credential_name: str) -> bool:
        """
        Enable rotation policy.

        Args:
            credential_name: Name of credential

        Returns:
            True if enabled, False if not found
        """
        policy = self._policies.get(credential_name)
        if policy:
            policy.enabled = True
            self._save_policies()
            return True
        return False

    def disable_policy(self, credential_name: str) -> bool:
        """
        Disable rotation policy.

        Args:
            credential_name: Name of credential

        Returns:
            True if disabled, False if not found
        """
        policy = self._policies.get(credential_name)
        if policy:
            policy.enabled = False
            self._save_policies()
            return True
        return False

    async def rotate_now(
        self,
        credential_name: str,
        reason: RotationReason = RotationReason.MANUAL
    ) -> bool:
        """
        Force immediate rotation for a credential.

        Args:
            credential_name: Name of credential to rotate
            reason: Reason for rotation

        Returns:
            True if successful, False otherwise
        """
        policy = self._policies.get(credential_name)
        if not policy:
            return False

        try:
            success = await self._execute_rotation(policy, reason)

            if success:
                # Update policy timing
                policy.last_rotation = datetime.utcnow()
                policy.next_rotation = policy.calculate_next_rotation()
                self._save_policies()

            return success

        except Exception:
            return False

    async def _execute_rotation(
        self,
        policy: RotationPolicy,
        reason: RotationReason = RotationReason.SCHEDULED
    ) -> bool:
        """
        Execute rotation for a policy.

        Args:
            policy: RotationPolicy to execute
            reason: Reason for rotation

        Returns:
            True if successful, False otherwise
        """
        credential_name = policy.credential_name

        try:
            # Run pre-rotation hook if provided
            if policy.pre_rotation_hook:
                if not policy.pre_rotation_hook(credential_name):
                    return False

            # Generate new value
            if not policy.value_generator:
                return False

            new_value = policy.value_generator()

            # Perform rotation
            rotation_id = self.rotation_manager.rotate(
                credential_name=credential_name,
                new_value=new_value,
                reason=reason,
                initiated_by="scheduler",
                metadata=policy.metadata
            )

            # Run post-rotation hook if provided
            if policy.post_rotation_hook:
                policy.post_rotation_hook(credential_name, rotation_id)

            return True

        except Exception:
            return False

    async def _check_and_rotate(self) -> None:
        """Check for due rotations and execute them."""
        for policy in self._policies.values():
            if policy.is_due():
                success = await self._execute_rotation(policy)

                if success:
                    # Update policy timing
                    policy.last_rotation = datetime.utcnow()
                    policy.next_rotation = policy.calculate_next_rotation()
                    self._save_policies()

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_and_rotate()
            except Exception:
                # Continue running even if check fails
                pass

            await asyncio.sleep(self.check_interval_seconds)

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None

    def get_status(self) -> Dict[str, Any]:
        """
        Get scheduler status.

        Returns:
            Dictionary with scheduler status information
        """
        enabled_policies = [p for p in self._policies.values() if p.enabled]
        due_policies = [p for p in enabled_policies if p.is_due()]

        return {
            "running": self._running,
            "total_policies": len(self._policies),
            "enabled_policies": len(enabled_policies),
            "disabled_policies": len(self._policies) - len(enabled_policies),
            "due_rotations": len(due_policies),
            "check_interval_seconds": self.check_interval_seconds
        }

    def get_next_rotations(self, limit: int = 10) -> List[Tuple[str, datetime]]:
        """
        Get upcoming rotations.

        Args:
            limit: Maximum number of rotations to return

        Returns:
            List of (credential_name, next_rotation_time) tuples
        """
        enabled_policies = [p for p in self._policies.values() if p.enabled and p.next_rotation]

        # Sort by next_rotation time
        enabled_policies.sort(key=lambda p: p.next_rotation)

        return [
            (p.credential_name, p.next_rotation)
            for p in enabled_policies[:limit]
        ]

    def get_all_policies(self) -> List[RotationPolicy]:
        """
        Get all rotation policies.

        Returns:
            List of all RotationPolicy instances
        """
        return list(self._policies.values())


# Global scheduler instance
_scheduler_instance: Optional[RotationScheduler] = None


def get_rotation_scheduler(
    rotation_manager: Optional[KeyRotationManager] = None,
    check_interval_seconds: int = 60,
    scheduler_dir: Optional[Path] = None
) -> RotationScheduler:
    """
    Get or create singleton rotation scheduler instance.

    Args:
        rotation_manager: Optional rotation manager
        check_interval_seconds: Check interval in seconds
        scheduler_dir: Optional scheduler directory

    Returns:
        RotationScheduler instance
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        _scheduler_instance = RotationScheduler(
            rotation_manager=rotation_manager,
            check_interval_seconds=check_interval_seconds,
            scheduler_dir=scheduler_dir
        )

    return _scheduler_instance
