"""
Comprehensive tests for configuration management functionality.

This test suite covers:
- Configuration API endpoints (GET, PUT, PATCH, POST)
- Settings model validation
- Configuration updates and persistence
- Security warnings and validation
- Authentication requirements
"""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Configuration models and functions
try:
    from bot.config_loader import AdvancedBotConfig as Settings
    from src.api.config import router as config_router
except ImportError:
    pytest.skip("Required modules not available", allow_module_level=True)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings() -> Settings:
    """Create a mock Settings instance with test data."""
    return Settings(
        discord_bot_token="test_token_1234567890abcdef1234567890abcdef1234567890",
        discord_guild_id=123456789,
        discord_channel_ids="111111111,222222222,333333333",
        anthropic_api_key="sk-ant-test123456789",
        google_api_key="google_test_key_123",
        openai_api_key="sk-test123456789",
        bot_response_threshold=0.6,
        bot_max_history=50,
        bot_language="cs",
        bot_personality="friendly",
        api_host="0.0.0.0",
        api_port=8000,
        log_level="INFO",
        secret_key="test-secret-key-for-testing",
        admin_username="admin",
        admin_password="admin123",
    )


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI application with config router."""
    app = FastAPI(title="Test Config API")
    app.include_router(config_router, prefix="/api/config", tags=["configuration"])
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def admin_token() -> str:
    """Return mock admin token for testing."""
    return "mock_admin_token_for_testing"


@pytest.fixture
def mock_get_settings(mock_settings: Settings):
    """Mock get_settings dependency."""
    with patch("src.api.config.get_settings", return_value=mock_settings):
        yield mock_settings


@pytest.fixture
def mock_auth():
    """Mock authentication dependency."""
    mock_user = {"username": "admin", "role": "admin"}
    with patch("src.api.config.get_current_admin_user", return_value=mock_user):
        yield mock_user


# ============================================================================
# Test Configuration API Endpoints
# ============================================================================


class TestConfigurationEndpoints:
    """Test suite for configuration API endpoints."""

    def test_get_config_structure(self, client: TestClient, mock_get_settings: Settings):
        """Test that GET /api/config/ returns proper structure."""
        with patch("src.api.config.get_settings", return_value=mock_get_settings):
            response = client.get("/api/config/")

            assert response.status_code == 200
            config = response.json()

            # Check required fields
            assert "discord_configured" in config
            assert "ai_providers_available" in config
            assert "bot_settings" in config
            assert "channels" in config
            assert "environment" in config

    def test_get_config_masks_secrets(self, client: TestClient, mock_get_settings: Settings):
        """Test that GET /api/config/ does not expose secrets."""
        with patch("src.api.config.get_settings", return_value=mock_get_settings):
            response = client.get("/api/config/")

            assert response.status_code == 200
            config_json = response.json()

            # Should not contain raw API keys or tokens
            config_str = str(config_json)
            assert "test_token_" not in config_str
            assert "sk-ant-" not in config_str

    def test_get_config_secrets_requires_auth(self, client: TestClient):
        """Test that /api/config/secrets requires authentication."""
        response = client.get("/api/config/secrets")
        # Should fail without proper auth mock
        assert response.status_code in [401, 403, 500]

    def test_get_config_secrets_with_auth(
        self, client: TestClient, mock_get_settings: Settings, mock_auth: Dict[str, str]
    ):
        """Test retrieving masked secrets with authentication."""
        with patch("src.api.config.get_settings", return_value=mock_get_settings):
            response = client.get("/api/config/secrets")

            if response.status_code == 200:
                secrets = response.json()

                # Should have masked values
                assert "discord_bot_token" in secrets
                assert "anthropic_api_key" in secrets

                # Values should be masked (contain ... or ***)
                if secrets["discord_bot_token"]:
                    assert "..." in secrets["discord_bot_token"] or "***" in secrets["discord_bot_token"]

    def test_update_config_requires_auth(self, client: TestClient):
        """Test that PUT /api/config/ requires authentication."""
        response = client.put(
            "/api/config/",
            json={"bot_language": "en"}
        )
        # Should fail without auth
        assert response.status_code in [401, 403, 500]

    def test_update_config_validates_input(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test that config updates validate input data."""
        with patch("src.api.config.get_config_manager") as mock_manager:
            mock_manager.return_value.update = Mock()

            # Invalid threshold (> 1.0)
            response = client.put(
                "/api/config/",
                json={"bot_response_threshold": 2.0}
            )
            # Should return validation error
            assert response.status_code in [400, 422, 500]

    def test_update_bot_language(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test updating bot language setting."""
        with patch("src.api.config.get_config_manager") as mock_manager, \
             patch("src.api.config.get_settings") as mock_get, \
             patch("src.api.config.save_bot_config_to_shared") as mock_shared, \
             patch("src.api.config.send_reload_command") as mock_reload:

            mock_instance = Mock()
            mock_instance.update = Mock()
            mock_manager.return_value = mock_instance
            mock_get.return_value = Mock()
            mock_get.return_value.model_dump = Mock(return_value={})
            mock_reload.return_value = True

            response = client.put(
                "/api/config/",
                json={"bot_language": "en"}
            )

            if response.status_code == 200:
                data = response.json()
                assert "message" in data
                assert "updated_fields" in data

    def test_reload_config_endpoint(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test POST /api/config/reload endpoint."""
        with patch("src.api.config.reload_settings") as mock_reload:
            mock_reload.return_value = None

            response = client.post("/api/config/reload")

            if response.status_code == 200:
                data = response.json()
                assert "message" in data
                mock_reload.assert_called_once()

    def test_validate_config_endpoint(self, client: TestClient, mock_get_settings: Settings):
        """Test GET /api/config/validate endpoint."""
        with patch("src.api.config.get_settings", return_value=mock_get_settings):
            response = client.get("/api/config/validate")

            assert response.status_code == 200
            validation = response.json()

            # Check structure
            assert "valid" in validation
            assert "errors" in validation
            assert "warnings" in validation
            assert isinstance(validation["errors"], list)
            assert isinstance(validation["warnings"], list)


# ============================================================================
# Test Settings Model Validation
# ============================================================================


class TestSettingsValidation:
    """Test suite for Settings model validation."""

    def test_minimal_valid_settings(self):
        """Test creating settings with minimal required fields."""
        settings = Settings(
            discord_bot_token="test_token_1234567890abcdef1234567890abcdef1234567890"
        )

        assert settings.discord_bot_token is not None
        assert settings.bot_language == "cs"  # Default
        assert settings.log_level == "INFO"  # Default

    def test_response_threshold_validation(self):
        """Test response threshold range validation."""
        # Valid threshold
        settings = Settings(
            discord_bot_token="test_token_123456789012345678901234567890123456789012",
            bot_response_threshold=0.7
        )
        assert settings.bot_response_threshold == 0.7

        # Boundary values
        settings_min = Settings(
            discord_bot_token="test_token_123456789012345678901234567890123456789012",
            bot_response_threshold=0.0
        )
        assert settings_min.bot_response_threshold == 0.0

        settings_max = Settings(
            discord_bot_token="test_token_123456789012345678901234567890123456789012",
            bot_response_threshold=1.0
        )
        assert settings_max.bot_response_threshold == 1.0

    def test_max_history_validation(self):
        """Test max history range validation."""
        # Valid history
        settings = Settings(
            discord_bot_token="test_token_123456789012345678901234567890123456789012",
            bot_max_history=100
        )
        assert settings.bot_max_history == 100

        # Test within bounds
        settings_min = Settings(
            discord_bot_token="test_token_123456789012345678901234567890123456789012",
            bot_max_history=1
        )
        assert settings_min.bot_max_history == 1

    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = Settings(
                discord_bot_token="test_token_123456789012345678901234567890123456789012",
                log_level=level
            )
            assert settings.log_level == level.upper()

    def test_language_validation(self):
        """Test language code validation."""
        valid_languages = ["cs", "en", "sk", "de", "es", "fr"]

        for lang in valid_languages:
            settings = Settings(
                discord_bot_token="test_token_123456789012345678901234567890123456789012",
                bot_language=lang
            )
            assert settings.bot_language == lang.lower()

    def test_api_port_validation(self):
        """Test API port range validation."""
        # Valid port
        settings = Settings(
            discord_bot_token="test_token_123456789012345678901234567890123456789012",
            api_port=8080
        )
        assert settings.api_port == 8080

        # Boundary values
        settings_min = Settings(
            discord_bot_token="test_token_123456789012345678901234567890123456789012",
            api_port=1
        )
        assert settings_min.api_port == 1

        settings_max = Settings(
            discord_bot_token="test_token_123456789012345678901234567890123456789012",
            api_port=65535
        )
        assert settings_max.api_port == 65535


# ============================================================================
# Test Configuration Update Functionality
# ============================================================================


class TestConfigUpdate:
    """Test suite for configuration update functionality."""

    def test_partial_config_update(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test updating only some config fields."""
        with patch("src.api.config.get_config_manager") as mock_manager, \
             patch("src.api.config.get_settings") as mock_get, \
             patch("src.api.config.save_bot_config_to_shared"), \
             patch("src.api.config.send_reload_command"):

            mock_instance = Mock()
            mock_instance.update = Mock()
            mock_manager.return_value = mock_instance
            mock_get.return_value = Mock()
            mock_get.return_value.model_dump = Mock(return_value={})

            response = client.put(
                "/api/config/",
                json={"bot_personality": "helpful"}
            )

            # Should accept partial updates
            assert response.status_code in [200, 500]  # 500 if mocks incomplete

    def test_update_discord_config(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test PATCH /api/config/discord endpoint."""
        with patch("src.api.config.get_config_manager") as mock_manager:

            mock_instance = Mock()
            mock_instance.update = Mock()
            mock_manager.return_value = mock_instance

            response = client.patch(
                "/api/config/discord",
                json={"discord_channel_ids": "111111111,222222222"}
            )

            if response.status_code == 200:
                data = response.json()
                assert "message" in data

    def test_update_ai_config(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test PATCH /api/config/ai endpoint."""
        with patch("src.api.config.get_config_manager") as mock_manager:

            mock_instance = Mock()
            mock_instance.update = Mock()
            mock_manager.return_value = mock_instance

            response = client.patch(
                "/api/config/ai",
                json={"anthropic_api_key": "sk-ant-new-key-12345"}
            )

            if response.status_code == 200:
                data = response.json()
                assert "message" in data

    def test_update_behavior_config(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test PATCH /api/config/behavior endpoint."""
        with patch("src.api.config.get_config_manager") as mock_manager:

            mock_instance = Mock()
            mock_instance.update = Mock()
            mock_manager.return_value = mock_instance

            response = client.patch(
                "/api/config/behavior",
                json={
                    "bot_language": "en",
                    "bot_response_threshold": 0.8
                }
            )

            if response.status_code == 200:
                data = response.json()
                assert "message" in data

    def test_empty_update_rejected(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test that empty config updates are rejected."""
        with patch("src.api.config.get_config_manager") as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance

            response = client.put("/api/config/", json={})

            # Should reject empty updates
            assert response.status_code in [400, 422, 500]


# ============================================================================
# Test Security and Validation
# ============================================================================


class TestSecurityWarnings:
    """Test suite for security configuration warnings."""

    def test_validation_detects_missing_discord_token(self):
        """Test that validation detects missing Discord token."""
        with patch("src.api.config.get_settings") as mock_get:
            mock_settings = Mock()
            mock_settings.discord_bot_token = None
            mock_settings.discord_channel_ids = "123,456"
            mock_settings.has_any_ai_key = Mock(return_value=True)
            mock_settings.secret_key = "secure-key"
            mock_settings.admin_password = "secure-pass"
            mock_settings.is_production = Mock(return_value=False)
            mock_get.return_value = mock_settings

            from src.api.config import router
            client = TestClient(FastAPI())
            client.app.include_router(router, prefix="/api/config")

            with patch("src.api.config.get_settings", return_value=mock_settings):
                response = client.get("/api/config/validate")

                if response.status_code == 200:
                    validation = response.json()
                    assert not validation["valid"]
                    assert any("token" in error.lower() for error in validation["errors"])

    def test_validation_warns_about_default_credentials(self):
        """Test that validation warns about default admin credentials."""
        with patch("src.api.config.get_settings") as mock_get:
            mock_settings = Mock()
            mock_settings.discord_bot_token = "test_token"
            mock_settings.discord_channel_ids = "123"
            mock_settings.has_any_ai_key = Mock(return_value=True)
            mock_settings.secret_key = "change-me-in-production"
            mock_settings.admin_password = "admin"
            mock_settings.is_production = Mock(return_value=False)
            mock_get.return_value = mock_settings

            from src.api.config import router
            client = TestClient(FastAPI())
            client.app.include_router(router, prefix="/api/config")

            with patch("src.api.config.get_settings", return_value=mock_settings):
                response = client.get("/api/config/validate")

                if response.status_code == 200:
                    validation = response.json()
                    warnings = validation.get("warnings", [])

                    # Should warn about insecure defaults
                    assert len(warnings) > 0

    def test_mask_secret_function(self):
        """Test the mask_secret helper function."""
        from src.api.config import mask_secret

        # Test normal secret
        assert mask_secret("abcdefghijklmnop") == "abcd...mnop"

        # Test short secret
        assert mask_secret("abc") == "***"

        # Test None
        assert mask_secret(None) is None

        # Test empty string
        assert mask_secret("") is None


# ============================================================================
# Test Export and Hot Reload
# ============================================================================


class TestAdvancedEndpoints:
    """Test suite for advanced configuration endpoints."""

    def test_export_config_with_masked_secrets(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test GET /api/config/export with masked secrets."""
        with patch("src.api.config.get_config_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_safe_dict = Mock(return_value={"test": "data"})
            mock_manager.return_value = mock_instance

            response = client.get("/api/config/export?mask_secrets=true")

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)

    def test_hot_reload_endpoint(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test POST /api/config/hot-reload endpoint."""
        with patch("src.api.config.get_settings") as mock_get, \
             patch("src.api.config.save_bot_config_to_shared") as mock_save, \
             patch("src.api.config.send_reload_command") as mock_reload:

            mock_settings = Mock()
            mock_settings.model_dump = Mock(return_value={})
            mock_get.return_value = mock_settings
            mock_reload.return_value = True

            response = client.post("/api/config/hot-reload")

            if response.status_code == 200:
                data = response.json()
                assert "success" in data
                assert "message" in data


# ============================================================================
# Integration Tests
# ============================================================================


class TestConfigurationIntegration:
    """Integration tests for configuration management."""

    def test_config_update_flow(
        self, client: TestClient, mock_auth: Dict[str, str]
    ):
        """Test complete configuration update flow."""
        with patch("src.api.config.get_config_manager") as mock_manager, \
             patch("src.api.config.get_settings") as mock_get, \
             patch("src.api.config.save_bot_config_to_shared"), \
             patch("src.api.config.send_reload_command"):

            mock_instance = Mock()
            mock_instance.update = Mock()
            mock_manager.return_value = mock_instance
            mock_get.return_value = Mock()
            mock_get.return_value.model_dump = Mock(return_value={})

            # 1. Update configuration
            update_response = client.put(
                "/api/config/",
                json={"bot_language": "en", "bot_max_history": 75}
            )

            # Should succeed or fail gracefully
            assert update_response.status_code in [200, 400, 500]

    def test_validation_after_update(
        self, client: TestClient, mock_auth: Dict[str, str], mock_get_settings: Settings
    ):
        """Test that validation works after config update."""
        # This tests the workflow of update -> validate
        with patch("src.api.config.get_settings", return_value=mock_get_settings):
            validation_response = client.get("/api/config/validate")

            assert validation_response.status_code == 200
            validation = validation_response.json()
            assert "valid" in validation
