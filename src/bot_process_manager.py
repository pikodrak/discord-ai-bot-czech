"""
Bot Process Manager for Discord bot lifecycle management.

Provides process management, monitoring, and control for the Discord bot subprocess.
"""

import asyncio
import logging
import os
import signal
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any

try:
    import psutil
except ImportError:
    psutil = None


logger = logging.getLogger(__name__)


class ProcessState(Enum):
    """Bot process states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ProcessInfo:
    """Information about bot process state."""

    state: ProcessState
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    restart_count: int = 0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "state": self.state.value,
            "pid": self.pid,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "restart_count": self.restart_count,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "error_message": self.error_message
        }


class BotProcessManager:
    """
    Manages Discord bot subprocess lifecycle.

    Handles starting, stopping, restarting, and monitoring the bot process.

    Example:
        ```python
        manager = BotProcessManager(
            project_dir=Path("/path/to/project"),
            bot_script="main.py"
        )

        # Start bot
        await manager.start()

        # Check status
        info = manager.get_status()
        print(f"Bot state: {info.state}")

        # Stop bot
        await manager.stop()
        ```
    """

    def __init__(
        self,
        project_dir: Path,
        bot_script: str = "main.py",
        pid_file: Optional[Path] = None
    ):
        """
        Initialize bot process manager.

        Args:
            project_dir: Project root directory
            bot_script: Bot script filename (relative to project_dir)
            pid_file: Optional PID file path. Defaults to data/bot.pid
        """
        self.project_dir = Path(project_dir)
        self.bot_script = self.project_dir / bot_script
        self.pid_file = pid_file or self.project_dir / "data" / "bot.pid"

        self._process: Optional[asyncio.subprocess.Process] = None
        self._state = ProcessState.STOPPED
        self._started_at: Optional[datetime] = None
        self._restart_count = 0
        self._error_message: Optional[str] = None

        # Ensure PID file directory exists
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

    def get_status(self) -> ProcessInfo:
        """
        Get current process status.

        Returns:
            ProcessInfo with current state and metrics
        """
        cpu_percent = 0.0
        memory_mb = 0.0

        if self._process and psutil:
            try:
                proc = psutil.Process(self._process.pid)
                cpu_percent = proc.cpu_percent(interval=0.1)
                memory_mb = proc.memory_info().rss / 1024 / 1024
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return ProcessInfo(
            state=self._state,
            pid=self._process.pid if self._process else None,
            started_at=self._started_at,
            restart_count=self._restart_count,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            error_message=self._error_message
        )

    def is_running(self) -> bool:
        """
        Check if bot process is running.

        Returns:
            True if bot is running
        """
        if not self._process:
            return False

        return self._process.returncode is None

    async def start(
        self,
        env_vars: Optional[Dict[str, str]] = None,
        timeout: float = 10.0
    ) -> bool:
        """
        Start bot process.

        Args:
            env_vars: Optional environment variables to inject
            timeout: Startup timeout in seconds

        Returns:
            True if started successfully

        Raises:
            RuntimeError: If bot is already running
        """
        if self.is_running():
            raise RuntimeError("Bot is already running")

        self._state = ProcessState.STARTING
        self._error_message = None

        try:
            # Prepare environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            # Start process
            self._process = await asyncio.create_subprocess_exec(
                "python3",
                str(self.bot_script),
                cwd=str(self.project_dir),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True
            )

            self._started_at = datetime.utcnow()

            # Write PID file
            with open(self.pid_file, 'w') as f:
                f.write(str(self._process.pid))

            # Wait for process to stabilize
            await asyncio.sleep(2.0)

            # Check if process is still running
            if self.is_running():
                self._state = ProcessState.RUNNING
                logger.info(f"Bot process started with PID {self._process.pid}")
                return True
            else:
                self._state = ProcessState.ERROR
                self._error_message = "Process exited immediately after start"
                logger.error(self._error_message)
                return False

        except Exception as e:
            self._state = ProcessState.ERROR
            self._error_message = str(e)
            logger.error(f"Failed to start bot process: {e}")
            return False

    async def stop(self, timeout: float = 10.0) -> bool:
        """
        Stop bot process gracefully.

        Args:
            timeout: Graceful shutdown timeout in seconds

        Returns:
            True if stopped successfully
        """
        if not self.is_running():
            self._state = ProcessState.STOPPED
            return True

        self._state = ProcessState.STOPPING
        logger.info(f"Stopping bot process PID {self._process.pid}")

        try:
            # Send SIGTERM for graceful shutdown
            self._process.send_signal(signal.SIGTERM)

            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(self._process.wait(), timeout=timeout)
                logger.info("Bot process stopped gracefully")
            except asyncio.TimeoutError:
                logger.warning(f"Graceful shutdown timed out, sending SIGKILL")
                self._process.kill()
                await self._process.wait()

            self._state = ProcessState.STOPPED
            self._process = None

            # Remove PID file
            if self.pid_file.exists():
                self.pid_file.unlink()

            return True

        except Exception as e:
            self._state = ProcessState.ERROR
            self._error_message = str(e)
            logger.error(f"Failed to stop bot process: {e}")
            return False

    async def restart(
        self,
        env_vars: Optional[Dict[str, str]] = None,
        timeout: float = 10.0
    ) -> bool:
        """
        Restart bot process.

        Args:
            env_vars: Optional environment variables to inject
            timeout: Shutdown/startup timeout in seconds

        Returns:
            True if restarted successfully
        """
        logger.info("Restarting bot process")

        # Stop if running
        if self.is_running():
            if not await self.stop(timeout=timeout):
                return False

        # Increment restart counter
        self._restart_count += 1

        # Start new process
        return await self.start(env_vars=env_vars, timeout=timeout)

    async def recover(
        self,
        env_vars: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Attempt to recover from error state.

        Args:
            env_vars: Optional environment variables to inject

        Returns:
            True if recovery successful
        """
        logger.info("Attempting process recovery")

        # Force cleanup
        if self._process:
            try:
                self._process.kill()
                await self._process.wait()
            except:
                pass
            self._process = None

        self._state = ProcessState.STOPPED
        self._error_message = None

        # Restart
        return await self.restart(env_vars=env_vars)

    def get_resource_usage(self) -> Dict[str, float]:
        """
        Get current resource usage metrics.

        Returns:
            Dictionary with cpu_percent and memory_mb
        """
        if not self._process or not psutil:
            return {"cpu_percent": 0.0, "memory_mb": 0.0}

        try:
            proc = psutil.Process(self._process.pid)
            return {
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_mb": proc.memory_info().rss / 1024 / 1024
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"cpu_percent": 0.0, "memory_mb": 0.0}

    def get_uptime_seconds(self) -> float:
        """
        Get process uptime in seconds.

        Returns:
            Uptime in seconds, 0.0 if not running
        """
        if not self._started_at or not self.is_running():
            return 0.0

        return (datetime.utcnow() - self._started_at).total_seconds()


# Global instance
_bot_manager: Optional[BotProcessManager] = None


def get_bot_manager(
    project_dir: Optional[Path] = None,
    bot_script: str = "main.py"
) -> BotProcessManager:
    """
    Get or create singleton bot process manager instance.

    Args:
        project_dir: Project root directory. If None, uses current directory.
        bot_script: Bot script filename

    Returns:
        BotProcessManager instance
    """
    global _bot_manager

    if _bot_manager is None:
        if project_dir is None:
            project_dir = Path.cwd()
        _bot_manager = BotProcessManager(
            project_dir=project_dir,
            bot_script=bot_script
        )

    return _bot_manager
