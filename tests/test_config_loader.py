"""
Comprehensive tests for config_loader module.
"""
import pytest
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, Mock
from pydantic import ValidationError

# Assuming config_loader is in bot/
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config_loader import (
    Environment,
    ConfigValidationError,
    AdvancedBotConfig,
    ConfigLoader,
    load_config,
)


class TestEnvironmentEnum:
    """Test Environment enum."""

    def test_environment_values(self):
        """Test that all environment values are defined."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTING.value == "testing"

    def test_environment_iteration(self):
        """Test iterating over environments."""
        envs = list(Environment)
        assert len(envs) == 4
        assert Environment.DEVELOPMENT in envs


class TestConfigValidationError:
    """Test ConfigValidationError exception."""

    def test_validation_error_creation(self):
        """Test creating validation error."""
        error = ConfigValidationError("Test error")
        assert str(error) == "Test error"
        assert error.errors == []

    def test_validation_error_with_errors(self):
        """Test creating validation error with error list."""
        errors = [{"field": "test", "message": "invalid"}]
        error = ConfigValidationError("Validation failed", errors)
        assert error.errors == errors


class TestAdvancedBotConfig:
    """Test AdvancedBotConfig class."""

    def test_default_config(self):
        """Test config with minimal required fields."""
        config = AdvancedBotConfig(discord_bot_token="test_token")

        assert config.discord_bot_token == "test_token"
        assert config.environment == Environment.DEVELOPMENT
        assert config.bot_response_threshold == 0.6
        assert config.bot_max_history == 50
        assert config.bot_language == "cs"
        assert config.log_level == "INFO"

    def test_custom_config(self):
        """Test config with custom values."""
        config = AdvancedBotConfig(
            discord_bot_token="custom_token",
            environment="production",
            bot_language="en",
            log_level="DEBUG",
            max_retry_attempts=5,
        )

        assert config.discord_bot_token == "custom_token"
        assert config.environment == Environment.PRODUCTION
        assert config.bot_language == "en"
        assert config.log_level == "DEBUG"
        assert config.max_retry_attempts == 5

    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = AdvancedBotConfig(discord_bot_token="token", log_level=level)
            assert config.log_level == level.upper()

        # Invalid level
        with pytest.raises(ValidationError):
            AdvancedBotConfig(discord_bot_token="token", log_level="INVALID")

    def test_log_level_case_insensitive(self):
        """Test that log level is case insensitive."""
        config = AdvancedBotConfig(discord_bot_token="token", log_level="debug")
        assert config.log_level == "DEBUG"

    def test_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "staging", "production", "testing"]:
            config = AdvancedBotConfig(discord_bot_token="token", environment=env)
            assert config.environment.value == env

        # Invalid environment
        with pytest.raises(ValidationError):
            AdvancedBotConfig(discord_bot_token="token", environment="invalid")

    def test_language_validation(self):
        """Test language validation."""
        # Valid languages
        for lang in ["cs", "en", "sk", "de", "es", "fr"]:
            config = AdvancedBotConfig(discord_bot_token="token", bot_language=lang)
            assert config.bot_language == lang

        # Invalid language
        with pytest.raises(ValidationError):
            AdvancedBotConfig(discord_bot_token="token", bot_language="invalid")

    def test_numeric_field_validation(self):
        """Test numeric field validations."""
        # bot_response_threshold must be 0.0 to 1.0
        with pytest.raises(ValidationError):
            AdvancedBotConfig(discord_bot_token="token", bot_response_threshold=1.5)

        with pytest.raises(ValidationError):
            AdvancedBotConfig(discord_bot_token="token", bot_response_threshold=-0.1)

        # Valid value
        config = AdvancedBotConfig(discord_bot_token="token", bot_response_threshold=0.8)
        assert config.bot_response_threshold == 0.8

    def test_retry_config_validation(self):
        """Test retry configuration validation."""
        # max_retry_attempts: 1 to 10
        with pytest.raises(ValidationError):
            AdvancedBotConfig(discord_bot_token="token", max_retry_attempts=0)

        with pytest.raises(ValidationError):
            AdvancedBotConfig(discord_bot_token="token", max_retry_attempts=11)

        config = AdvancedBotConfig(discord_bot_token="token", max_retry_attempts=5)
        assert config.max_retry_attempts == 5

    def test_timeout_config_validation(self):
        """Test timeout configuration validation."""
        # http_timeout: 1.0 to 300.0
        with pytest.raises(ValidationError):
            AdvancedBotConfig(discord_bot_token="token", http_timeout=0.5)

        config = AdvancedBotConfig(discord_bot_token="token", http_timeout=15.0)
        assert config.http_timeout == 15.0

    def test_production_secret_key_validation(self):
        """Test that production requires custom secret key."""
        with pytest.raises(ValueError, match="SECRET_KEY must be changed"):
            AdvancedBotConfig(
                discord_bot_token="token",
                environment="production",
                secret_key="dev-secret-key-change-in-production"
            )

    def test_production_admin_password_validation(self):
        """Test that production requires custom admin password."""
        with pytest.raises(ValueError, match="ADMIN_PASSWORD must be changed"):
            AdvancedBotConfig(
                discord_bot_token="token",
                environment="production",
                secret_key="custom-secret",
                admin_password="admin"
            )

    def test_get_channel_ids(self):
        """Test parsing channel IDs."""
        config = AdvancedBotConfig(
            discord_bot_token="token",
            discord_channel_ids="123456789, 987654321, 111222333"
        )

        channel_ids = config.get_channel_ids()
        assert channel_ids == [123456789, 987654321, 111222333]

    def test_get_channel_ids_empty(self):
        """Test parsing empty channel IDs."""
        config = AdvancedBotConfig(discord_bot_token="token")
        channel_ids = config.get_channel_ids()
        assert channel_ids == []

    def test_get_channel_ids_invalid(self):
        """Test parsing channel IDs with invalid values."""
        config = AdvancedBotConfig(
            discord_bot_token="token",
            discord_channel_ids="123456789, invalid, 987654321"
        )

        channel_ids = config.get_channel_ids()
        # Should skip invalid and keep valid ones
        assert 123456789 in channel_ids
        assert 987654321 in channel_ids
        assert len(channel_ids) == 2

    def test_has_any_ai_key(self):
        """Test checking for any AI key."""
        config1 = AdvancedBotConfig(discord_bot_token="token")
        assert config1.has_any_ai_key() is False

        config2 = AdvancedBotConfig(
            discord_bot_token="token",
            anthropic_api_key="test_key"
        )
        assert config2.has_any_ai_key() is True

    def test_has_ai_provider(self):
        """Test checking specific AI provider."""
        config = AdvancedBotConfig(
            discord_bot_token="token",
            anthropic_api_key="claude_key",
            google_api_key="gemini_key"
        )

        assert config.has_ai_provider("anthropic") is True
        assert config.has_ai_provider("google") is True
        assert config.has_ai_provider("openai") is False

    def test_get_available_providers(self):
        """Test getting list of available providers."""
        config = AdvancedBotConfig(
            discord_bot_token="token",
            anthropic_api_key="claude_key",
            openai_api_key="openai_key"
        )

        providers = config.get_available_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "google" not in providers

    def test_is_production(self):
        """Test production environment check."""
        config1 = AdvancedBotConfig(discord_bot_token="token", environment="development")
        assert config1.is_production() is False

        config2 = AdvancedBotConfig(
            discord_bot_token="token",
            environment="production",
            secret_key="custom",
            admin_password="custom"
        )
        assert config2.is_production() is True

    def test_is_development(self):
        """Test development environment check."""
        config = AdvancedBotConfig(discord_bot_token="token", environment="development")
        assert config.is_development() is True

    def test_to_dict_without_secrets(self):
        """Test converting config to dict without secrets."""
        config = AdvancedBotConfig(
            discord_bot_token="secret_token",
            anthropic_api_key="secret_key",
            secret_key="secret"
        )

        config_dict = config.to_dict(include_secrets=False)

        assert config_dict["discord_bot_token"] == "***REDACTED***"
        assert config_dict["anthropic_api_key"] == "***REDACTED***"
        assert config_dict["secret_key"] == "***REDACTED***"

    def test_to_dict_with_secrets(self):
        """Test converting config to dict with secrets."""
        config = AdvancedBotConfig(
            discord_bot_token="secret_token",
            anthropic_api_key="secret_key"
        )

        config_dict = config.to_dict(include_secrets=True)

        assert config_dict["discord_bot_token"] == "secret_token"
        assert config_dict["anthropic_api_key"] == "secret_key"

    def test_repr(self):
        """Test string representation."""
        config = AdvancedBotConfig(
            discord_bot_token="token",
            environment="development",
            bot_language="cs"
        )

        repr_str = repr(config)
        assert "AdvancedBotConfig" in repr_str
        assert "development" in repr_str
        assert "cs" in repr_str


class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_config_loader_initialization(self):
        """Test ConfigLoader initialization."""
        loader = ConfigLoader()
        assert loader.config_dir == Path.cwd()

    def test_config_loader_custom_dir(self):
        """Test ConfigLoader with custom directory."""
        custom_dir = Path("/tmp/config")
        loader = ConfigLoader(config_dir=custom_dir)
        assert loader.config_dir == custom_dir

    def test_load_config_minimal(self):
        """Test loading minimal config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .env file
            env_file = os.path.join(tmpdir, ".env")
            with open(env_file, "w") as f:
                f.write("DISCORD_BOT_TOKEN=test_token\n")

            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token"}, clear=True):
                loader = ConfigLoader(config_dir=Path(tmpdir))
                config = loader.load()

                assert config.discord_bot_token == "test_token"

    def test_load_config_with_yaml(self):
        """Test loading config with YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create YAML config
            yaml_file = os.path.join(tmpdir, "config.development.yaml")
            yaml_data = {
                "bot_language": "en",
                "bot_max_history": 100,
                "log_level": "DEBUG",
            }
            with open(yaml_file, "w") as f:
                yaml.dump(yaml_data, f)

            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "ENVIRONMENT": "development"}):
                loader = ConfigLoader(config_dir=Path(tmpdir))
                config = loader.load()

                assert config.bot_language == "en"
                assert config.bot_max_history == 100
                assert config.log_level == "DEBUG"

    def test_load_config_yaml_not_found(self):
        """Test loading config when YAML file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}):
                loader = ConfigLoader(config_dir=Path(tmpdir))
                config = loader.load()

                # Should still work with defaults
                assert config.discord_bot_token == "token"

    def test_load_config_invalid_yaml(self):
        """Test loading config with invalid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid YAML
            yaml_file = os.path.join(tmpdir, "config.development.yaml")
            with open(yaml_file, "w") as f:
                f.write("invalid: yaml: content:\n  - broken")

            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "ENVIRONMENT": "development"}):
                loader = ConfigLoader(config_dir=Path(tmpdir))
                # Should handle gracefully
                config = loader.load()
                assert config is not None

    def test_reload_config(self):
        """Test reloading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}):
                loader = ConfigLoader(config_dir=Path(tmpdir))
                config1 = loader.load()
                config2 = loader.reload()

                assert config2 is not None

    def test_get_config(self):
        """Test getting current config."""
        loader = ConfigLoader()
        assert loader.get_config() is None

        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}):
            loader.load()
            config = loader.get_config()
            assert config is not None


class TestLoadConfigFunction:
    """Test load_config convenience function."""

    def test_load_config_function(self):
        """Test load_config convenience function."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token"}):
            config = load_config()
            assert config.discord_bot_token == "test_token"

    def test_load_config_with_env_file(self):
        """Test load_config with env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = os.path.join(tmpdir, "custom.env")
            with open(env_file, "w") as f:
                f.write("DISCORD_BOT_TOKEN=custom_token\n")

            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "custom_token"}):
                config = load_config(env_file=env_file)
                assert config.discord_bot_token == "custom_token"


class TestConfigDirectoryCreation:
    """Test automatic directory creation."""

    def test_log_directory_created(self):
        """Test that log directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "logs", "test.log")

            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}):
                config = AdvancedBotConfig(
                    discord_bot_token="token",
                    log_file=log_file
                )

                log_dir = Path(log_file).parent
                assert log_dir.exists()

    def test_database_directory_created(self):
        """Test that database directory is created for SQLite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "data", "bot.db")
            db_url = f"sqlite:///{db_path}"

            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}):
                config = AdvancedBotConfig(
                    discord_bot_token="token",
                    database_url=db_url
                )

                db_dir = Path(db_path).parent
                assert db_dir.exists()


class TestConfigEnvironmentSpecific:
    """Test environment-specific configurations."""

    def test_development_environment_config(self):
        """Test development environment configuration."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "ENVIRONMENT": "development"}):
            config = load_config()
            assert config.environment == Environment.DEVELOPMENT
            assert config.is_development() is True

    def test_production_environment_config(self):
        """Test production environment configuration."""
        with patch.dict(os.environ, {
            "DISCORD_BOT_TOKEN": "token",
            "ENVIRONMENT": "production",
            "SECRET_KEY": "production-secret",
            "ADMIN_PASSWORD": "production-password"
        }):
            config = load_config()
            assert config.environment == Environment.PRODUCTION
            assert config.is_production() is True

    def test_staging_environment_config(self):
        """Test staging environment configuration."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "ENVIRONMENT": "staging"}):
            config = load_config()
            assert config.environment == Environment.STAGING

    def test_testing_environment_config(self):
        """Test testing environment configuration."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "ENVIRONMENT": "testing"}):
            config = load_config()
            assert config.environment == Environment.TESTING


class TestConfigFeatureFlags:
    """Test feature flag configurations."""

    def test_default_feature_flags(self):
        """Test default feature flag values."""
        config = AdvancedBotConfig(discord_bot_token="token")

        assert config.enable_message_caching is True
        assert config.enable_graceful_degradation is True
        assert config.enable_health_checks is True
        assert config.enable_metrics is False

    def test_custom_feature_flags(self):
        """Test custom feature flag values."""
        config = AdvancedBotConfig(
            discord_bot_token="token",
            enable_message_caching=False,
            enable_metrics=True
        )

        assert config.enable_message_caching is False
        assert config.enable_metrics is True


class TestConfigPerformanceSettings:
    """Test performance-related settings."""

    def test_default_performance_settings(self):
        """Test default performance settings."""
        config = AdvancedBotConfig(discord_bot_token="token")

        assert config.message_queue_size == 100
        assert config.worker_threads == 4
        assert config.cache_ttl == 3600

    def test_custom_performance_settings(self):
        """Test custom performance settings."""
        config = AdvancedBotConfig(
            discord_bot_token="token",
            message_queue_size=500,
            worker_threads=8,
            cache_ttl=7200
        )

        assert config.message_queue_size == 500
        assert config.worker_threads == 8
        assert config.cache_ttl == 7200
