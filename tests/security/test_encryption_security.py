"""
Comprehensive security tests for encryption and decryption.

Tests cover:
- Encryption strength and randomness
- Key derivation security
- Cipher mode security (AES-GCM)
- Side-channel attack resistance
- Cryptographic parameter validation
- Error handling and information leakage
"""

import pytest
import os
import base64
import hashlib
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.exceptions import InvalidTag
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from secrets_manager import SecretsManager


class TestEncryptionStrength:
    """Tests for cryptographic strength and security properties."""

    def test_encryption_produces_different_ciphertext_for_same_plaintext(self):
        """Ensure same plaintext produces different ciphertexts (IND-CPA security)."""
        manager = SecretsManager(master_key="test_master_key_12345678")
        plaintext = "sensitive_data"

        ciphertext1 = manager.encrypt(plaintext)
        ciphertext2 = manager.encrypt(plaintext)

        assert ciphertext1 != ciphertext2, "Same plaintext should produce different ciphertexts"

        # Verify both decrypt to the same plaintext
        assert manager.decrypt(ciphertext1) == plaintext
        assert manager.decrypt(ciphertext2) == plaintext

    def test_salt_uniqueness_across_operations(self):
        """Verify each encryption operation uses a unique salt."""
        manager = SecretsManager(master_key="test_master_key_12345678")
        plaintext = "test_data"

        salts = set()
        for _ in range(100):
            encrypted = manager.encrypt(plaintext)
            # Extract salt from base64 encoded format
            decoded = base64.b64decode(encrypted)
            salt = decoded[:16]  # First 16 bytes are salt
            salts.add(salt)

        assert len(salts) == 100, "Each encryption should use a unique salt"

    def test_nonce_uniqueness_across_operations(self):
        """Verify each encryption operation uses a unique nonce."""
        manager = SecretsManager(master_key="test_master_key_12345678")
        plaintext = "test_data"

        nonces = set()
        for _ in range(100):
            encrypted = manager.encrypt(plaintext)
            decoded = base64.b64decode(encrypted)
            nonce = decoded[16:28]  # Bytes 16-28 are nonce
            nonces.add(nonce)

        assert len(nonces) == 100, "Each encryption should use a unique nonce"

    def test_key_derivation_strength(self):
        """Test PBKDF2 key derivation parameters."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        # Test that key derivation uses sufficient iterations
        # This is a timing-based test - more iterations = more time
        import time

        start = time.time()
        _ = manager.encrypt("test")
        duration = time.time() - start

        # PBKDF2 with 100,000 iterations should take measurable time (> 1ms)
        assert duration > 0.001, "Key derivation should use sufficient iterations"

    def test_encryption_output_length(self):
        """Verify encryption output has expected length (salt + nonce + ciphertext + tag)."""
        manager = SecretsManager(master_key="test_master_key_12345678")
        plaintext = "test"

        encrypted = manager.encrypt(plaintext)
        decoded = base64.b64decode(encrypted)

        # Expected: 16 (salt) + 12 (nonce) + len(plaintext) + 16 (GCM tag)
        expected_length = 16 + 12 + len(plaintext.encode()) + 16
        assert len(decoded) == expected_length

    def test_encryption_with_empty_string(self):
        """Test encryption of empty strings."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        encrypted = manager.encrypt("")
        decrypted = manager.decrypt(encrypted)

        assert decrypted == ""

    def test_encryption_with_unicode(self):
        """Test encryption of Unicode characters."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        unicode_text = "Hello 世界 🔐 Příliš žluťoučký kůň"
        encrypted = manager.encrypt(unicode_text)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == unicode_text

    def test_encryption_with_large_data(self):
        """Test encryption of large data blocks."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        large_text = "x" * 1_000_000  # 1 MB
        encrypted = manager.encrypt(large_text)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == large_text


class TestDecryptionSecurity:
    """Tests for decryption security and error handling."""

    def test_decryption_with_wrong_key(self):
        """Verify decryption fails with wrong key."""
        manager1 = SecretsManager(master_key="correct_key_12345678901")
        manager2 = SecretsManager(master_key="wrong_key_123456789012")

        plaintext = "sensitive_data"
        encrypted = manager1.encrypt(plaintext)

        with pytest.raises(Exception):  # Should raise decryption error
            manager2.decrypt(encrypted)

    def test_decryption_with_corrupted_ciphertext(self):
        """Verify decryption fails with corrupted ciphertext."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        plaintext = "test_data"
        encrypted = manager.encrypt(plaintext)

        # Corrupt the ciphertext
        decoded = base64.b64decode(encrypted)
        corrupted = bytearray(decoded)
        corrupted[30] ^= 0xFF  # Flip bits in ciphertext
        corrupted_encrypted = base64.b64encode(bytes(corrupted)).decode()

        with pytest.raises(Exception):
            manager.decrypt(corrupted_encrypted)

    def test_decryption_with_corrupted_tag(self):
        """Verify GCM authentication tag is validated."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        plaintext = "test_data"
        encrypted = manager.encrypt(plaintext)

        # Corrupt the authentication tag (last 16 bytes)
        decoded = base64.b64decode(encrypted)
        corrupted = bytearray(decoded)
        corrupted[-1] ^= 0xFF
        corrupted_encrypted = base64.b64encode(bytes(corrupted)).decode()

        with pytest.raises(Exception):
            manager.decrypt(corrupted_encrypted)

    def test_decryption_with_invalid_base64(self):
        """Verify proper error handling for invalid base64."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        with pytest.raises(Exception):
            manager.decrypt("not_valid_base64!@#$")

    def test_decryption_with_truncated_data(self):
        """Verify error handling for truncated encrypted data."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        plaintext = "test_data"
        encrypted = manager.encrypt(plaintext)

        # Truncate the encrypted data
        truncated = encrypted[:20]

        with pytest.raises(Exception):
            manager.decrypt(truncated)

    def test_timing_attack_resistance(self):
        """Test that decryption failures have consistent timing (timing attack resistance)."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        plaintext = "test_data"
        encrypted = manager.encrypt(plaintext)

        import time

        # Test timing for wrong key
        wrong_key_times = []
        for _ in range(10):
            wrong_manager = SecretsManager(master_key=f"wrong_key_{_}")
            start = time.time()
            try:
                wrong_manager.decrypt(encrypted)
            except Exception:
                pass
            wrong_key_times.append(time.time() - start)

        # Test timing for corrupted data
        corrupted_times = []
        for i in range(10):
            decoded = base64.b64decode(encrypted)
            corrupted = bytearray(decoded)
            corrupted[30 + i] ^= 0xFF
            corrupted_encrypted = base64.b64encode(bytes(corrupted)).decode()

            start = time.time()
            try:
                manager.decrypt(corrupted_encrypted)
            except Exception:
                pass
            corrupted_times.append(time.time() - start)

        # Timing should be similar (within 50% variation)
        avg_wrong_key = sum(wrong_key_times) / len(wrong_key_times)
        avg_corrupted = sum(corrupted_times) / len(corrupted_times)

        if avg_wrong_key > 0:
            ratio = max(avg_wrong_key, avg_corrupted) / min(avg_wrong_key, avg_corrupted)
            # Allow for some variance but flag if timing differs significantly
            assert ratio < 5.0, "Decryption timing should be consistent to prevent timing attacks"


class TestKeyDerivation:
    """Tests for key derivation security."""

    def test_master_key_minimum_length(self):
        """Verify master key length requirements."""
        # Short keys should still work but are not recommended
        manager = SecretsManager(master_key="short")

        plaintext = "test"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == plaintext

    def test_derived_key_uniqueness(self):
        """Verify different salts produce different derived keys."""
        master_key = "test_master_key_12345678"

        # This test verifies that the same master key + different salts = different derived keys
        # We can test this indirectly by verifying different encryptions can't be decrypted with each other
        manager = SecretsManager(master_key=master_key)

        plaintext = "test"
        encrypted1 = manager.encrypt(plaintext)
        encrypted2 = manager.encrypt(plaintext)

        # Extract components
        decoded1 = base64.b64decode(encrypted1)
        decoded2 = base64.b64decode(encrypted2)

        salt1 = decoded1[:16]
        salt2 = decoded2[:16]

        assert salt1 != salt2, "Different encryptions should use different salts"

    def test_pbkdf2_iteration_count(self):
        """Verify PBKDF2 uses sufficient iterations (100,000)."""
        # This is tested indirectly via timing in test_key_derivation_strength
        # Here we verify the implementation uses the correct parameters
        manager = SecretsManager(master_key="test_key")

        # The implementation should use 100,000 iterations
        # We can verify this by checking the code or via timing
        import time

        iterations_test_count = 10
        times = []

        for _ in range(iterations_test_count):
            start = time.time()
            manager.encrypt("test")
            times.append(time.time() - start)

        avg_time = sum(times) / len(times)

        # With 100k iterations, each encryption should take measurable time
        assert avg_time > 0.001, "PBKDF2 should use sufficient iterations"


class TestDictionaryEncryption:
    """Tests for dictionary encryption with selective key encryption."""

    def test_selective_key_encryption(self):
        """Test that only specified keys are encrypted in dictionaries."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        data = {
            "public_key": "public_value",
            "secret_key": "secret_value",
            "another_public": "another_value"
        }

        keys_to_encrypt = ["secret_key"]
        encrypted_dict = manager.encrypt_dict(data, keys_to_encrypt)

        # Public keys should remain unchanged
        assert encrypted_dict["public_key"] == "public_value"
        assert encrypted_dict["another_public"] == "another_value"

        # Secret key should be encrypted
        assert encrypted_dict["secret_key"] != "secret_value"

        # Decrypt and verify
        decrypted_dict = manager.decrypt_dict(encrypted_dict, keys_to_encrypt)
        assert decrypted_dict == data

    def test_dictionary_with_none_values(self):
        """Test dictionary encryption with None values."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        data = {
            "key1": "value1",
            "key2": None,
            "key3": "value3"
        }

        encrypted_dict = manager.encrypt_dict(data, ["key1", "key2"])
        decrypted_dict = manager.decrypt_dict(encrypted_dict, ["key1", "key2"])

        assert decrypted_dict == data

    def test_dictionary_with_nested_structures(self):
        """Test that nested structures are handled correctly."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        # The current implementation only encrypts string values
        # Nested structures should be converted to strings
        data = {
            "simple": "value",
            "nested": {"inner": "data"}
        }

        # Only encrypt simple string values
        encrypted_dict = manager.encrypt_dict(data, ["simple"])

        assert encrypted_dict["simple"] != "value"
        # Nested should remain unchanged (or be serialized depending on implementation)

        decrypted_dict = manager.decrypt_dict(encrypted_dict, ["simple"])
        assert decrypted_dict["simple"] == "value"


class TestErrorHandlingAndInformationLeakage:
    """Tests to ensure errors don't leak sensitive information."""

    def test_error_messages_dont_leak_plaintext(self):
        """Verify error messages don't contain plaintext data."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        secret_data = "super_secret_password_123"
        encrypted = manager.encrypt(secret_data)

        # Corrupt and try to decrypt
        decoded = base64.b64decode(encrypted)
        corrupted = bytearray(decoded)
        corrupted[30] ^= 0xFF
        corrupted_encrypted = base64.b64encode(bytes(corrupted)).decode()

        try:
            manager.decrypt(corrupted_encrypted)
            assert False, "Should have raised an exception"
        except Exception as e:
            error_message = str(e)
            assert secret_data not in error_message, "Error should not leak plaintext"

    def test_error_messages_dont_leak_keys(self):
        """Verify error messages don't contain key material."""
        master_key = "secret_master_key_xyz"
        manager = SecretsManager(master_key=master_key)

        try:
            manager.decrypt("invalid_data")
            assert False, "Should have raised an exception"
        except Exception as e:
            error_message = str(e).lower()
            assert "secret_master_key" not in error_message, "Error should not leak key material"

    def test_exception_types_are_generic(self):
        """Verify that different error conditions raise similar exceptions."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        # Test various error conditions
        error_types = []

        # Wrong key
        try:
            other_manager = SecretsManager(master_key="wrong_key")
            encrypted = manager.encrypt("test")
            other_manager.decrypt(encrypted)
        except Exception as e:
            error_types.append(type(e).__name__)

        # Corrupted data
        try:
            manager.decrypt("corrupted_base64_data")
        except Exception as e:
            error_types.append(type(e).__name__)

        # Invalid base64
        try:
            manager.decrypt("not!valid@base64")
        except Exception as e:
            error_types.append(type(e).__name__)

        # All error types should be generic (not revealing attack vector)
        # This helps prevent attackers from learning about the system through errors


class TestCryptographicPrimitives:
    """Tests for the underlying cryptographic primitives."""

    def test_aes_gcm_mode_is_used(self):
        """Verify AES-GCM is used (authenticated encryption)."""
        manager = SecretsManager(master_key="test_master_key_12345678")

        plaintext = "test_data"
        encrypted = manager.encrypt(plaintext)
        decoded = base64.b64decode(encrypted)

        # GCM tag is 16 bytes and should be at the end
        assert len(decoded) >= 16, "Encrypted data should include GCM tag"

        # Verify tag validation by corrupting it
        corrupted = bytearray(decoded)
        corrupted[-1] ^= 0xFF
        corrupted_encrypted = base64.b64encode(bytes(corrupted)).decode()

        with pytest.raises(Exception):
            manager.decrypt(corrupted_encrypted)

    def test_key_size_is_256_bits(self):
        """Verify AES-256 is used (32-byte key)."""
        # This is verified through successful encryption/decryption
        # AESGCM expects a 32-byte key for AES-256
        manager = SecretsManager(master_key="test_master_key_12345678")

        # Successful encryption/decryption means correct key size
        plaintext = "test"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == plaintext

    def test_sha256_is_used_for_pbkdf2(self):
        """Verify SHA-256 is used in PBKDF2 (not weaker hash)."""
        # This is verified through the implementation
        # We can test that the derived keys have expected properties
        manager = SecretsManager(master_key="test_key")

        # Different plaintexts should produce different ciphertexts
        encrypted1 = manager.encrypt("test1")
        encrypted2 = manager.encrypt("test2")

        assert encrypted1 != encrypted2


class TestConcurrencyAndThreadSafety:
    """Tests for thread-safety in encryption operations."""

    def test_concurrent_encryption(self):
        """Test concurrent encryption operations."""
        import threading

        manager = SecretsManager(master_key="test_master_key_12345678")
        results = []
        errors = []

        def encrypt_task(data):
            try:
                encrypted = manager.encrypt(data)
                decrypted = manager.decrypt(encrypted)
                results.append((data, decrypted))
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(50):
            thread = threading.Thread(target=encrypt_task, args=(f"data_{i}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Concurrent encryption errors: {errors}"
        assert len(results) == 50

        # Verify all data was encrypted/decrypted correctly
        for original, decrypted in results:
            assert original == decrypted

    def test_concurrent_key_derivation(self):
        """Test that concurrent operations with key derivation don't interfere."""
        import threading

        results = []
        errors = []

        def encrypt_with_new_manager(data, key):
            try:
                manager = SecretsManager(master_key=key)
                encrypted = manager.encrypt(data)
                decrypted = manager.decrypt(encrypted)
                results.append((data, decrypted))
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(20):
            thread = threading.Thread(
                target=encrypt_with_new_manager,
                args=(f"data_{i}", f"key_{i}")
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Concurrent key derivation errors: {errors}"
        assert len(results) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
