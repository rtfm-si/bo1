"""Encryption service for sensitive data at rest.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256).
Key must be provided via ENCRYPTION_KEY environment variable.
"""

import json
import logging
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Error during encryption/decryption operation."""

    pass


class EncryptionService:
    """Service for encrypting/decrypting sensitive data.

    Uses Fernet (AES-128-CBC + HMAC-SHA256) for authenticated encryption.
    Key must be 32 bytes, URL-safe base64-encoded.

    Generate a key with:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """

    def __init__(self, key: str) -> None:
        """Initialize encryption service.

        Args:
            key: Fernet key (32 bytes, URL-safe base64-encoded)

        Raises:
            EncryptionError: If key is invalid
        """
        if not key:
            raise EncryptionError("Encryption key is required")

        try:
            self._fernet = Fernet(key.encode())
        except (ValueError, TypeError) as e:
            raise EncryptionError(f"Invalid encryption key format: {e}") from e

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded ciphertext

        Raises:
            EncryptionError: If encryption fails
        """
        try:
            ciphertext = self._fernet.encrypt(plaintext.encode())
            return ciphertext.decode()
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}") from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string.

        Args:
            ciphertext: Base64-encoded ciphertext

        Returns:
            Decrypted plaintext

        Raises:
            EncryptionError: If decryption fails (invalid key, tampered data, etc.)
        """
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode())
            return plaintext.decode()
        except InvalidToken as e:
            raise EncryptionError(
                "Decryption failed: invalid token (wrong key or tampered data)"
            ) from e
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}") from e

    def encrypt_json(self, data: dict[str, Any]) -> str:
        """Encrypt a dictionary as JSON.

        Args:
            data: Dictionary to encrypt

        Returns:
            Base64-encoded ciphertext
        """
        return self.encrypt(json.dumps(data))

    def decrypt_json(self, ciphertext: str) -> dict[str, Any]:
        """Decrypt ciphertext to a dictionary.

        Args:
            ciphertext: Base64-encoded ciphertext

        Returns:
            Decrypted dictionary

        Raises:
            EncryptionError: If decryption fails or JSON is invalid
        """
        try:
            plaintext = self.decrypt(ciphertext)
            result: dict[str, Any] = json.loads(plaintext)
            return result
        except json.JSONDecodeError as e:
            raise EncryptionError(f"Decrypted data is not valid JSON: {e}") from e


# Singleton instance
_encryption_service: EncryptionService | None = None


@lru_cache(maxsize=1)
def get_encryption_service() -> EncryptionService:
    """Get the encryption service singleton.

    Lazily initializes from ENCRYPTION_KEY environment variable.

    Returns:
        EncryptionService instance

    Raises:
        EncryptionError: If ENCRYPTION_KEY is not set or invalid
    """
    from bo1.config import get_settings

    settings = get_settings()
    key = settings.encryption_key

    if not key:
        raise EncryptionError(
            "ENCRYPTION_KEY environment variable is required. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

    return EncryptionService(key)


def reset_encryption_service() -> None:
    """Reset the encryption service singleton (for testing)."""
    get_encryption_service.cache_clear()


def is_encrypted(data: str) -> bool:
    """Check if a string looks like Fernet-encrypted data.

    Fernet tokens are URL-safe base64 with specific structure.
    This is a heuristic check, not cryptographic validation.

    Args:
        data: String to check

    Returns:
        True if data appears to be Fernet-encrypted
    """
    if not data or len(data) < 50:
        return False

    # Fernet tokens start with "gAAAAA" (version byte + timestamp)
    # and are URL-safe base64
    try:
        return data.startswith("gAAAAA") and all(c.isalnum() or c in "-_=" for c in data)
    except Exception:
        return False
