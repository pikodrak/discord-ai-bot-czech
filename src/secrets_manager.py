"""
Secrets encryption and decryption manager using AES-256-GCM.

Provides secure encryption/decryption functionality for sensitive credentials
using authenticated encryption with PBKDF2 key derivation.
"""

import os
import json
import base64
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""

    ciphertext: str
    nonce: str
    salt: str

    def to_dict(self) -> Dict[str, str]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with encrypted data fields
        """
        return {
            "ciphertext": self.ciphertext,
            "nonce": self.nonce,
            "salt": self.salt
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "EncryptedData":
        """
        Create from dictionary.

        Args:
            data: Dictionary with encrypted data fields

        Returns:
            EncryptedData instance
        """
        return cls(
            ciphertext=data["ciphertext"],
            nonce=data["nonce"],
            salt=data["salt"]
        )


class SecretsManager:
    """
    Manages encryption and decryption of sensitive data.

    Uses AES-256-GCM authenticated encryption with PBKDF2 key derivation.
    Each encryption operation uses a unique salt and nonce for security.

    Example:
        ```python
        manager = SecretsManager(master_key="your-secure-key")

        # Encrypt data
        encrypted = manager.encrypt("secret-value")

        # Decrypt data
        plaintext = manager.decrypt(encrypted)
        ```
    """

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize secrets manager.

        Args:
            master_key: Master encryption key (base64 encoded).
                       If None, attempts to load from MASTER_ENCRYPTION_KEY env var.

        Raises:
            ValueError: If no master key is provided or found
        """
        if master_key is None:
            master_key = os.getenv("MASTER_ENCRYPTION_KEY")

        if not master_key:
            raise ValueError(
                "Master encryption key required. "
                "Provide via constructor or MASTER_ENCRYPTION_KEY environment variable."
            )

        self.master_key = master_key

    def _derive_key(self, salt: bytes) -> bytes:
        """
        Derive encryption key from master key using PBKDF2.

        Args:
            salt: Random salt for key derivation

        Returns:
            Derived 256-bit key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(self.master_key.encode())

    def encrypt(self, plaintext: str) -> EncryptedData:
        """
        Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: Data to encrypt

        Returns:
            EncryptedData with ciphertext, nonce, and salt

        Raises:
            ValueError: If encryption fails
        """
        try:
            # Generate random salt and nonce
            salt = os.urandom(16)
            nonce = os.urandom(12)

            # Derive encryption key
            key = self._derive_key(salt)

            # Encrypt with AES-GCM
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(
                nonce,
                plaintext.encode(),
                None  # No additional authenticated data
            )

            # Encode to base64 for storage
            return EncryptedData(
                ciphertext=base64.b64encode(ciphertext).decode(),
                nonce=base64.b64encode(nonce).decode(),
                salt=base64.b64encode(salt).decode()
            )

        except Exception as e:
            raise ValueError(f"Failed to encrypt data: {e}")

    def decrypt(self, encrypted_data: EncryptedData) -> str:
        """
        Decrypt encrypted data.

        Args:
            encrypted_data: EncryptedData instance

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails
        """
        try:
            # Decode from base64
            ciphertext = base64.b64decode(encrypted_data.ciphertext)
            nonce = base64.b64decode(encrypted_data.nonce)
            salt = base64.b64decode(encrypted_data.salt)

            # Derive encryption key
            key = self._derive_key(salt)

            # Decrypt with AES-GCM
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            return plaintext.decode()

        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {e}")

    def encrypt_dict(
        self,
        data: Dict[str, Any],
        keys_to_encrypt: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Encrypt specific keys in a dictionary.

        Args:
            data: Dictionary to encrypt
            keys_to_encrypt: List of keys to encrypt. If None, encrypts all string values.

        Returns:
            Dictionary with encrypted values
        """
        result = {}

        for key, value in data.items():
            if keys_to_encrypt and key not in keys_to_encrypt:
                result[key] = value
            elif isinstance(value, str):
                encrypted = self.encrypt(value)
                result[key] = encrypted.to_dict()
            elif isinstance(value, dict):
                result[key] = self.encrypt_dict(value, keys_to_encrypt)
            else:
                result[key] = value

        return result

    def decrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt dictionary with encrypted values.

        Args:
            data: Dictionary with encrypted values

        Returns:
            Dictionary with decrypted values
        """
        result = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # Check if it's encrypted data
                if all(k in value for k in ["ciphertext", "nonce", "salt"]):
                    encrypted = EncryptedData.from_dict(value)
                    result[key] = self.decrypt(encrypted)
                else:
                    result[key] = self.decrypt_dict(value)
            else:
                result[key] = value

        return result

    def save_encrypted_config(
        self,
        config: Dict[str, Any],
        file_path: Union[str, Path]
    ) -> None:
        """
        Save encrypted configuration to file.

        Args:
            config: Configuration dictionary to encrypt and save
            file_path: Path to save encrypted config

        Raises:
            IOError: If file operations fail
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            encrypted = self.encrypt_dict(config)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(encrypted, f, indent=2)

            # Set restrictive permissions
            os.chmod(file_path, 0o600)

        except Exception as e:
            raise IOError(f"Failed to save encrypted config: {e}")

    def load_encrypted_config(
        self,
        file_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Load and decrypt configuration from file.

        Args:
            file_path: Path to encrypted config file

        Returns:
            Decrypted configuration dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file operations fail
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"Config file not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                encrypted = json.load(f)

            return self.decrypt_dict(encrypted)

        except FileNotFoundError:
            raise
        except Exception as e:
            raise IOError(f"Failed to load encrypted config: {e}")


def generate_master_key() -> str:
    """
    Generate a secure random master encryption key.

    Returns:
        Base64-encoded 256-bit key

    Example:
        ```python
        key = generate_master_key()
        print(f"MASTER_ENCRYPTION_KEY={key}")
        ```
    """
    key_bytes = os.urandom(32)  # 256 bits
    return base64.b64encode(key_bytes).decode()


def get_secrets_manager(master_key: Optional[str] = None) -> SecretsManager:
    """
    Get or create secrets manager instance (singleton pattern).

    Args:
        master_key: Optional master key. If None, uses environment variable.

    Returns:
        SecretsManager instance
    """
    return SecretsManager(master_key=master_key)
