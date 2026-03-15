"""
Tests for secure credential delivery mechanism.

This module tests the credential delivery functionality including:
- Environment variable handling (INITIAL_ADMIN_PASSWORD, ADMIN_PASSWORD)
- Auto-generated password creation
- Console logging
- File creation with proper permissions
- Security warnings
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth.database import UserDatabase
from src.auth.security import generate_secure_password


class TestCredentialDelivery:
    """Test suite for credential delivery mechanism."""

    def test_initial_admin_password_env_var(self, monkeypatch, caplog):
        """Test that INITIAL_ADMIN_PASSWORD environment variable is used."""
        # Set environment variable
        test_password = "MyTestPassword123!"
        monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", test_password)

        # Create database (triggers admin creation)
        with patch('builtins.print') as mock_print:
            db = UserDatabase()

        # Verify admin user was created
        admin = db.get_user_by_username("admin")
        assert admin is not None
        assert admin.username == "admin"
        assert admin.is_admin is True
        assert admin.must_change_password is True

        # Verify password works
        from src.auth.security import verify_password
        assert verify_password(test_password, admin.hashed_password)

        # Verify console output was called
        assert mock_print.called

        # Verify logging mentions environment variable
        assert any("INITIAL_ADMIN_PASSWORD" in record.message for record in caplog.records)

    def test_admin_password_env_var_legacy(self, monkeypatch, caplog):
        """Test that ADMIN_PASSWORD environment variable is used (legacy)."""
        # Set legacy environment variable
        test_password = "LegacyPassword456!"
        monkeypatch.setenv("ADMIN_PASSWORD", test_password)

        # Create database
        db = UserDatabase()

        # Verify admin user was created with correct password
        admin = db.get_user_by_username("admin")
        assert admin is not None

        from src.auth.security import verify_password
        assert verify_password(test_password, admin.hashed_password)

        # Verify logging mentions environment variable
        assert any("ADMIN_PASSWORD" in record.message for record in caplog.records)

    def test_initial_admin_password_takes_priority(self, monkeypatch):
        """Test that INITIAL_ADMIN_PASSWORD takes priority over ADMIN_PASSWORD."""
        # Set both environment variables
        initial_password = "InitialPassword123!"
        admin_password = "AdminPassword456!"

        monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", initial_password)
        monkeypatch.setenv("ADMIN_PASSWORD", admin_password)

        # Create database
        with patch('builtins.print'):
            db = UserDatabase()

        # Verify the INITIAL_ADMIN_PASSWORD was used (not ADMIN_PASSWORD)
        admin = db.get_user_by_username("admin")
        from src.auth.security import verify_password
        assert verify_password(initial_password, admin.hashed_password)
        assert not verify_password(admin_password, admin.hashed_password)

    def test_auto_generated_password(self, monkeypatch, tmp_path):
        """Test that password is auto-generated when no env var is set."""
        # Ensure no environment variables are set
        monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

        # Change to temp directory for file creation
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create database (should generate password)
            with patch('builtins.print') as mock_print:
                db = UserDatabase()

            # Verify admin user was created
            admin = db.get_user_by_username("admin")
            assert admin is not None
            assert admin.is_admin is True
            assert admin.must_change_password is True

            # Verify console output was called multiple times (for formatting)
            assert mock_print.call_count > 5

            # Verify credentials file was created
            credentials_file = tmp_path / ".admin_credentials"
            assert credentials_file.exists()

            # Verify file permissions on Unix-like systems
            if hasattr(os, 'chmod'):
                stat_info = credentials_file.stat()
                # Check that only owner has read/write permissions
                # 0o600 = 0o100600 (regular file with rw-------)
                assert stat_info.st_mode & 0o777 == 0o600

            # Verify file content
            content = credentials_file.read_text()
            assert "Username: admin" in content
            assert "Password:" in content
            assert "SECURITY INSTRUCTIONS" in content
            assert "DELETE THIS FILE" in content

        finally:
            os.chdir(original_cwd)

    def test_file_creation_with_proper_format(self, monkeypatch, tmp_path):
        """Test that credentials file is created with proper format and warnings."""
        monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with patch('builtins.print'):
                db = UserDatabase()

            credentials_file = tmp_path / ".admin_credentials"
            content = credentials_file.read_text()

            # Verify required sections
            assert "ADMIN CREDENTIALS" in content
            assert "Username: admin" in content
            assert "Password:" in content
            assert "Email:    admin@example.com" in content

            # Verify security instructions
            assert "SECURITY INSTRUCTIONS" in content
            assert "password manager" in content
            assert "Change the password" in content
            assert "DELETE THIS FILE" in content
            assert "version control" in content

        finally:
            os.chdir(original_cwd)

    def test_console_output_format(self, monkeypatch):
        """Test that console output has proper formatting and warnings."""
        monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

        with patch('builtins.print') as mock_print:
            db = UserDatabase()

        # Get all print calls
        print_calls = [str(call) for call in mock_print.call_args_list]
        output = "\n".join(print_calls)

        # Verify warning symbols and formatting
        assert "!" in output  # Warning symbols
        assert "=" in output  # Separator lines
        assert "Username:" in output or "admin" in output
        assert "Password:" in output
        assert "WARNING" in output or "SECURITY" in output

    def test_password_complexity(self):
        """Test that generated passwords meet complexity requirements."""
        # Generate multiple passwords and verify they all meet requirements
        for _ in range(10):
            password = generate_secure_password(length=20)

            # Length check
            assert len(password) == 20

            # Character class checks
            assert any(c.isupper() for c in password), "Should contain uppercase"
            assert any(c.islower() for c in password), "Should contain lowercase"
            assert any(c.isdigit() for c in password), "Should contain digits"
            assert any(not c.isalnum() for c in password), "Should contain special chars"

    def test_file_write_failure_fallback(self, monkeypatch, caplog):
        """Test that system falls back to console-only on file write failure."""
        monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

        # Mock file open to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Cannot write")):
            with patch('builtins.print') as mock_print:
                db = UserDatabase()

        # Verify admin was still created
        admin = db.get_user_by_username("admin")
        assert admin is not None

        # Verify error was logged
        assert any("Failed to save admin credentials" in record.message
                   for record in caplog.records)

        # Verify console output was still called
        assert mock_print.called

    def test_admin_user_properties(self, monkeypatch):
        """Test that admin user has correct properties set."""
        monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "TestPass123!")

        with patch('builtins.print'):
            db = UserDatabase()

        admin = db.get_user_by_username("admin")

        # Verify all admin properties
        assert admin.username == "admin"
        assert admin.email == "admin@example.com"
        assert admin.is_active is True
        assert admin.is_admin is True
        assert admin.must_change_password is True
        assert admin.hashed_password is not None
        assert admin.hashed_password != "TestPass123!"  # Should be hashed

    def test_no_credential_file_with_env_var(self, monkeypatch, tmp_path):
        """Test that no credentials file is created when using environment variable."""
        monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "EnvPassword123!")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with patch('builtins.print'):
                db = UserDatabase()

            # Verify credentials file was NOT created
            credentials_file = tmp_path / ".admin_credentials"
            assert not credentials_file.exists()

        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
