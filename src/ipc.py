"""
File-based IPC (Inter-Process Communication) System

Provides a simple file-based IPC mechanism using JSON signals for
communication between the bot process and the admin interface.
Signals are exchanged via files in a shared directory.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class IPCCommand(str, Enum):
    """Available IPC commands."""

    RELOAD_CONFIG = "reload_config"
    SHUTDOWN = "shutdown"
    PING = "ping"
    STATUS = "status"
    RESTART = "restart"
    UPDATE_CONFIG = "update_config"


@dataclass
class IPCSignal:
    """
    Represents an IPC signal exchanged between processes.

    Attributes:
        command: The IPC command
        data: Optional payload data
        timestamp: When the signal was created
        source: Who sent the signal
        signal_id: Unique identifier for this signal
    """

    command: IPCCommand
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    signal_id: str = ""

    def __post_init__(self):
        if not self.signal_id:
            self.signal_id = f"{self.command.value}_{int(self.timestamp * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary."""
        return {
            "command": self.command.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "signal_id": self.signal_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPCSignal":
        """Create signal from dictionary."""
        return cls(
            command=IPCCommand(data["command"]),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", time.time()),
            source=data.get("source", "unknown"),
            signal_id=data.get("signal_id", ""),
        )


class IPCChannel:
    """
    File-based IPC channel for process communication.

    Uses a shared directory to exchange JSON signal files between
    the bot process and admin interface. Each signal is written as
    a separate JSON file and consumed (deleted) after processing.
    """

    def __init__(self, ipc_dir: Path, channel_name: str = "bot"):
        """
        Initialize IPC channel.

        Args:
            ipc_dir: Directory for IPC signal files
            channel_name: Name of this channel endpoint
        """
        self.ipc_dir = Path(ipc_dir)
        self.channel_name = channel_name
        self.inbox_dir = self.ipc_dir / f"{channel_name}_inbox"
        self.status_file = self.ipc_dir / f"{channel_name}_status.json"

        # Handler registry: command -> async handler function
        self._handlers: Dict[IPCCommand, Callable[..., Coroutine]] = {}

        # Ensure directories exist
        self.ipc_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"IPC channel initialized: {channel_name} at {self.ipc_dir}")

    def register_handler(
        self,
        command: IPCCommand,
        handler: Callable[[IPCSignal], Coroutine],
    ) -> None:
        """
        Register a handler for an IPC command.

        Args:
            command: The IPC command to handle
            handler: Async function to call when command is received
        """
        self._handlers[command] = handler
        logger.debug(f"Registered IPC handler for {command.value}")

    def send_signal(self, signal: IPCSignal, target: str = "admin") -> None:
        """
        Send an IPC signal to a target channel.

        Args:
            signal: The signal to send
            target: Target channel name
        """
        target_dir = self.ipc_dir / f"{target}_inbox"
        target_dir.mkdir(parents=True, exist_ok=True)

        signal_file = target_dir / f"{signal.signal_id}.json"
        try:
            with open(signal_file, "w", encoding="utf-8") as f:
                json.dump(signal.to_dict(), f, indent=2)
            logger.debug(f"Sent IPC signal: {signal.command.value} -> {target}")
        except Exception as e:
            logger.error(f"Failed to send IPC signal: {e}")

    async def process_signals(self) -> List[Dict[str, Any]]:
        """
        Process all pending signals in the inbox.

        Reads and processes all signal files, calling registered handlers.

        Returns:
            List of results from processed signals
        """
        results = []

        if not self.inbox_dir.exists():
            return results

        # Get all signal files sorted by name (timestamp-based)
        signal_files = sorted(self.inbox_dir.glob("*.json"))

        for signal_file in signal_files:
            try:
                # Read signal
                with open(signal_file, "r", encoding="utf-8") as f:
                    signal_data = json.load(f)

                signal = IPCSignal.from_dict(signal_data)

                # Process signal
                result = await self._process_signal(signal)
                results.append(result)

                # Remove processed signal file
                signal_file.unlink()
                logger.debug(f"Processed and removed signal: {signal.signal_id}")

            except Exception as e:
                logger.error(f"Error processing signal file {signal_file}: {e}")
                # Remove broken signal files to prevent infinite retry
                try:
                    signal_file.unlink()
                except OSError:
                    pass

        return results

    async def _process_signal(self, signal: IPCSignal) -> Dict[str, Any]:
        """
        Process a single IPC signal.

        Args:
            signal: The signal to process

        Returns:
            Result dictionary
        """
        handler = self._handlers.get(signal.command)

        if handler is None:
            logger.warning(f"No handler for IPC command: {signal.command.value}")
            return {"error": f"No handler for command: {signal.command.value}"}

        try:
            result = await handler(signal)
            return result if result else {"status": "ok"}
        except Exception as e:
            logger.error(
                f"Error handling IPC command {signal.command.value}: {e}",
                exc_info=True,
            )
            return {"error": str(e)}

    def update_status(self, status: Dict[str, Any]) -> None:
        """
        Update the status file for this channel.

        Args:
            status: Status information to publish
        """
        try:
            status_data = {
                "channel": self.channel_name,
                "timestamp": time.time(),
                **status,
            }
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update status: {e}")

    def get_status(self, target: str = "admin") -> Optional[Dict[str, Any]]:
        """
        Read status from a target channel.

        Args:
            target: Target channel name

        Returns:
            Status dictionary or None
        """
        status_file = self.ipc_dir / f"{target}_status.json"
        if not status_file.exists():
            return None

        try:
            with open(status_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read status from {target}: {e}")
            return None

    def cleanup(self) -> None:
        """Clean up IPC resources."""
        try:
            # Remove status file
            if self.status_file.exists():
                self.status_file.unlink()

            # Remove remaining signal files in inbox
            if self.inbox_dir.exists():
                for f in self.inbox_dir.glob("*.json"):
                    f.unlink()

            logger.info(f"IPC channel {self.channel_name} cleaned up")
        except Exception as e:
            logger.error(f"Error during IPC cleanup: {e}")


# Module-level storage for channel instances
_channels: Dict[str, IPCChannel] = {}


def get_ipc_channel(
    project_root: Path,
    channel_name: str = "bot",
) -> IPCChannel:
    """
    Get or create an IPC channel.

    Args:
        project_root: Project root directory
        channel_name: Name of the channel endpoint

    Returns:
        IPCChannel instance
    """
    key = f"{project_root}:{channel_name}"
    if key not in _channels:
        ipc_dir = Path(project_root) / "data" / "ipc"
        _channels[key] = IPCChannel(ipc_dir, channel_name)
    return _channels[key]
