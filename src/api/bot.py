"""
Bot management router.

Provides endpoints for controlling and monitoring the Discord bot.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from src.bot_process_manager import (
    get_bot_manager,
    BotProcessManager,
    ProcessState,
    ProcessInfo
)


logger = logging.getLogger(__name__)
router = APIRouter()


# Initialize bot manager
try:
    project_dir = Path(__file__).parent.parent.parent
    bot_manager = get_bot_manager(project_dir)
    logger.info(f"Bot manager initialized for project: {project_dir}")
except Exception as e:
    logger.error(f"Failed to initialize bot manager: {e}")
    bot_manager = None


class BotStatus(BaseModel):
    """Model for bot status response."""

    running: bool
    state: str
    pid: Optional[int] = None
    uptime_seconds: Optional[float] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    restart_count: int = 0
    started_at: Optional[str] = None


class BotCommand(BaseModel):
    """Model for bot control commands."""

    action: str = Field(..., description="Action to perform: start, stop, or restart")
    env_vars: Optional[Dict[str, str]] = Field(None, description="Optional environment variables")
    timeout: float = Field(10.0, description="Timeout for stop operation in seconds", ge=1, le=60)


class BotRestartRequest(BaseModel):
    """Model for bot restart requests."""

    timeout: float = Field(10.0, description="Timeout for shutdown in seconds", ge=1, le=60)
    env_vars: Optional[Dict[str, str]] = Field(None, description="Optional environment variables to pass to bot")


class BotRestartResponse(BaseModel):
    """Model for bot restart response."""

    success: bool
    message: str
    previous_state: str
    current_state: str
    pid: Optional[int] = None
    restart_count: int


class BotStats(BaseModel):
    """Model for bot statistics."""

    total_messages_processed: int
    total_responses_sent: int
    ai_provider_usage: Dict[str, int]
    average_response_time_ms: float
    uptime_hours: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None


def get_manager() -> BotProcessManager:
    """
    Dependency to get bot manager.

    Returns:
        BotProcessManager instance

    Raises:
        HTTPException: If bot manager is not initialized
    """
    if bot_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot manager not initialized"
        )
    return bot_manager


@router.get("/status", response_model=BotStatus)
async def get_bot_status(manager: BotProcessManager = Depends(get_manager)) -> BotStatus:
    """
    Get current bot status.

    Returns detailed information about the bot process including:
    - Running state
    - Process ID
    - Uptime
    - Resource usage (CPU, memory)
    - Restart count

    Args:
        manager: Bot process manager (injected)

    Returns:
        BotStatus: Current bot status
    """
    try:
        process_info: ProcessInfo = manager.get_status()

        return BotStatus(
            running=process_info.state == ProcessState.RUNNING,
            state=process_info.state.value,
            pid=process_info.pid,
            uptime_seconds=process_info.uptime_seconds,
            cpu_percent=process_info.cpu_percent,
            memory_mb=process_info.memory_mb,
            restart_count=process_info.restart_count,
            started_at=process_info.started_at.isoformat() if process_info.started_at else None
        )

    except Exception as e:
        logger.error(f"Failed to get bot status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bot status: {str(e)}"
        )


@router.post("/control")
async def control_bot(
    command: BotCommand,
    manager: BotProcessManager = Depends(get_manager)
) -> Dict[str, Any]:
    """
    Control bot operations (start, stop, restart).

    Allows controlling the bot process lifecycle:
    - start: Start the bot process
    - stop: Gracefully stop the bot process
    - restart: Restart the bot process

    Args:
        command: Bot command to execute
        manager: Bot process manager (injected)

    Returns:
        Dict[str, Any]: Command result with success status and message

    Raises:
        HTTPException: If command is invalid or execution fails
    """
    valid_actions = ["start", "stop", "restart"]

    if command.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
        )

    logger.info(f"Executing bot command: {command.action}")

    try:
        if command.action == "start":
            success = await manager.start(env_vars=command.env_vars)
            message = "Bot started successfully" if success else "Failed to start bot"

        elif command.action == "stop":
            success = await manager.stop(timeout=command.timeout)
            message = "Bot stopped successfully" if success else "Failed to stop bot"

        elif command.action == "restart":
            success = await manager.restart(
                env_vars=command.env_vars,
                timeout=command.timeout
            )
            message = "Bot restarted successfully" if success else "Failed to restart bot"

        else:
            # Should never reach here due to validation above
            raise ValueError(f"Unexpected action: {command.action}")

        # Get updated status
        process_info = manager.get_status()

        return {
            "success": success,
            "message": message,
            "action": command.action,
            "current_state": process_info.state.value,
            "pid": process_info.pid
        }

    except RuntimeError as e:
        logger.error(f"Runtime error executing {command.action}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to execute {command.action}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute {command.action}: {str(e)}"
        )


@router.post("/restart", response_model=BotRestartResponse)
async def restart_bot(
    request: BotRestartRequest = BotRestartRequest(),
    manager: BotProcessManager = Depends(get_manager)
) -> BotRestartResponse:
    """
    Restart the Discord bot process.

    This endpoint gracefully restarts the bot by:
    1. Stopping the current process (with timeout)
    2. Waiting for clean shutdown
    3. Starting a new process
    4. Verifying the new process is running

    This is the recommended endpoint to use after configuration changes
    to ensure the bot picks up the new settings.

    Args:
        request: Restart request with optional timeout and environment variables
        manager: Bot process manager (injected)

    Returns:
        BotRestartResponse: Restart result with status information

    Raises:
        HTTPException: If restart fails
    """
    logger.info(f"Bot restart requested (timeout: {request.timeout}s)")

    try:
        # Get current state before restart
        previous_info = manager.get_status()
        previous_state = previous_info.state.value

        # Perform restart
        success = await manager.restart(
            env_vars=request.env_vars,
            timeout=request.timeout
        )

        # Get new state
        current_info = manager.get_status()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bot restart failed - see logs for details"
            )

        logger.info(f"Bot restarted successfully (PID: {current_info.pid})")

        return BotRestartResponse(
            success=True,
            message="Bot restarted successfully",
            previous_state=previous_state,
            current_state=current_info.state.value,
            pid=current_info.pid,
            restart_count=current_info.restart_count
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to restart bot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bot restart failed: {str(e)}"
        )


@router.get("/stats", response_model=BotStats)
async def get_bot_stats(manager: BotProcessManager = Depends(get_manager)) -> BotStats:
    """
    Get bot statistics.

    Returns various statistics about bot operation including:
    - Message processing metrics
    - AI provider usage
    - Performance metrics
    - Resource usage

    Note: Most statistics are placeholders and will be implemented
    when the bot is fully integrated with a metrics collection system.

    Args:
        manager: Bot process manager (injected)

    Returns:
        BotStats: Bot statistics
    """
    try:
        # Get current process info for resource usage
        process_info = manager.get_status()

        uptime_hours = 0.0
        if process_info.uptime_seconds:
            uptime_hours = process_info.uptime_seconds / 3600

        # TODO: Implement actual statistics collection
        # These are placeholder values
        return BotStats(
            total_messages_processed=0,
            total_responses_sent=0,
            ai_provider_usage={
                "anthropic": 0,
                "google": 0,
                "openai": 0
            },
            average_response_time_ms=0.0,
            uptime_hours=uptime_hours,
            memory_usage_mb=process_info.memory_mb,
            cpu_usage_percent=process_info.cpu_percent
        )

    except Exception as e:
        logger.error(f"Failed to get bot stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bot stats: {str(e)}"
        )


@router.get("/health")
async def bot_health_check(manager: BotProcessManager = Depends(get_manager)) -> Dict[str, Any]:
    """
    Health check endpoint for the bot.

    Returns basic health information about the bot process.

    Args:
        manager: Bot process manager (injected)

    Returns:
        Dict[str, Any]: Health status information
    """
    try:
        is_running = manager.is_running()
        process_info = manager.get_status()

        return {
            "healthy": is_running,
            "running": is_running,
            "state": process_info.state.value,
            "pid": process_info.pid,
            "uptime_seconds": process_info.uptime_seconds
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "healthy": False,
            "running": False,
            "state": "error",
            "error": str(e)
        }
