"""
Tests for bot control and monitoring endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app import create_app


class TestBotStatus:
    """Test suite for bot status endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        # Register bot router
        from src.api import bot
        from fastapi import Depends
        from src.api.auth import get_current_admin_user
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

    def test_get_bot_status_requires_auth(self, client):
        """Test that bot status endpoint requires authentication."""
        response = client.get("/api/bot/status")
        assert response.status_code in [401, 403]

    def test_get_bot_status(self, client, admin_token):
        """Test getting bot status."""
        response = client.get(
            "/api/bot/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        status = response.json()
        assert "running" in status
        assert "connected" in status
        assert "guild_name" in status
        assert "active_channels" in status
        assert "uptime_seconds" in status
        assert isinstance(status["active_channels"], list)

    def test_get_bot_stats(self, client, admin_token):
        """Test getting bot statistics."""
        response = client.get(
            "/api/bot/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        stats = response.json()
        assert "total_messages_processed" in stats
        assert "total_responses_sent" in stats
        assert "ai_provider_usage" in stats
        assert "anthropic" in stats["ai_provider_usage"]
        assert "google" in stats["ai_provider_usage"]
        assert "openai" in stats["ai_provider_usage"]


class TestBotControl:
    """Test suite for bot control operations."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        from src.api import bot
        from fastapi import Depends
        from src.api.auth import get_current_admin_user
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

    def test_control_bot_requires_auth(self, client):
        """Test that control endpoint requires authentication."""
        response = client.post(
            "/api/bot/control",
            json={"action": "start"}
        )
        assert response.status_code in [401, 403]

    def test_start_bot_command(self, client, admin_token):
        """Test start bot command."""
        response = client.post(
            "/api/bot/control",
            json={"action": "start"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["action"] == "start"

    def test_stop_bot_command(self, client, admin_token):
        """Test stop bot command."""
        response = client.post(
            "/api/bot/control",
            json={"action": "stop"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "stop"

    def test_restart_bot_command(self, client, admin_token):
        """Test restart bot command."""
        response = client.post(
            "/api/bot/control",
            json={"action": "restart"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "restart"

    def test_invalid_bot_command(self, client, admin_token):
        """Test invalid bot command."""
        response = client.post(
            "/api/bot/control",
            json={"action": "invalid_action"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_missing_action_field(self, client, admin_token):
        """Test control request with missing action field."""
        response = client.post(
            "/api/bot/control",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 422  # Validation error


class TestEndpointIntegration:
    """Test suite for integrated endpoint workflows."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        from src.api import bot
        from fastapi import Depends
        from src.api.auth import get_current_admin_user
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

    def test_check_status_after_control_command(self, client, admin_token):
        """Test checking status after sending control command."""
        # Send control command
        control_response = client.post(
            "/api/bot/control",
            json={"action": "start"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert control_response.status_code == 200

        # Check status
        status_response = client.get(
            "/api/bot/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert status_response.status_code == 200
        # Status should be queryable after command

    def test_get_stats_returns_valid_structure(self, client, admin_token):
        """Test that stats endpoint returns valid data structure."""
        response = client.get(
            "/api/bot/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        stats = response.json()
        
        # Validate structure
        assert isinstance(stats["total_messages_processed"], int)
        assert isinstance(stats["total_responses_sent"], int)
        assert isinstance(stats["ai_provider_usage"], dict)
        assert isinstance(stats["average_response_time_ms"], (int, float))
        assert isinstance(stats["uptime_hours"], (int, float))
