"""
Tests for authentication system.

These tests verify the authentication endpoints, JWT token handling,
and middleware protection.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from src.main import app
from src.api.auth import create_access_token, verify_password, get_password_hash
from src.config import get_settings


client = TestClient(app)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hash_and_verify(self):
        """Test that password hashing and verification work correctly."""
        plain_password = "test_password_123"
        hashed = get_password_hash(plain_password)

        # Hash should be different from plain password
        assert hashed != plain_password

        # Verification should succeed with correct password
        assert verify_password(plain_password, hashed) is True

        # Verification should fail with incorrect password
        assert verify_password("wrong_password", hashed) is False

    def test_same_password_different_hashes(self):
        """Test that the same password produces different hashes (salt)."""
        password = "test_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

        # Both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokenCreation:
    """Test JWT token creation and validation."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        settings = get_settings()
        data = {"sub": "testuser", "is_admin": True}

        token = create_access_token(
            data=data,
            settings=settings,
            expires_delta=timedelta(hours=1)
        )

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count('.') == 2  # JWT has 3 parts separated by dots

    def test_token_expiration(self):
        """Test that tokens have expiration set."""
        settings = get_settings()
        data = {"sub": "testuser", "is_admin": False}

        # Create token with 1-hour expiration
        token = create_access_token(
            data=data,
            settings=settings,
            expires_delta=timedelta(hours=1)
        )

        # Decode without verification to check expiration
        import jwt
        decoded = jwt.decode(token, options={"verify_signature": False})

        assert "exp" in decoded
        exp_time = datetime.fromtimestamp(decoded["exp"])
        now = datetime.utcnow()

        # Expiration should be approximately 1 hour in the future
        time_diff = exp_time - now
        assert 3500 < time_diff.total_seconds() < 3700  # ~1 hour (with small margin)


class TestAuthenticationEndpoints:
    """Test authentication API endpoints."""

    def test_health_endpoint(self):
        """Test public health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self):
        """Test public root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data

    def test_login_success(self):
        """Test successful login with correct credentials."""
        settings = get_settings()
        response = client.post(
            "/api/auth/login",
            json={
                "username": settings.admin_username,
                "password": settings.admin_password
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 86400  # 24 hours in seconds

    def test_login_invalid_username(self):
        """Test login failure with invalid username."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "invalid_user",
                "password": "any_password"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Incorrect username or password" in data["detail"]

    def test_login_invalid_password(self):
        """Test login failure with invalid password."""
        settings = get_settings()
        response = client.post(
            "/api/auth/login",
            json={
                "username": settings.admin_username,
                "password": "wrong_password"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_login_missing_credentials(self):
        """Test login failure with missing credentials."""
        response = client.post("/api/auth/login", json={})

        assert response.status_code == 422  # Validation error


class TestProtectedEndpoints:
    """Test protected endpoints and middleware."""

    def get_admin_token(self) -> str:
        """Helper method to get admin token."""
        settings = get_settings()
        response = client.post(
            "/api/auth/login",
            json={
                "username": settings.admin_username,
                "password": settings.admin_password
            }
        )
        return response.json()["access_token"]

    def test_me_endpoint_authenticated(self):
        """Test /me endpoint with valid token."""
        token = self.get_admin_token()
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "username" in data
        assert "is_admin" in data
        assert "is_active" in data
        assert data["is_admin"] is True

    def test_me_endpoint_no_token(self):
        """Test /me endpoint without token."""
        response = client.get("/api/auth/me")

        assert response.status_code == 403  # Forbidden (no token provided)

    def test_me_endpoint_invalid_token(self):
        """Test /me endpoint with invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == 401  # Unauthorized

    def test_admin_dashboard_authenticated(self):
        """Test admin dashboard with valid admin token."""
        token = self.get_admin_token()
        response = client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "user" in data
        assert "stats" in data
        assert "admin" in data["message"].lower()

    def test_admin_dashboard_no_token(self):
        """Test admin dashboard without token."""
        response = client.get("/api/admin/dashboard")

        assert response.status_code == 403  # Forbidden

    def test_logout_endpoint(self):
        """Test logout endpoint."""
        token = self.get_admin_token()
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "logged out" in data["message"].lower()


class TestTokenRefresh:
    """Test token refresh functionality."""

    def test_refresh_token_valid(self):
        """Test refreshing a valid token."""
        settings = get_settings()

        # Login to get initial token
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": settings.admin_username,
                "password": settings.admin_password
            }
        )
        old_token = login_response.json()["access_token"]

        # Refresh the token
        refresh_response = client.post(
            "/api/auth/refresh",
            params={"token": old_token}
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert data["access_token"] != old_token  # New token should be different

    def test_refresh_token_invalid(self):
        """Test refreshing with invalid token."""
        response = client.post(
            "/api/auth/refresh",
            params={"token": "invalid_token"}
        )

        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
