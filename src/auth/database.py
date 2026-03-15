"""
Database layer for user management.
In-memory implementation for now - should be replaced with actual database.
"""
from datetime import datetime
from typing import Dict, List, Optional
import os
import logging
from pathlib import Path
from src.auth.models import User, UserCreate
from src.auth.security import hash_password, generate_secure_password

logger = logging.getLogger(__name__)


class UserDatabase:
    """In-memory user database (replace with real DB in production)."""

    def __init__(self):
        """Initialize the database with an admin user."""
        self._users: Dict[int, User] = {}
        self._next_id: int = 1
        self._username_index: Dict[str, int] = {}
        self._email_index: Dict[str, int] = {}

        # Create default admin user
        self._create_default_admin()

    def _log_credentials_to_console(
        self,
        username: str,
        password: str,
        from_env: bool = False
    ) -> None:
        """
        Log credentials to console with prominent warning.

        Args:
            username: Username
            password: Plain text password
            from_env: Whether password came from environment variable
        """
        separator = "=" * 80
        warning_line = "!" * 80

        # Log to console with prominent formatting
        print("\n" + warning_line)
        print(separator)
        if from_env:
            print("  ADMIN CREDENTIALS (from environment variable)")
        else:
            print("  ADMIN CREDENTIALS - FIRST STARTUP")
        print(separator)
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"  Email:    admin@example.com")
        print(separator)
        print("  ⚠️  SECURITY WARNING:")
        print("  - Save these credentials in a secure password manager NOW")
        print("  - Change this password immediately after first login")
        print("  - Delete the .admin_credentials file after saving")
        print("  - Never commit credentials to version control")
        print(separator)
        print(warning_line + "\n")

        # Also log through logger for audit trail
        logger.warning(
            f"Admin credentials displayed on console. "
            f"Username: {username}, Password source: "
            f"{'environment variable' if from_env else 'randomly generated'}"
        )

    def _save_credentials_to_file(
        self,
        username: str,
        password: str,
        email: str
    ) -> None:
        """
        Save credentials to a secure file with restricted permissions.

        Args:
            username: Username
            password: Plain text password
            email: Email address
        """
        credentials_file = Path(".admin_credentials")

        try:
            # Write credentials file
            with credentials_file.open("w") as f:
                f.write("=" * 80 + "\n")
                f.write("ADMIN CREDENTIALS - KEEP THIS FILE SECURE\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Username: {username}\n")
                f.write(f"Password: {password}\n")
                f.write(f"Email:    {email}\n\n")
                f.write("=" * 80 + "\n")
                f.write("⚠️  SECURITY INSTRUCTIONS:\n")
                f.write("=" * 80 + "\n\n")
                f.write("1. Save these credentials in a secure password manager\n")
                f.write("2. Log in to the admin interface\n")
                f.write("3. Change the password immediately\n")
                f.write("4. DELETE THIS FILE after securing credentials\n")
                f.write("5. Never commit this file to version control\n\n")
                f.write("=" * 80 + "\n")

            # Set restrictive permissions (Unix-like systems only)
            try:
                credentials_file.chmod(0o600)  # rw------- (owner only)
                logger.info(f"Set file permissions to 0600 for {credentials_file}")
            except Exception as e:
                logger.warning(
                    f"Could not set file permissions (may be on Windows): {e}"
                )

            logger.warning(
                f"Admin credentials saved to {credentials_file.absolute()}. "
                f"Please retrieve and DELETE this file after securing the password."
            )

        except Exception as e:
            logger.error(f"Failed to save admin credentials to file: {e}")
            logger.critical(
                f"CRITICAL: Could not write credentials file. "
                f"Password must be saved from console output: {password}"
            )

    def _create_default_admin(self) -> None:
        """
        Create a default admin user for initial access.

        Uses one of the following methods (in order of priority):
        1. INITIAL_ADMIN_PASSWORD environment variable (for automated deployments)
        2. ADMIN_PASSWORD environment variable (legacy support)
        3. Generate a secure random password and save to .admin_credentials file

        The password is logged securely to allow the administrator to access the system.
        """
        # Try to get password from environment variables
        # INITIAL_ADMIN_PASSWORD takes priority for automated deployments
        admin_password = os.getenv("INITIAL_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")

        if admin_password:
            if os.getenv("INITIAL_ADMIN_PASSWORD"):
                password_source = "INITIAL_ADMIN_PASSWORD environment variable"
            else:
                password_source = "ADMIN_PASSWORD environment variable"

            logger.info(f"Using admin password from {password_source}")

            # For automated deployments, still log the password for verification
            if os.getenv("INITIAL_ADMIN_PASSWORD"):
                self._log_credentials_to_console("admin", admin_password, from_env=True)
        else:
            # Generate a secure random password
            admin_password = generate_secure_password(length=20)
            password_source = "randomly generated"

            # Log credentials to console with prominent warning
            self._log_credentials_to_console("admin", admin_password, from_env=False)

            # Save credentials to a secure file
            self._save_credentials_to_file("admin", admin_password, "admin@example.com")

        admin = User(
            id=self._next_id,
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password(admin_password),
            is_active=True,
            is_admin=True,
            must_change_password=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self._users[admin.id] = admin
        self._username_index[admin.username] = admin.id
        self._email_index[admin.email] = admin.id
        self._next_id += 1

        logger.info(f"Default admin user created (password from {password_source})")

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user

        Raises:
            ValueError: If username or email already exists
        """
        if user_data.username in self._username_index:
            raise ValueError(f"Username '{user_data.username}' already exists")

        if user_data.email in self._email_index:
            raise ValueError(f"Email '{user_data.email}' already exists")

        user = User(
            id=self._next_id,
            username=user_data.username,
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            is_active=True,
            is_admin=user_data.is_admin,
            must_change_password=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self._users[user.id] = user
        self._username_index[user.username] = user.id
        self._email_index[user.email] = user.id
        self._next_id += 1

        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User's ID

        Returns:
            User if found, None otherwise
        """
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username: Username to search for

        Returns:
            User if found, None otherwise
        """
        user_id = self._username_index.get(username)
        if user_id is None:
            return None
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: Email to search for

        Returns:
            User if found, None otherwise
        """
        user_id = self._email_index.get(email)
        if user_id is None:
            return None
        return self._users.get(user_id)

    def get_all_users(self) -> List[User]:
        """
        Get all users.

        Returns:
            List of all users
        """
        return list(self._users.values())

    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """
        Update user fields.

        Args:
            user_id: User's ID
            **kwargs: Fields to update

        Returns:
            Updated user if found, None otherwise
        """
        user = self._users.get(user_id)
        if user is None:
            return None

        # Update allowed fields
        allowed_fields = {'is_active', 'is_admin', 'email', 'must_change_password', 'hashed_password'}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        return user

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.

        Args:
            user_id: User's ID

        Returns:
            True if deleted, False if not found
        """
        user = self._users.get(user_id)
        if user is None:
            return False

        del self._username_index[user.username]
        del self._email_index[user.email]
        del self._users[user_id]
        return True


# Global database instance
user_db = UserDatabase()
