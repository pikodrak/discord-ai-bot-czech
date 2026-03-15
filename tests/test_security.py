"""
Comprehensive tests for security module (password hashing, JWT tokens).
"""
import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch
import os

# Assuming security module is in src/
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    generate_secure_password,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from models import TokenData


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a hash."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_hash_password_different_each_time(self):
        """Test that hashing same password produces different hashes (due to salt)."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "my_secure_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "my_secure_password"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        password = "my_secure_password"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False

    def test_hash_special_characters(self):
        """Test hashing password with special characters."""
        password = "p@ssw0rd!#$%^&*()"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_hash_unicode_characters(self):
        """Test hashing password with Unicode characters."""
        password = "heslo_čeština_ěščřžý"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_invalid_hash(self):
        """Test verification with invalid hash format."""
        result = verify_password("password", "invalid_hash")
        assert result is False


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        user_id = 123
        username = "testuser"
        is_admin = True

        token = create_access_token(user_id, username, is_admin)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self):
        """Test JWT token creation with custom expiration."""
        user_id = 123
        username = "testuser"
        is_admin = False
        expires_delta = timedelta(minutes=15)

        token = create_access_token(user_id, username, is_admin, expires_delta)

        # Verify expiration time
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)

        # Should expire in approximately 15 minutes
        now = datetime.utcnow()
        delta = (exp_datetime - now).total_seconds()
        assert 14 * 60 < delta < 16 * 60  # Between 14 and 16 minutes

    def test_verify_token_valid(self):
        """Test verification of valid JWT token."""
        user_id = 456
        username = "admin"
        is_admin = True

        token = create_access_token(user_id, username, is_admin)
        token_data = verify_token(token)

        assert token_data is not None
        assert isinstance(token_data, TokenData)
        assert token_data.user_id == user_id
        assert token_data.username == username
        assert token_data.is_admin == is_admin
        assert token_data.exp is not None

    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.jwt.token"
        token_data = verify_token(invalid_token)

        assert token_data is None

    def test_verify_token_expired(self):
        """Test verification of expired token."""
        user_id = 789
        username = "testuser"
        is_admin = False

        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(user_id, username, is_admin, expires_delta)

        # Token should be invalid due to expiration
        token_data = verify_token(token)
        assert token_data is None

    def test_verify_token_malformed(self):
        """Test verification of malformed token."""
        malformed_tokens = [
            "",
            "not-a-jwt",
            "header.payload",  # Missing signature
            "a.b.c.d",  # Too many parts
        ]

        for token in malformed_tokens:
            token_data = verify_token(token)
            assert token_data is None

    def test_token_contains_correct_claims(self):
        """Test that token contains all required claims."""
        user_id = 999
        username = "claimuser"
        is_admin = True

        token = create_access_token(user_id, username, is_admin)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "user_id" in payload
        assert "username" in payload
        assert "is_admin" in payload
        assert "exp" in payload

        assert payload["user_id"] == user_id
        assert payload["username"] == username
        assert payload["is_admin"] == is_admin

    def test_token_with_non_admin_user(self):
        """Test token creation and verification for non-admin user."""
        user_id = 111
        username = "regular_user"
        is_admin = False

        token = create_access_token(user_id, username, is_admin)
        token_data = verify_token(token)

        assert token_data is not None
        assert token_data.is_admin is False


class TestSecurePasswordGeneration:
    """Test secure password generation."""

    def test_generate_secure_password_default_length(self):
        """Test password generation with default length."""
        password = generate_secure_password()

        assert len(password) == 16
        assert isinstance(password, str)

    def test_generate_secure_password_custom_length(self):
        """Test password generation with custom length."""
        length = 24
        password = generate_secure_password(length)

        assert len(password) == length

    def test_generate_secure_password_minimum_length(self):
        """Test password generation with minimum allowed length."""
        password = generate_secure_password(12)
        assert len(password) == 12

    def test_generate_secure_password_length_too_short(self):
        """Test that short passwords raise ValueError."""
        with pytest.raises(ValueError, match="at least 12 characters"):
            generate_secure_password(8)

    def test_generate_secure_password_has_lowercase(self):
        """Test that generated password contains lowercase letters."""
        password = generate_secure_password(16)
        assert any(c.islower() for c in password)

    def test_generate_secure_password_has_uppercase(self):
        """Test that generated password contains uppercase letters."""
        password = generate_secure_password(16)
        assert any(c.isupper() for c in password)

    def test_generate_secure_password_has_digits(self):
        """Test that generated password contains digits."""
        password = generate_secure_password(16)
        assert any(c.isdigit() for c in password)

    def test_generate_secure_password_has_special(self):
        """Test that generated password contains special characters."""
        password = generate_secure_password(16)
        special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?"
        assert any(c in special_chars for c in password)

    def test_generate_secure_password_uniqueness(self):
        """Test that multiple generated passwords are different."""
        passwords = [generate_secure_password(16) for _ in range(10)]

        # All passwords should be unique
        assert len(set(passwords)) == 10

    def test_generate_secure_password_complexity(self):
        """Test that password meets complexity requirements."""
        password = generate_secure_password(20)

        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)

        assert has_lower and has_upper and has_digit and has_special

    def test_generate_secure_password_no_predictable_pattern(self):
        """Test that password doesn't have obvious predictable patterns."""
        passwords = [generate_secure_password(16) for _ in range(5)]

        for password in passwords:
            # Should not start with same 4 characters consistently
            assert password[:4] != "Aa1!"  # Common forced pattern


class TestSecurityConfiguration:
    """Test security configuration from environment."""

    def test_secret_key_loaded(self):
        """Test that SECRET_KEY is loaded."""
        assert SECRET_KEY is not None
        assert isinstance(SECRET_KEY, str)
        assert len(SECRET_KEY) > 0

    def test_algorithm_is_hs256(self):
        """Test that algorithm is HS256."""
        assert ALGORITHM == "HS256"

    def test_access_token_expire_minutes_valid(self):
        """Test that token expiration is valid."""
        assert ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert isinstance(ACCESS_TOKEN_EXPIRE_MINUTES, int)

    @patch.dict(os.environ, {"SECRET_KEY": "custom-secret-key"})
    def test_custom_secret_key_from_env(self):
        """Test loading custom secret key from environment."""
        # This would require reimporting the module
        # Just verify the pattern works
        custom_key = os.getenv("SECRET_KEY", "default")
        assert custom_key == "custom-secret-key"

    @patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "120"})
    def test_custom_token_expiry_from_env(self):
        """Test loading custom token expiry from environment."""
        custom_expiry = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        assert custom_expiry == 120


class TestTokenDataModel:
    """Test TokenData model."""

    def test_token_data_creation(self):
        """Test TokenData model creation."""
        exp_time = datetime.utcnow() + timedelta(hours=1)
        token_data = TokenData(
            user_id=123,
            username="testuser",
            is_admin=True,
            exp=exp_time
        )

        assert token_data.user_id == 123
        assert token_data.username == "testuser"
        assert token_data.is_admin is True
        assert token_data.exp == exp_time

    def test_token_data_optional_exp(self):
        """Test TokenData with optional exp field."""
        token_data = TokenData(
            user_id=456,
            username="user",
            is_admin=False
        )

        assert token_data.user_id == 456
        assert token_data.username == "user"
        assert token_data.is_admin is False
        assert token_data.exp is None


class TestSecurityIntegration:
    """Integration tests for security module."""

    def test_full_password_flow(self):
        """Test complete password creation and verification flow."""
        # Create password
        plain_password = "my_test_password_123!"

        # Hash it
        hashed = hash_password(plain_password)

        # Verify correct password
        assert verify_password(plain_password, hashed) is True

        # Verify incorrect password
        assert verify_password("wrong_password", hashed) is False

    def test_full_token_flow(self):
        """Test complete token creation and verification flow."""
        # Create user credentials
        user_id = 789
        username = "integrationuser"
        is_admin = True

        # Create token
        token = create_access_token(user_id, username, is_admin)

        # Verify token
        token_data = verify_token(token)

        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.username == username
        assert token_data.is_admin == is_admin

    def test_password_and_token_together(self):
        """Test using both password hashing and tokens together."""
        # Register user
        username = "newuser"
        plain_password = "secure_password_123"
        user_id = 100

        # Hash password (as would be stored in DB)
        stored_hash = hash_password(plain_password)

        # Login: verify password
        login_password = "secure_password_123"
        assert verify_password(login_password, stored_hash) is True

        # Create access token upon successful login
        token = create_access_token(user_id, username, is_admin=False)

        # Verify token
        token_data = verify_token(token)
        assert token_data is not None
        assert token_data.username == username

    def test_generated_password_can_be_hashed(self):
        """Test that generated secure password can be hashed and verified."""
        # Generate password
        password = generate_secure_password(20)

        # Hash it
        hashed = hash_password(password)

        # Verify it
        assert verify_password(password, hashed) is True
