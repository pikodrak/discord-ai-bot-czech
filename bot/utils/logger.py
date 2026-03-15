"""
Logging Configuration Module

This module provides centralized logging configuration for the Discord AI bot,
supporting both file and console output with configurable log levels.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    logger_name: str = "discord_bot"
) -> logging.Logger:
    """
    Set up and configure the application logger.

    This function creates a logger with both console and file handlers,
    formatted for easy reading and debugging. It ensures log directories
    exist and handles log rotation if needed.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional, defaults to logs/bot.log)
        logger_name: Name of the logger instance

    Returns:
        Configured logger instance

    Raises:
        ValueError: If log_level is invalid
    """
    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    log_level_upper = log_level.upper()
    if log_level_upper not in valid_levels:
        raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")

    # Get or create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level_upper))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level_upper))
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file is provided)
    if log_file:
        try:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Create rotating file handler
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)

        except Exception as e:
            logger.warning(f"Failed to set up file logging: {e}")

    # Set log levels for third-party libraries to reduce noise
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    # Log initial message
    logger.info(f"Logger initialized with level: {log_level_upper}")
    if log_file:
        logger.info(f"Logging to file: {log_file}")

    return logger


def get_logger(name: str = "discord_bot") -> logging.Logger:
    """
    Get an existing logger instance.

    Args:
        name: Logger name to retrieve

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
