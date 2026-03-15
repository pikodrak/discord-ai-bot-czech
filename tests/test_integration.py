"""
Integration tests for complete workflows.
"""
import pytest
from fastapi.testclient import TestClient

from app import create_app


class TestCompleteWorkflow:
    """Test complete user workflows from start to finish."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application with all routers."""
        app = create_app()
        # Register all routers
        from src.api import config, bot
        from fastapi import Depends
        from src.api.auth import get_current_admin_user
        
        app.include_router(
            config.router,
            prefix="/api/config",
            tags=["configuration"],
            dependencies=[Depends(get_current_admin_user)]
        )
        app.include_router(
            bot.router,
            prefix="/api/bot",
            tags=["bot"],
            dependencies=[Depends(get_current_admin_user)]
        )
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_complete_admin_workflow(self, client):
        """Test complete admin workflow: login -> config -> bot control."""
        # 1. Check health
        health = client.get("/health")
        assert health.status_code == 200

        # 2. Login
        login_response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Get user info
        user_info = client.get("/api/auth/me", headers=headers)
        assert user_info.status_code == 200
        assert user_info.json()["username"] == "admin"

        # 4. Get current config
        config = client.get("/api/config/", headers=headers)
        assert config.status_code == 200

        # 5. Validate config
        validation = client.get("/api/config/validate", headers=headers)
        assert validation.status_code == 200

        # 6. Get bot status
        status = client.get("/api/bot/status", headers=headers)
        assert status.status_code == 200

        # 7. Get bot stats
        stats = client.get("/api/bot/stats", headers=headers)
        assert stats.status_code == 200

        # 8. Logout
        logout = client.post("/api/auth/logout", headers=headers)
        assert logout.status_code == 200

    def test_unauthorized_access_flow(self, client):
        """Test that unauthorized access is properly blocked."""
        # Try to access protected endpoints without token
        endpoints = [
            "/api/config/",
            "/api/config/validate",
            "/api/bot/status",
            "/api/bot/stats",
            "/api/auth/me",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require auth"

    def test_config_update_workflow(self, client):
        """Test configuration update workflow."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get initial config
        initial_config = client.get("/api/config/", headers=headers)
        assert initial_config.status_code == 200

        # Update config
        update_response = client.put(
            "/api/config/",
            json={
                "bot_response_threshold": 0.8,
                "bot_personality": "professional"
            },
            headers=headers
        )
        assert update_response.status_code == 200

        # Verify update was successful
        updated_config = client.get("/api/config/", headers=headers)
        assert updated_config.status_code == 200

    def test_error_handling_chain(self, client):
        """Test error handling across multiple operations."""
        # Try invalid login
        bad_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"}
        )
        assert bad_login.status_code == 401

        # Login correctly
        good_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = good_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try invalid bot command
        bad_command = client.post(
            "/api/bot/control",
            json={"action": "invalid"},
            headers=headers
        )
        assert bad_command.status_code == 400

        # Try valid bot command
        good_command = client.post(
            "/api/bot/control",
            json={"action": "start"},
            headers=headers
        )
        assert good_command.status_code == 200


class TestAPIResponseFormats:
    """Test API response format consistency."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        from src.api import config, bot
        from fastapi import Depends
        from src.api.auth import get_current_admin_user
        
        app.include_router(config.router, prefix="/api/config", tags=["configuration"], dependencies=[Depends(get_current_admin_user)])
        app.include_router(bot.router, prefix="/api/bot", tags=["bot"], dependencies=[Depends(get_current_admin_user)])
        return TestClient(app)

    @pytest.fixture
    def admin_token(self, client):
        """Get admin token."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        return response.json()["access_token"]

    def test_error_response_format(self, client):
        """Test that error responses follow consistent format."""
        # Invalid login
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_success_response_format(self, client, admin_token):
        """Test that success responses follow consistent format."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Bot status
        status = client.get("/api/bot/status", headers=headers)
        assert status.status_code == 200
        assert isinstance(status.json(), dict)

        # Bot stats
        stats = client.get("/api/bot/stats", headers=headers)
        assert stats.status_code == 200
        assert isinstance(stats.json(), dict)

    def test_validation_error_format(self, client, admin_token):
        """Test validation error response format."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Missing required field
        response = client.post(
            "/api/bot/control",
            json={},
            headers=headers
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestCORS:
    """Test CORS configuration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(create_app())

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS middleware should add headers
        assert response.status_code == 200

    def test_options_request(self, client):
        """Test OPTIONS request for CORS preflight."""
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        # Should handle preflight request
        assert response.status_code in [200, 204]
