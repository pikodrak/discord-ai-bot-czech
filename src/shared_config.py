"""
Shared Configuration Loader

Manages bot configuration with thread-safe operations, hot-reload support,
and automatic fallback to environment variables. Provides a centralized
configuration store that can be shared between the bot and admin interface.
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class SharedConfigLoader:
    """
    Thread-safe shared configuration loader.

    Loads config from multiple sources in priority order:
    1. Shared config JSON file (for hot-reloaded values)
    2. Environment-specific YAML config files
    3. .env file / environment variables

    Provides thread-safe read/write operations and hot-reload support.
    """

    def __init__(self, project_root: Path, env_file: str = ".env"):
        """
        Initialize SharedConfigLoader.

        Args:
            project_root: Root directory of the project
            env_file: Path to .env file relative to project root
        """
        self.project_root = Path(project_root)
        self.env_file = self.project_root / env_file
        self.shared_config_file = self.project_root / "data" / "shared_config.json"
        self._config: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._loaded = False

        # Ensure data directory exists
        self.shared_config_file.parent.mkdir(parents=True, exist_ok=True)

    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load configuration from all sources.

        Args:
            force_reload: Force reload even if already loaded

        Returns:
            Merged configuration dictionary
        """
        with self._lock:
            if self._loaded and not force_reload:
                return self._config.copy()

            config = {}

            # 1. Load from .env file
            if self.env_file.exists():
                load_dotenv(str(self.env_file), override=True)
                logger.info(f"Loaded .env file: {self.env_file}")

            # 2. Load environment-specific YAML config
            environment = os.getenv("ENVIRONMENT", "development").lower()
            yaml_config = self._load_yaml_config(environment)
            config.update(yaml_config)

            # 3. Load from environment variables (these override YAML)
            env_config = self._load_env_config()
            config.update(env_config)

            # 4. Load shared config file (highest priority for hot-reloaded values)
            shared = self._load_shared_file()
            config.update(shared)

            self._config = config
            self._loaded = True

            logger.info(f"Configuration loaded successfully (environment={environment})")
            return self._config.copy()

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to shared config file.

        Args:
            config: Configuration dictionary to save
        """
        with self._lock:
            # Filter out sensitive keys before saving to file
            safe_config = {}
            sensitive_keys = {
                "discord_bot_token", "anthropic_api_key", "google_api_key",
                "openai_api_key", "secret_key", "admin_password",
            }
            for key, value in config.items():
                if key not in sensitive_keys:
                    safe_config[key] = value

            try:
                with open(self.shared_config_file, "w", encoding="utf-8") as f:
                    json.dump(safe_config, f, indent=2, default=str)
                logger.info(f"Shared config saved to {self.shared_config_file}")
            except Exception as e:
                logger.error(f"Failed to save shared config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        with self._lock:
            if not self._loaded:
                self.load_config()
            return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value and persist it.

        Args:
            key: Configuration key
            value: Configuration value
        """
        with self._lock:
            self._config[key] = value
            self.save_config(self._config)

    def _load_yaml_config(self, environment: str) -> Dict[str, Any]:
        """
        Load YAML configuration for the given environment.

        Args:
            environment: Environment name

        Returns:
            Configuration dictionary from YAML
        """
        yaml_file = self.project_root / f"config.{environment}.yaml"
        if not yaml_file.exists():
            logger.debug(f"No YAML config found: {yaml_file}")
            return {}

        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                logger.info(f"Loaded YAML config from {yaml_file}")
                return config
        except Exception as e:
            logger.warning(f"Failed to load YAML config: {e}")
            return {}

    def _load_env_config(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.

        Maps known environment variable names to config keys.

        Returns:
            Configuration dictionary from environment
        """
        config = {}

        # Map environment variables to config keys
        env_mapping = {
            "DISCORD_BOT_TOKEN": "discord_bot_token",
            "DISCORD_GUILD_ID": "discord_guild_id",
            "DISCORD_CHANNEL_IDS": "discord_channel_ids",
            "DISCORD_CHANNEL_ID": "discord_channel_ids",
            "ANTHROPIC_API_KEY": "anthropic_api_key",
            "CLAUDE_API_KEY": "anthropic_api_key",
            "GOOGLE_API_KEY": "google_api_key",
            "OPENAI_API_KEY": "openai_api_key",
            "BOT_RESPONSE_THRESHOLD": "bot_response_threshold",
            "BOT_MAX_HISTORY": "bot_max_history",
            "BOT_LANGUAGE": "bot_language",
            "BOT_PERSONALITY": "bot_personality",
            "DATABASE_URL": "database_url",
            "LOG_LEVEL": "log_level",
            "LOG_FILE": "log_file",
            "API_HOST": "api_host",
            "API_PORT": "api_port",
            "SECRET_KEY": "secret_key",
            "ADMIN_USERNAME": "admin_username",
            "ADMIN_PASSWORD": "admin_password",
            "ENVIRONMENT": "environment",
        }

        for env_key, config_key in env_mapping.items():
            value = os.getenv(env_key)
            if value is not None and value.strip():
                # Type conversion for known types
                if config_key in ("discord_guild_id", "api_port", "bot_max_history"):
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                elif config_key == "bot_response_threshold":
                    try:
                        value = float(value)
                    except ValueError:
                        pass

                config[config_key] = value

        return config

    def _load_shared_file(self) -> Dict[str, Any]:
        """
        Load shared config from JSON file.

        Returns:
            Configuration dictionary from shared file
        """
        if not self.shared_config_file.exists():
            return {}

        try:
            with open(self.shared_config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.debug(f"Loaded shared config from {self.shared_config_file}")
                return config
        except Exception as e:
            logger.warning(f"Failed to load shared config file: {e}")
            return {}


# Module-level singleton storage
_shared_loaders: Dict[str, SharedConfigLoader] = {}
_module_lock = threading.Lock()


def get_shared_config_loader(project_root: Path) -> SharedConfigLoader:
    """
    Get or create a SharedConfigLoader for the given project root.

    Uses a singleton pattern per project root to ensure thread-safety.

    Args:
        project_root: Root directory of the project

    Returns:
        SharedConfigLoader instance
    """
    key = str(project_root)
    with _module_lock:
        if key not in _shared_loaders:
            _shared_loaders[key] = SharedConfigLoader(project_root)
        return _shared_loaders[key]


def load_bot_config_from_shared(project_root: Path) -> Dict[str, Any]:
    """
    Convenience function to load bot config from shared storage.

    Args:
        project_root: Root directory of the project

    Returns:
        Configuration dictionary suitable for AdvancedBotConfig
    """
    loader = get_shared_config_loader(project_root)
    return loader.load_config()
