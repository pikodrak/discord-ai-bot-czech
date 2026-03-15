"""
Comprehensive tests for logger module.
"""
import pytest
import logging
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock

# Assuming logger is in bot/utils/
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.utils.logger import setup_logger, get_logger


class TestLoggerSetup:
    """Test logger setup and configuration."""

    def test_setup_logger_default(self):
        """Test logger setup with default parameters."""
        logger = setup_logger()

        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "discord_bot"
        assert logger.level == logging.INFO

    def test_setup_logger_custom_name(self):
        """Test logger setup with custom name."""
        logger = setup_logger(logger_name="custom_logger")

        assert logger.name == "custom_logger"

    def test_setup_logger_debug_level(self):
        """Test logger setup with DEBUG level."""
        logger = setup_logger(log_level="DEBUG")

        assert logger.level == logging.DEBUG

    def test_setup_logger_warning_level(self):
        """Test logger setup with WARNING level."""
        logger = setup_logger(log_level="WARNING")

        assert logger.level == logging.WARNING

    def test_setup_logger_error_level(self):
        """Test logger setup with ERROR level."""
        logger = setup_logger(log_level="ERROR")

        assert logger.level == logging.ERROR

    def test_setup_logger_critical_level(self):
        """Test logger setup with CRITICAL level."""
        logger = setup_logger(log_level="CRITICAL")

        assert logger.level == logging.CRITICAL

    def test_setup_logger_case_insensitive(self):
        """Test that log level is case insensitive."""
        logger_lower = setup_logger(log_level="info", logger_name="test1")
        logger_upper = setup_logger(log_level="INFO", logger_name="test2")
        logger_mixed = setup_logger(log_level="InFo", logger_name="test3")

        assert logger_lower.level == logging.INFO
        assert logger_upper.level == logging.INFO
        assert logger_mixed.level == logging.INFO

    def test_setup_logger_invalid_level(self):
        """Test that invalid log level raises ValueError."""
        with pytest.raises(ValueError, match="Log level must be one of"):
            setup_logger(log_level="INVALID")

    def test_setup_logger_with_file(self):
        """Test logger setup with file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            logger = setup_logger(log_file=log_file, logger_name="file_logger")

            # Log a message
            logger.info("Test message")

            # Check file exists
            assert os.path.exists(log_file)

            # Check content
            with open(log_file, "r") as f:
                content = f.read()
                assert "Test message" in content

    def test_setup_logger_creates_log_directory(self):
        """Test that logger creates log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "subdir", "nested", "test.log")
            logger = setup_logger(log_file=log_file, logger_name="nested_logger")

            # Log a message
            logger.info("Test message")

            # Check directory and file were created
            assert os.path.exists(os.path.dirname(log_file))
            assert os.path.exists(log_file)

    def test_setup_logger_handlers_cleared(self):
        """Test that existing handlers are cleared."""
        logger_name = "handler_test"

        # First setup
        logger1 = setup_logger(logger_name=logger_name)
        initial_handler_count = len(logger1.handlers)

        # Second setup (should clear previous handlers)
        logger2 = setup_logger(logger_name=logger_name)
        final_handler_count = len(logger2.handlers)

        # Should have same number of handlers (old ones cleared)
        assert final_handler_count == initial_handler_count

    def test_setup_logger_console_handler(self):
        """Test that console handler is added."""
        logger = setup_logger(logger_name="console_test")

        # Check that at least one StreamHandler exists
        stream_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
        ]
        assert len(stream_handlers) >= 1

    def test_setup_logger_file_handler_rotation(self):
        """Test that file handler uses rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "rotating.log")
            logger = setup_logger(log_file=log_file, logger_name="rotating_logger")

            # Check that RotatingFileHandler exists
            from logging.handlers import RotatingFileHandler
            rotating_handlers = [
                h for h in logger.handlers
                if isinstance(h, RotatingFileHandler)
            ]
            assert len(rotating_handlers) == 1

            handler = rotating_handlers[0]
            assert handler.maxBytes == 10 * 1024 * 1024  # 10 MB
            assert handler.backupCount == 5


class TestLoggerFormatting:
    """Test logger formatting."""

    def test_console_formatter(self):
        """Test console log formatter."""
        logger = setup_logger(logger_name="format_test")

        # Get console handler
        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) >= 1

        formatter = console_handlers[0].formatter
        assert formatter is not None

        # Check format string contains expected elements
        format_string = formatter._fmt
        assert "%(asctime)s" in format_string
        assert "%(levelname)" in format_string
        assert "%(message)s" in format_string

    def test_file_formatter_detailed(self):
        """Test that file formatter is more detailed than console."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "detail.log")
            logger = setup_logger(log_file=log_file, logger_name="detail_logger")

            # Get file handler
            from logging.handlers import RotatingFileHandler
            file_handlers = [
                h for h in logger.handlers
                if isinstance(h, RotatingFileHandler)
            ]
            assert len(file_handlers) == 1

            formatter = file_handlers[0].formatter
            format_string = formatter._fmt

            # File format should include function name and line number
            assert "%(funcName)s" in format_string
            assert "%(lineno)d" in format_string


class TestLoggerLevels:
    """Test logging at different levels."""

    def test_logger_debug_messages(self):
        """Test DEBUG level messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "debug.log")
            logger = setup_logger(log_level="DEBUG", log_file=log_file, logger_name="debug_test")

            logger.debug("Debug message")

            with open(log_file, "r") as f:
                content = f.read()
                assert "Debug message" in content

    def test_logger_info_messages(self):
        """Test INFO level messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "info.log")
            logger = setup_logger(log_level="INFO", log_file=log_file, logger_name="info_test")

            logger.info("Info message")

            with open(log_file, "r") as f:
                content = f.read()
                assert "Info message" in content

    def test_logger_warning_messages(self):
        """Test WARNING level messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "warning.log")
            logger = setup_logger(log_level="WARNING", log_file=log_file, logger_name="warning_test")

            logger.warning("Warning message")

            with open(log_file, "r") as f:
                content = f.read()
                assert "Warning message" in content

    def test_logger_filters_lower_levels(self):
        """Test that logger filters messages below its level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "filter.log")
            logger = setup_logger(log_level="ERROR", log_file=log_file, logger_name="filter_test")

            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            with open(log_file, "r") as f:
                content = f.read()
                assert "Debug message" not in content
                assert "Info message" not in content
                assert "Warning message" not in content
                assert "Error message" in content


class TestThirdPartyLoggers:
    """Test that third-party logger levels are set correctly."""

    def test_discord_logger_level(self):
        """Test that discord logger level is set to WARNING."""
        setup_logger(logger_name="main_logger")

        discord_logger = logging.getLogger("discord")
        assert discord_logger.level == logging.WARNING

    def test_aiohttp_logger_level(self):
        """Test that aiohttp logger level is set to WARNING."""
        setup_logger(logger_name="main_logger")

        aiohttp_logger = logging.getLogger("aiohttp")
        assert aiohttp_logger.level == logging.WARNING

    def test_anthropic_logger_level(self):
        """Test that anthropic logger level is set to WARNING."""
        setup_logger(logger_name="main_logger")

        anthropic_logger = logging.getLogger("anthropic")
        assert anthropic_logger.level == logging.WARNING

    def test_openai_logger_level(self):
        """Test that openai logger level is set to WARNING."""
        setup_logger(logger_name="main_logger")

        openai_logger = logging.getLogger("openai")
        assert openai_logger.level == logging.WARNING


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_default(self):
        """Test getting logger with default name."""
        logger = get_logger()

        assert logger is not None
        assert logger.name == "discord_bot"

    def test_get_logger_custom_name(self):
        """Test getting logger with custom name."""
        logger = get_logger("custom_name")

        assert logger.name == "custom_name"

    def test_get_logger_returns_existing(self):
        """Test that get_logger returns existing logger instance."""
        setup_logger(logger_name="existing_logger")
        logger1 = get_logger("existing_logger")
        logger2 = get_logger("existing_logger")

        assert logger1 is logger2


class TestLoggerInitialization:
    """Test logger initialization messages."""

    def test_initialization_message_logged(self):
        """Test that initialization message is logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "init.log")
            logger = setup_logger(log_level="INFO", log_file=log_file, logger_name="init_test")

            with open(log_file, "r") as f:
                content = f.read()
                assert "Logger initialized with level" in content
                assert "INFO" in content

    def test_log_file_message(self):
        """Test that log file path is logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "path.log")
            logger = setup_logger(log_file=log_file, logger_name="path_test")

            with open(log_file, "r") as f:
                content = f.read()
                assert "Logging to file" in content


class TestLoggerErrorHandling:
    """Test logger error handling."""

    def test_setup_logger_file_permission_error(self):
        """Test logger behavior when file cannot be created."""
        # Try to write to a read-only location (if possible)
        with patch("bot.utils.logger.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = PermissionError("Permission denied")

            # Should not raise, just warn
            logger = setup_logger(log_file="/root/test.log", logger_name="permission_test")

            assert logger is not None

    def test_setup_logger_continues_without_file_on_error(self):
        """Test that logger continues with console only if file fails."""
        with patch("bot.utils.logger.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = Exception("File error")

            logger = setup_logger(log_file="/invalid/path.log", logger_name="error_test")

            # Should still have console handler
            assert len(logger.handlers) >= 1


class TestLoggerEncoding:
    """Test logger encoding support."""

    def test_utf8_encoding(self):
        """Test that logger handles UTF-8 characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "utf8.log")
            logger = setup_logger(log_file=log_file, logger_name="utf8_test")

            # Log message with Czech characters
            logger.info("Testovací zpráva s češtinou: ěščřžýáíé")

            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert "Testovací zpráva s češtinou: ěščřžýáíé" in content

    def test_special_characters(self):
        """Test that logger handles special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "special.log")
            logger = setup_logger(log_file=log_file, logger_name="special_test")

            logger.info("Special chars: !@#$%^&*()_+-=[]{}|;:,.<>?")

            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert "Special chars: !@#$%^&*()_+-=[]{}|;:,.<>?" in content


class TestLoggerMultipleInstances:
    """Test multiple logger instances."""

    def test_multiple_loggers_independent(self):
        """Test that multiple loggers are independent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file1 = os.path.join(tmpdir, "logger1.log")
            log_file2 = os.path.join(tmpdir, "logger2.log")

            logger1 = setup_logger(log_level="DEBUG", log_file=log_file1, logger_name="logger1")
            logger2 = setup_logger(log_level="ERROR", log_file=log_file2, logger_name="logger2")

            logger1.debug("Debug from logger1")
            logger2.error("Error from logger2")

            with open(log_file1, "r") as f:
                content1 = f.read()
                assert "Debug from logger1" in content1
                assert "Error from logger2" not in content1

            with open(log_file2, "r") as f:
                content2 = f.read()
                assert "Error from logger2" in content2
                assert "Debug from logger1" not in content2
