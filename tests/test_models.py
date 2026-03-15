"""
Comprehensive tests for authentication and user models.

Tests Pydantic models for users, authentication, tokens, etc.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.auth.models import (
    User,
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenData,
    PasswordChange,
)


class TestUser:
    """Test suite for User model."""

    def test_create_user(self):
        """Test creating a valid user."""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_pw",
        )
        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True  # Default
        assert user.is_admin is False  # Default
        assert user.must_change_password is False  # Default

    def test_user_with_custom_flags(self):
        """Test creating user with custom flags."""
        user = User(
            id=1,
            username="admin",
            email="admin@example.com",
            hashed_password="hashed_pw",
            is_admin=True,
            is_active=False,
            must_change_password=True,
        )
        assert user.is_admin is True
        assert user.is_active is False
        assert user.must_change_password is True

    def test_user_timestamps(self):
        """Test that timestamps are auto-generated."""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_pw",
        )
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)


class TestUserCreate:
    """Test suite for UserCreate model."""

    def test_create_valid_user(self):
        """Test creating valid user creation request."""
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123",
        )
        assert user_data.username == "newuser"
        assert user_data.email == "new@example.com"
        assert user_data.password == "password123"
        assert user_data.is_admin is False  # Default

    def test_create_admin_user(self):
        """Test creating admin user."""
        user_data = UserCreate(
            username="admin",
            email="admin@example.com",
            password="securepass123",
            is_admin=True,
        )
        assert user_data.is_admin is True

    def test_username_min_length(self):
        """Test username minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="ab",  # Too short (min 3)
                email="test@example.com",
                password="password123",
            )
        assert "username" in str(exc_info.value).lower()

    def test_username_max_length(self):
        """Test username maximum length validation."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="a" * 51,  # Too long (max 50)
                email="test@example.com",
                password="password123",
            )

    def test_password_min_length(self):
        """Test password minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="short",  # Too short (min 8)
            )
        assert "password" in str(exc_info.value).lower()

    def test_invalid_email(self):
        """Test email validation."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="not-an-email",
                password="password123",
            )


class TestUserLogin:
    """Test suite for UserLogin model."""

    def test_valid_login(self):
        """Test creating valid login request."""
        login = UserLogin(username="testuser", password="password123")
        assert login.username == "testuser"
        assert login.password == "password123"

    def test_empty_username(self):
        """Test that empty username is invalid."""
        with pytest.raises(ValidationError):
            UserLogin(username="", password="password123")

    def test_empty_password(self):
        """Test that empty password is invalid."""
        with pytest.raises(ValidationError):
            UserLogin(username="testuser", password="")


class TestUserResponse:
    """Test suite for UserResponse model."""

    def test_user_response(self):
        """Test creating user response (without password)."""
        now = datetime.utcnow()
        response = UserResponse(
            id=1,
            username="testuser",
            email="test@example.com",
            is_active=True,
            is_admin=False,
            must_change_password=False,
            created_at=now,
        )
        assert response.id == 1
        assert response.username == "testuser"
        # Note: hashed_password should not be in UserResponse
        assert not hasattr(response, 'hashed_password')


class TestToken:
    """Test suite for Token model."""

    def test_create_token(self):
        """Test creating token response."""
        token = Token(
            access_token="jwt_token_here",
            expires_in=3600,
        )
        assert token.access_token == "jwt_token_here"
        assert token.token_type == "bearer"  # Default
        assert token.expires_in == 3600
        assert token.must_change_password is False  # Default

    def test_token_with_password_change(self):
        """Test token with must_change_password flag."""
        token = Token(
            access_token="jwt_token_here",
            expires_in=3600,
            must_change_password=True,
        )
        assert token.must_change_password is True

    def test_custom_token_type(self):
        """Test token with custom token type."""
        token = Token(
            access_token="token",
            token_type="custom",
            expires_in=3600,
        )
        assert token.token_type == "custom"


class TestTokenData:
    """Test suite for TokenData model."""

    def test_create_token_data(self):
        """Test creating token payload data."""
        exp_time = datetime.utcnow() + timedelta(hours=1)
        token_data = TokenData(
            user_id=1,
            username="testuser",
            is_admin=False,
            exp=exp_time,
        )
        assert token_data.user_id == 1
        assert token_data.username == "testuser"
        assert token_data.is_admin is False
        assert token_data.exp == exp_time

    def test_token_data_without_expiration(self):
        """Test token data without expiration time."""
        token_data = TokenData(
            user_id=1,
            username="testuser",
            is_admin=True,
        )
        assert token_data.exp is None

    def test_admin_token_data(self):
        """Test admin token data."""
        token_data = TokenData(
            user_id=999,
            username="admin",
            is_admin=True,
        )
        assert token_data.is_admin is True


class TestPasswordChange:
    """Test suite for PasswordChange model."""

    def test_valid_password_change(self):
        """Test creating valid password change request."""
        pwd_change = PasswordChange(
            current_password="oldpassword",
            new_password="newpassword123",
        )
        assert pwd_change.current_password == "oldpassword"
        assert pwd_change.new_password == "newpassword123"

    def test_new_password_min_length(self):
        """Test new password minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PasswordChange(
                current_password="oldpassword",
                new_password="short",  # Too short (min 8)
            )
        assert "new_password" in str(exc_info.value).lower()

    def test_same_passwords(self):
        """Test that same current and new passwords are allowed (model doesn't validate this)."""
        # The model itself doesn't prevent this - business logic should
        pwd_change = PasswordChange(
            current_password="samepassword123",
            new_password="samepassword123",
        )
        assert pwd_change.current_password == pwd_change.new_password
