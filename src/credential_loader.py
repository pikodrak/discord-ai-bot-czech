"""
Credential loader for loading and validating credentials from multiple sources.

Provides a unified interface for loading credentials from environment variables,
encrypted vault, or defaults with validation and health checking.
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from src.credential_vault import CredentialVault, CredentialType, get_credential_vault


@dataclass
class CredentialConfig:
    """Configuration for a credential to load."""

    name: str
    env_var: str
    credential_type: CredentialType
    required: bool = False
    default: Optional[str] = None
    min_length: Optional[int] = None

    def validate(self, value: Optional[str]) -> bool:
        """
        Validate credential value.

        Args:
            value: Credential value to validate

        Returns:
            True if valid, False otherwise
        """
        if value is None:
            return not self.required

        if self.min_length and len(value) < self.min_length:
            return False

        return True


class CredentialLoader:
    """
    Loads and validates credentials from multiple sources.

    Priority order:
    1. Environment variables
    2. Encrypted vault
    3. Default values (if not in strict mode)

    Example:
        ```python
        loader = CredentialLoader()

        config = CredentialConfig(
            name="api_key",
            env_var="ANTHROPIC_API_KEY",
            credential_type=CredentialType.API_KEY,
            required=True
        )

        value = loader.load_credential(config)
        ```
    """

    def __init__(
        self,
        vault: Optional[CredentialVault] = None,
        strict_mode: bool = None
    ):
        """
        Initialize credential loader.

        Args:
            vault: Optional CredentialVault instance
            strict_mode: If True, no defaults allowed. If None, uses ENVIRONMENT env var.
        """
        self.vault = vault or get_credential_vault()

        if strict_mode is None:
            environment = os.getenv("ENVIRONMENT", "development")
            self.strict_mode = environment == "production"
        else:
            self.strict_mode = strict_mode

        self._loaded_credentials: Dict[str, Optional[str]] = {}
        self._missing_required: List[str] = []

    def load_credential(self, config: CredentialConfig) -> Optional[str]:
        """
        Load credential from available sources.

        Args:
            config: Credential configuration

        Returns:
            Credential value or None if not found

        Raises:
            ValueError: If required credential missing in strict mode
        """
        value: Optional[str] = None

        # Try environment variable
        env_value = os.getenv(config.env_var)
        if env_value:
            value = env_value

        # Try vault if not found in environment
        if value is None:
            try:
                vault_value = self.vault.get_credential(
                    config.env_var,
                    env_var_override=False
                )
                if vault_value:
                    value = vault_value
            except Exception:
                # Vault may not be configured
                pass

        # Use default if allowed
        if value is None and config.default and not self.strict_mode:
            value = config.default

        # Validate
        if not config.validate(value):
            if config.required:
                self._missing_required.append(config.name)

                if self.strict_mode:
                    raise ValueError(
                        f"Required credential '{config.name}' "
                        f"(env: {config.env_var}) not found or invalid"
                    )

            value = None

        # Track loaded credential
        self._loaded_credentials[config.name] = value

        return value

    def load_credentials(
        self,
        configs: List[CredentialConfig]
    ) -> Dict[str, Optional[str]]:
        """
        Load multiple credentials.

        Args:
            configs: List of credential configurations

        Returns:
            Dictionary mapping credential names to values
        """
        results = {}

        for config in configs:
            try:
                value = self.load_credential(config)
                results[config.name] = value
            except ValueError:
                # In strict mode, this will raise
                # In non-strict mode, continue
                if self.strict_mode:
                    raise
                results[config.name] = None

        return results

    def validate_credentials(self) -> bool:
        """
        Check if all loaded credentials are valid.

        Returns:
            True if no required credentials are missing
        """
        return len(self._missing_required) == 0

    def get_missing_required(self) -> List[str]:
        """
        Get list of missing required credentials.

        Returns:
            List of credential names
        """
        return self._missing_required.copy()

    def get_loaded_credentials(self) -> Dict[str, Optional[str]]:
        """
        Get dictionary of loaded credentials.

        Returns:
            Dictionary mapping credential names to values
        """
        return self._loaded_credentials.copy()


def check_credential_health() -> Dict[str, Any]:
    """
    Check overall credential system health.

    Returns:
        Dictionary with health status information
    """
    # Standard credentials to check
    standard_credentials = [
        CredentialConfig("discord_bot_token", "DISCORD_BOT_TOKEN", CredentialType.TOKEN, required=True),
        CredentialConfig("discord_guild_id", "DISCORD_GUILD_ID", CredentialType.SECRET, required=False),
        CredentialConfig("anthropic_api_key", "ANTHROPIC_API_KEY", CredentialType.API_KEY, required=False),
        CredentialConfig("google_api_key", "GOOGLE_API_KEY", CredentialType.API_KEY, required=False),
        CredentialConfig("openai_api_key", "OPENAI_API_KEY", CredentialType.API_KEY, required=False),
        CredentialConfig("secret_key", "SECRET_KEY", CredentialType.SECRET, required=True),
        CredentialConfig("admin_password", "ADMIN_PASSWORD", CredentialType.PASSWORD, required=True),
        CredentialConfig("master_encryption_key", "MASTER_ENCRYPTION_KEY", CredentialType.SECRET, required=False),
    ]

    loader = CredentialLoader(strict_mode=False)
    loaded = loader.load_credentials(standard_credentials)

    # Count loaded credentials
    loaded_count = sum(1 for v in loaded.values() if v is not None)
    total_count = len(standard_credentials)
    coverage_percent = (loaded_count / total_count * 100) if total_count > 0 else 0

    # Determine status
    if loaded_count == total_count:
        status = "healthy"
    elif loaded_count >= total_count * 0.7:
        status = "degraded"
    else:
        status = "critical"

    # Get missing credentials
    missing = [name for name, value in loaded.items() if value is None]

    return {
        "status": status,
        "total_credentials": total_count,
        "loaded_credentials": loaded_count,
        "missing_credentials": missing,
        "coverage_percent": round(coverage_percent, 1)
    }
