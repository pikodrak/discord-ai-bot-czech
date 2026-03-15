"""
Complete rotation history tracking system with event logging, status tracking, statistics, and audit trail capabilities.

Provides comprehensive tracking of all credential rotation events with metadata,
status updates, and analytical capabilities for monitoring rotation health.
"""

import json
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict


class RotationReason(Enum):
    """Reasons for credential rotation."""

    SCHEDULED = "scheduled"
    MANUAL = "manual"
    COMPROMISED = "compromised"
    EXPIRED = "expired"
    POLICY = "policy"


class RotationStatus(Enum):
    """Status of rotation operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class RotationEvent:
    """Record of a single rotation event."""

    rotation_id: str
    credential_name: str
    status: RotationStatus
    reason: RotationReason
    initiated_at: datetime
    initiated_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    old_version_id: Optional[str] = None
    new_version_id: Optional[str] = None

    def duration_seconds(self) -> Optional[float]:
        """
        Calculate rotation duration in seconds.

        Returns:
            Duration in seconds, or None if not completed
        """
        if not self.completed_at:
            return None

        delta = self.completed_at - self.initiated_at
        return delta.total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "rotation_id": self.rotation_id,
            "credential_name": self.credential_name,
            "status": self.status.value,
            "reason": self.reason.value,
            "initiated_at": self.initiated_at.isoformat(),
            "initiated_by": self.initiated_by,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "old_version_id": self.old_version_id,
            "new_version_id": self.new_version_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RotationEvent":
        """
        Create from dictionary.

        Args:
            data: Dictionary with event data

        Returns:
            RotationEvent instance
        """
        return cls(
            rotation_id=data["rotation_id"],
            credential_name=data["credential_name"],
            status=RotationStatus(data["status"]),
            reason=RotationReason(data["reason"]),
            initiated_at=datetime.fromisoformat(data["initiated_at"]),
            initiated_by=data.get("initiated_by"),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message"),
            metadata=data.get("metadata"),
            old_version_id=data.get("old_version_id"),
            new_version_id=data.get("new_version_id")
        )


class RotationHistory:
    """
    Tracks and manages rotation event history.

    Provides comprehensive logging of rotation events with querying,
    statistics, and audit trail capabilities.

    Example:
        ```python
        history = RotationHistory()

        # Record rotation event
        event_id = history.record_rotation(
            credential_name="API_KEY",
            reason=RotationReason.SCHEDULED,
            initiated_by="scheduler"
        )

        # Mark as completed
        history.update_status(event_id, RotationStatus.COMPLETED)

        # Query history
        events = history.get_history("API_KEY", limit=10)
        ```
    """

    def __init__(self, history_dir: Optional[Path] = None):
        """
        Initialize rotation history tracker.

        Args:
            history_dir: Directory for storing history files.
                        Defaults to data/rotation_history/
        """
        self.history_dir = history_dir or Path("data/rotation_history")
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self._events: Dict[str, RotationEvent] = {}
        self._load_history()

    def _get_history_path(self) -> Path:
        """
        Get path to history file.

        Returns:
            Path to history JSON file
        """
        return self.history_dir / "rotation_events.json"

    def _load_history(self) -> None:
        """Load rotation history from disk."""
        history_path = self._get_history_path()

        if history_path.exists():
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._events = {
                    event_id: RotationEvent.from_dict(event_data)
                    for event_id, event_data in data.items()
                }
            except Exception:
                # If history is corrupted, start fresh
                self._events = {}

    def _save_history(self) -> None:
        """Save rotation history to disk."""
        history_path = self._get_history_path()

        try:
            data = {
                event_id: event.to_dict()
                for event_id, event in self._events.items()
            }

            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            raise IOError(f"Failed to save rotation history: {e}")

    def record_rotation(
        self,
        credential_name: str,
        reason: RotationReason,
        initiated_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        old_version_id: Optional[str] = None,
        new_version_id: Optional[str] = None
    ) -> str:
        """
        Record a new rotation event.

        Args:
            credential_name: Name of credential being rotated
            reason: Reason for rotation
            initiated_by: User or system that initiated rotation
            metadata: Additional metadata
            old_version_id: Previous version ID
            new_version_id: New version ID

        Returns:
            Rotation event ID
        """
        rotation_id = str(uuid.uuid4())

        event = RotationEvent(
            rotation_id=rotation_id,
            credential_name=credential_name,
            status=RotationStatus.PENDING,
            reason=reason,
            initiated_at=datetime.utcnow(),
            initiated_by=initiated_by,
            metadata=metadata or {},
            old_version_id=old_version_id,
            new_version_id=new_version_id
        )

        self._events[rotation_id] = event
        self._save_history()

        return rotation_id

    def update_status(
        self,
        rotation_id: str,
        status: RotationStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update rotation event status.

        Args:
            rotation_id: Rotation event ID
            status: New status
            error_message: Optional error message for failed rotations

        Returns:
            True if updated, False if event not found
        """
        if rotation_id not in self._events:
            return False

        event = self._events[rotation_id]
        event.status = status

        if status in [RotationStatus.COMPLETED, RotationStatus.FAILED, RotationStatus.ROLLED_BACK]:
            event.completed_at = datetime.utcnow()

        if error_message:
            event.error_message = error_message

        self._save_history()
        return True

    def get_event(self, rotation_id: str) -> Optional[RotationEvent]:
        """
        Get specific rotation event.

        Args:
            rotation_id: Rotation event ID

        Returns:
            RotationEvent or None if not found
        """
        return self._events.get(rotation_id)

    def get_history(
        self,
        credential_name: str,
        limit: Optional[int] = None,
        status: Optional[RotationStatus] = None
    ) -> List[RotationEvent]:
        """
        Get rotation history for a credential.

        Args:
            credential_name: Name of credential
            limit: Maximum number of events to return
            status: Optional filter by status

        Returns:
            List of rotation events, most recent first
        """
        events = [
            event for event in self._events.values()
            if event.credential_name == credential_name
        ]

        if status:
            events = [e for e in events if e.status == status]

        # Sort by initiated_at, most recent first
        events.sort(key=lambda e: e.initiated_at, reverse=True)

        if limit:
            events = events[:limit]

        return events

    def get_failed_rotations(
        self,
        credential_name: Optional[str] = None
    ) -> List[RotationEvent]:
        """
        Get all failed rotation events.

        Args:
            credential_name: Optional filter by credential name

        Returns:
            List of failed rotation events
        """
        events = [
            event for event in self._events.values()
            if event.status == RotationStatus.FAILED
        ]

        if credential_name:
            events = [e for e in events if e.credential_name == credential_name]

        events.sort(key=lambda e: e.initiated_at, reverse=True)
        return events

    def get_statistics(self, credential_name: str) -> Dict[str, Any]:
        """
        Get rotation statistics for a credential.

        Args:
            credential_name: Name of credential

        Returns:
            Dictionary with statistics
        """
        events = [
            event for event in self._events.values()
            if event.credential_name == credential_name
        ]

        total_rotations = len(events)
        successful = len([e for e in events if e.status == RotationStatus.COMPLETED])
        failed = len([e for e in events if e.status == RotationStatus.FAILED])
        pending = len([e for e in events if e.status == RotationStatus.PENDING])

        # Calculate average duration for completed rotations
        completed_events = [e for e in events if e.status == RotationStatus.COMPLETED]
        durations = [e.duration_seconds() for e in completed_events if e.duration_seconds() is not None]
        avg_duration = sum(durations) / len(durations) if durations else None

        # Find last rotation
        last_rotation = None
        if events:
            sorted_events = sorted(events, key=lambda e: e.initiated_at, reverse=True)
            last_rotation = sorted_events[0].initiated_at

        return {
            "total_rotations": total_rotations,
            "successful_rotations": successful,
            "failed_rotations": failed,
            "pending_rotations": pending,
            "average_duration_seconds": avg_duration,
            "last_rotation": last_rotation.isoformat() if last_rotation else None,
            "success_rate": (successful / total_rotations * 100) if total_rotations > 0 else 0.0
        }

    def get_all_credentials(self) -> List[str]:
        """
        Get list of all credentials with rotation history.

        Returns:
            List of unique credential names
        """
        credentials = set(event.credential_name for event in self._events.values())
        return sorted(list(credentials))

    def cleanup_old_events(self, days_to_keep: int = 90) -> int:
        """
        Remove rotation events older than specified days.

        Args:
            days_to_keep: Number of days of history to retain

        Returns:
            Number of events removed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        events_to_remove = [
            rotation_id for rotation_id, event in self._events.items()
            if event.initiated_at < cutoff_date
        ]

        for rotation_id in events_to_remove:
            del self._events[rotation_id]

        if events_to_remove:
            self._save_history()

        return len(events_to_remove)


# Global history instance
_history_instance: Optional[RotationHistory] = None


def get_rotation_history(history_dir: Optional[Path] = None) -> RotationHistory:
    """
    Get or create singleton rotation history instance.

    Args:
        history_dir: Optional history directory

    Returns:
        RotationHistory instance
    """
    global _history_instance

    if _history_instance is None:
        _history_instance = RotationHistory(history_dir=history_dir)

    return _history_instance
