"""
Tests for admin interface authentication functionality.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import timedelta

from app import create_app
from src.config import Settings
from src.auth.security import create_access_token, verify_password, hash_password
from src.auth.database import UserDatabase, user_db
from src.auth.models import UserCreate


class TestAdminAuthentication:
    """Test suite for authentication endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def test_settings(self):
        """Create test settings."""
        return Settings(
            admin_username="testadmin",
            admin_password="testpass123",
            secret_key="test-secret-key-for-testing-only"
        )

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "discord-ai-bot"

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_login_with_valid_credentials(self, client):
        """Test successful login with default admin credentials."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_with_invalid_credentials(self, client):
        """Test login failure with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_with_missing_fields(self, client):
        """Test login with missing required fields."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin"}
        )
        assert response.status_code == 422  # Validation error

    def test_login_with_nonexistent_user(self, client):
        """Test login with non-existent username."""
        response = client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "password"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without authentication."""
        response = client.get("/api/admin/dashboard")
        assert response.status_code == 403  # No credentials provided

    def test_protected_endpoint_with_valid_token(self, client):
        """Test accessing protected endpoint with valid token."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == "admin"

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        response = client.get(
            "/api/admin/dashboard",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401

    def test_get_current_user_info(self, client):
        """Test getting current user information."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]

        # Get user info
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["is_admin"] is True
        assert data["is_active"] is True

    def test_logout(self, client):
        """Test logout functionality."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert "message" in response.json()


class TestUserDatabase:
    """Test suite for user database operations."""

    @pytest.fixture
    def db(self):
        """Create fresh database for each test."""
        return UserDatabase()

    def test_default_admin_user_exists(self, db):
        """Test that default admin user is created."""
        admin = db.get_user_by_username("admin")
        assert admin is not None
        assert admin.username == "admin"
        assert admin.is_admin is True
        assert admin.is_active is True

    def test_create_user(self, db):
        """Test creating a new user."""
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_admin=False
        )
        user = db.create_user(user_data)
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_admin is False
        assert user.is_active is True

    def test_create_duplicate_username(self, db):
        """Test that duplicate username raises error."""
        user_data = UserCreate(
            username="admin",
            email="different@example.com",
            password="password",
            is_admin=False
        )
        with pytest.raises(ValueError, match="already exists"):
            db.create_user(user_data)

    def test_get_user_by_id(self, db):
        """Test getting user by ID."""
        admin = db.get_user_by_username("admin")
        retrieved = db.get_user_by_id(admin.id)
        assert retrieved is not None
        assert retrieved.id == admin.id

    def test_get_user_by_email(self, db):
        """Test getting user by email."""
        admin = db.get_user_by_email("admin@example.com")
        assert admin is not None
        assert admin.username == "admin"

    def test_update_user(self, db):
        """Test updating user fields."""
        admin = db.get_user_by_username("admin")
        updated = db.update_user(admin.id, is_active=False)
        assert updated is not None
        assert updated.is_active is False

    def test_delete_user(self, db):
        """Test deleting a user."""
        user_data = UserCreate(
            username="deleteme",
            email="delete@example.com",
            password="password",
            is_admin=False
        )
        user = db.create_user(user_data)
        assert db.delete_user(user.id) is True
        assert db.get_user_by_id(user.id) is None


class TestPasswordSecurity:
    """Test suite for password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """Test suite for JWT token creation and verification."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings(
            secret_key="test-secret-key-for-jwt-testing",
            admin_username="admin",
            admin_password="admin123"
        )

    def test_create_access_token(self, settings):
        """Test creating access token."""
        token = create_access_token(
            user_id=1,
            username="testuser",
            is_admin=True
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_custom_expiry(self, settings):
        """Test creating token with custom expiration."""
        token = create_access_token(
            user_id=1,
            username="testuser",
            is_admin=False,
            expires_delta=timedelta(minutes=30)
        )
        assert isinstance(token, str)

    def test_verify_valid_token(self, settings):
        """Test verifying valid token."""
        from src.auth.security import verify_token
        
        token = create_access_token(
            user_id=1,
            username="testuser",
            is_admin=True
        )
        
        token_data = verify_token(token)
        assert token_data is not None
        assert token_data.username == "testuser"
        assert token_data.is_admin is True

    def test_verify_invalid_token(self):
        """Test verifying invalid token."""
        from src.auth.security import verify_token
        
        token_data = verify_token("invalid.token.here")
        assert token_data is None


class TestAdminUserManagement:
    """Test suite for admin user management endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def admin_token(self, client):
        """Get admin token for authenticated requests."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        return response.json()["access_token"]

    def test_list_all_users(self, client, admin_token):
        """Test listing all users (admin only)."""
        response = client.get(
            "/api/auth/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 1  # At least admin user

    def test_get_user_by_id(self, client, admin_token):
        """Test getting specific user by ID."""
        response = client.get(
            "/api/auth/users/1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        user = response.json()
        assert "username" in user

    def test_create_user_as_admin(self, client, admin_token):
        """Test creating new user as admin."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "newpass123",
                "is_admin": False
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201
        user = response.json()
        assert user["username"] == "newuser"

    def test_delete_user_as_admin(self, client, admin_token):
        """Test deleting user as admin."""
        # First create a user
        create_response = client.post(
            "/api/auth/register",
            json={
                "username": "deleteme",
                "email": "delete@example.com",
                "password": "password",
                "is_admin": False
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        user_id = create_response.json()["id"]

        # Delete the user
        response = client.delete(
            f"/api/auth/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 204
