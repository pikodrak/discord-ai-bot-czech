"""
Configuration Loader with Environment Support

This module provides advanced configuration management with:
- Environment-based configuration (dev, staging, production)
- Configuration validation and type checking
- Secrets management
- Configuration hot-reloading support
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from bot.utils.logger import get_logger

logger = get_logger(__name__)


class Environment(str, Enum):
    """Supported environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize configuration validation error.

        Args:
            message: Error message
            errors: List of validation errors from Pydantic
        """
        super().__init__(message)
        self.errors = errors or []


class AdvancedBotConfig(BaseSettings):
    """
    Advanced bot configuration with environment support.

    This extends the basic BotConfig with additional features:
    - Environment-specific settings
    - Retry and timeout configurations
    - Feature flags
    - Performance tuning options
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment Configuration
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Runtime environment (development, staging, production, testing)",
    )

    # Discord Configuration
    discord_bot_token: str = Field(..., description="Discord bot token")
    discord_guild_id: Optional[int] = Field(None, description="Target guild ID")
    discord_channel_ids: Optional[str] = Field(
        None, description="Comma-separated channel IDs"
    )

    # AI Provider Configuration
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    google_api_key: Optional[str] = Field(None, description="Google API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")

    # Bot Behavior
    bot_response_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    bot_max_history: int = Field(default=50, ge=1, le=200)
    bot_language: str = Field(default="cs")
    bot_personality: str = Field(default="friendly")

    # Database Configuration
    database_url: str = Field(default="sqlite:///./data/bot_data.db")

    # Logging Configuration
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/bot.log")

    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="admin")

    # Error Handling & Retry Configuration
    max_retry_attempts: int = Field(
        default=3, ge=1, le=10, description="Maximum retry attempts for failed operations"
    )
    retry_base_delay: float = Field(
        default=1.0, ge=0.1, le=60.0, description="Base delay between retries in seconds"
    )
    retry_max_delay: float = Field(
        default=30.0, ge=1.0, le=300.0, description="Maximum delay between retries"
    )
    retry_exponential_base: float = Field(
        default=2.0, ge=1.0, le=10.0, description="Exponential backoff base multiplier"
    )

    # Timeout Configuration
    http_timeout: float = Field(
        default=30.0, ge=1.0, le=300.0, description="HTTP request timeout in seconds"
    )
    llm_timeout: float = Field(
        default=60.0, ge=5.0, le=300.0, description="LLM API timeout in seconds"
    )
    discord_timeout: float = Field(
        default=30.0, ge=5.0, le=120.0, description="Discord API timeout in seconds"
    )

    # Reconnection Configuration
    enable_auto_reconnect: bool = Field(
        default=True, description="Enable automatic reconnection on disconnect"
    )
    max_reconnect_attempts: int = Field(
        default=5, ge=1, le=50, description="Maximum reconnection attempts"
    )
    reconnect_base_delay: float = Field(
        default=5.0, ge=1.0, le=60.0, description="Base delay between reconnection attempts"
    )

    # Feature Flags
    enable_message_caching: bool = Field(
        default=True, description="Enable message context caching"
    )
    enable_graceful_degradation: bool = Field(
        default=True, description="Enable graceful degradation on errors"
    )
    enable_health_checks: bool = Field(
        default=True, description="Enable health check endpoints"
    )
    enable_metrics: bool = Field(
        default=False, description="Enable metrics collection"
    )

    # Performance Configuration
    message_queue_size: int = Field(
        default=100, ge=10, le=1000, description="Maximum message queue size"
    )
    worker_threads: int = Field(
        default=4, ge=1, le=32, description="Number of worker threads"
    )
    cache_ttl: int = Field(
        default=3600, ge=60, le=86400, description="Cache TTL in seconds"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: Any) -> Environment:
        """Validate and convert environment."""
        if isinstance(v, Environment):
            return v
        if isinstance(v, str):
            try:
                return Environment(v.lower())
            except ValueError:
                raise ValueError(
                    f"Environment must be one of: {', '.join([e.value for e in Environment])}"
                )
        raise ValueError("Environment must be a string or Environment enum")

    @field_validator("bot_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate bot language code."""
        valid_languages = ["cs", "en", "sk", "de", "es", "fr"]
        v_lower = v.lower()
        if v_lower not in valid_languages:
            raise ValueError(f"Language must be one of: {', '.join(valid_languages)}")
        return v_lower

    def model_post_init(self, __context) -> None:
        """Post-initialization validation and setup."""
        # Warn if no AI API key is configured (bot can still start with graceful degradation)
        if not any(
            [self.anthropic_api_key, self.google_api_key, self.openai_api_key]
        ):
            logger.warning(
                "No AI API key configured "
                "(ANTHROPIC_API_KEY, GOOGLE_API_KEY, or OPENAI_API_KEY). "
                "Bot will run with limited AI capabilities."
            )

        # Validate production environment requirements
        if self.environment == Environment.PRODUCTION:
            self._validate_production_config()

        # Create necessary directories
        self._ensure_directories()

        logger.info(f"Configuration loaded for environment: {self.environment.value}")

    def _validate_production_config(self) -> None:
        """Validate production-specific configuration requirements."""
        if self.secret_key == "dev-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be changed in production environment")

        if self.admin_password == "admin":
            raise ValueError("ADMIN_PASSWORD must be changed in production environment")

        if self.log_level == "DEBUG":
            logger.warning(
                "DEBUG log level is not recommended in production environment"
            )

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        # Create logs directory
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create data directory for database
        if "sqlite" in self.database_url:
            db_path = self.database_url.replace("sqlite:///", "")
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

    def get_channel_ids(self) -> List[int]:
        """
        Parse and return list of channel IDs.

        Returns:
            List of Discord channel IDs as integers
        """
        if not self.discord_channel_ids:
            return []

        result = []
        for cid in self.discord_channel_ids.split(","):
            cid = cid.strip()
            if cid and cid.isdigit():
                result.append(int(cid))
            elif cid:
                logger.warning(f"Skipping invalid channel ID: {cid}")
        return result

    def has_any_ai_key(self) -> bool:
        """Check if any AI provider API key is configured."""
        return bool(
            self.anthropic_api_key
            or self.google_api_key
            or self.openai_api_key
        )

    def has_ai_provider(self, provider: str) -> bool:
        """
        Check if a specific AI provider is configured.

        Args:
            provider: Provider name ("anthropic", "google", or "openai")

        Returns:
            True if the provider API key is configured
        """
        provider_map = {
            "anthropic": self.anthropic_api_key,
            "google": self.google_api_key,
            "openai": self.openai_api_key,
        }
        return bool(provider_map.get(provider.lower()))

    def get_available_providers(self) -> List[str]:
        """
        Get list of available AI providers.

        Returns:
            List of provider names with configured API keys
        """
        providers = []
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.google_api_key:
            providers.append("google")
        if self.openai_api_key:
            providers.append("openai")
        return providers

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Args:
            include_secrets: Whether to include sensitive values

        Returns:
            Configuration as dictionary
        """
        config_dict = self.model_dump()

        if not include_secrets:
            # Mask sensitive values
            sensitive_keys = [
                "discord_bot_token",
                "anthropic_api_key",
                "google_api_key",
                "openai_api_key",
                "secret_key",
                "admin_password",
            ]
            for key in sensitive_keys:
                if key in config_dict and config_dict[key]:
                    config_dict[key] = "***REDACTED***"

        return config_dict

    def __repr__(self) -> str:
        """String representation without sensitive data."""
        return (
            f"AdvancedBotConfig("
            f"env={self.environment.value}, "
            f"language={self.bot_language}, "
            f"providers={self.get_available_providers()}, "
            f"log_level={self.log_level}"
            f")"
        )


class ConfigLoader:
    """
    Configuration loader with support for multiple sources.

    Loads configuration from:
    1. Environment variables
    2. .env files
    3. YAML configuration files (optional)
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration loader.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir or Path.cwd()
        self._config: Optional[AdvancedBotConfig] = None

    def load(self, env_file: Optional[str] = None) -> AdvancedBotConfig:
        """
        Load configuration from all sources.

        Args:
            env_file: Path to .env file (optional)

        Returns:
            Loaded and validated configuration

        Raises:
            ConfigValidationError: If configuration validation fails
        """
        try:
            # Load environment-specific config file if exists
            environment = os.getenv("ENVIRONMENT", "development").lower()
            yaml_config = self._load_yaml_config(environment)

            # Merge with environment variables
            if env_file:
                os.environ.setdefault("ENV_FILE", env_file)

            # Create configuration instance
            self._config = AdvancedBotConfig(**yaml_config)

            logger.info(
                f"Configuration loaded successfully for environment: {self._config.environment.value}"
            )
            logger.debug(f"Available AI providers: {self._config.get_available_providers()}")

            return self._config

        except ValidationError as e:
            error_msg = "Configuration validation failed"
            logger.error(f"{error_msg}: {e}")
            raise ConfigValidationError(error_msg, e.errors())

        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ConfigValidationError(error_msg)

    def _load_yaml_config(self, environment: str) -> Dict[str, Any]:
        """
        Load YAML configuration file for environment.

        Args:
            environment: Environment name

        Returns:
            Configuration dictionary
        """
        yaml_file = self.config_dir / f"config.{environment}.yaml"

        if not yaml_file.exists():
            logger.debug(f"No YAML config file found: {yaml_file}")
            return {}

        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                logger.info(f"Loaded YAML configuration from {yaml_file}")
                return config
        except Exception as e:
            logger.warning(f"Failed to load YAML config from {yaml_file}: {e}")
            return {}

    def reload(self) -> AdvancedBotConfig:
        """
        Reload configuration from sources.

        Returns:
            Reloaded configuration

        Raises:
            ConfigValidationError: If configuration validation fails
        """
        logger.info("Reloading configuration...")
        return self.load()

    def get_config(self) -> Optional[AdvancedBotConfig]:
        """
        Get current configuration.

        Returns:
            Current configuration or None if not loaded
        """
        return self._config


def load_config(
    env_file: Optional[str] = None, config_dir: Optional[Path] = None
) -> AdvancedBotConfig:
    """
    Convenience function to load configuration.

    Args:
        env_file: Path to .env file
        config_dir: Directory containing config files

    Returns:
        Loaded configuration

    Raises:
        ConfigValidationError: If configuration validation fails
    """
    loader = ConfigLoader(config_dir)
    return loader.load(env_file)
