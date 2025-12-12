"""Tests for the encryption service."""

import json

import pytest
from cryptography.fernet import Fernet

from backend.services.encryption import (
    EncryptionError,
    EncryptionService,
    is_encrypted,
    reset_encryption_service,
)


@pytest.fixture
def valid_key() -> str:
    """Generate a valid Fernet key for testing."""
    return Fernet.generate_key().decode()


@pytest.fixture
def encryption_service(valid_key: str) -> EncryptionService:
    """Create an encryption service with a valid key."""
    return EncryptionService(valid_key)


class TestEncryptionService:
    """Test EncryptionService class."""

    def test_init_with_valid_key(self, valid_key: str) -> None:
        """Test initialization with a valid key."""
        service = EncryptionService(valid_key)
        assert service is not None

    def test_init_with_empty_key(self) -> None:
        """Test initialization with an empty key raises error."""
        with pytest.raises(EncryptionError, match="Encryption key is required"):
            EncryptionService("")

    def test_init_with_invalid_key(self) -> None:
        """Test initialization with an invalid key raises error."""
        with pytest.raises(EncryptionError, match="Invalid encryption key format"):
            EncryptionService("not-a-valid-key")

    def test_encrypt_decrypt_roundtrip(self, encryption_service: EncryptionService) -> None:
        """Test that encrypt -> decrypt returns original data."""
        plaintext = "hello world"
        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertext(
        self, encryption_service: EncryptionService
    ) -> None:
        """Test that encrypting the same data produces different ciphertext (due to IV)."""
        plaintext = "hello world"
        ciphertext1 = encryption_service.encrypt(plaintext)
        ciphertext2 = encryption_service.encrypt(plaintext)
        # Fernet uses random IV, so ciphertext should differ
        assert ciphertext1 != ciphertext2

    def test_decrypt_with_wrong_key(self, valid_key: str) -> None:
        """Test that decrypting with wrong key raises error."""
        service1 = EncryptionService(valid_key)
        service2 = EncryptionService(Fernet.generate_key().decode())

        ciphertext = service1.encrypt("secret data")

        with pytest.raises(EncryptionError, match="invalid token"):
            service2.decrypt(ciphertext)

    def test_decrypt_tampered_data(self, encryption_service: EncryptionService) -> None:
        """Test that decrypting tampered data raises error."""
        ciphertext = encryption_service.encrypt("secret data")
        # Tamper with the ciphertext
        tampered = ciphertext[:-5] + "XXXXX"

        with pytest.raises(EncryptionError, match="invalid token"):
            encryption_service.decrypt(tampered)

    def test_encrypt_json_roundtrip(self, encryption_service: EncryptionService) -> None:
        """Test JSON encrypt -> decrypt roundtrip."""
        data = {"access_token": "ya29.xxx", "refresh_token": "1//xxx", "expires_at": "2025-01-01"}

        ciphertext = encryption_service.encrypt_json(data)
        decrypted = encryption_service.decrypt_json(ciphertext)

        assert decrypted == data

    def test_encrypt_json_with_nested_data(self, encryption_service: EncryptionService) -> None:
        """Test JSON encryption with nested data structures."""
        data = {
            "tokens": {"access": "xxx", "refresh": "yyy"},
            "scopes": ["spreadsheets.readonly", "drive.readonly"],
            "metadata": {"created": 1234567890},
        }

        ciphertext = encryption_service.encrypt_json(data)
        decrypted = encryption_service.decrypt_json(ciphertext)

        assert decrypted == data

    def test_decrypt_json_invalid_json(self, encryption_service: EncryptionService) -> None:
        """Test that decrypting non-JSON data raises error."""
        ciphertext = encryption_service.encrypt("not json data")

        with pytest.raises(EncryptionError, match="not valid JSON"):
            encryption_service.decrypt_json(ciphertext)


class TestIsEncrypted:
    """Test is_encrypted helper function."""

    def test_is_encrypted_with_fernet_token(self, encryption_service: EncryptionService) -> None:
        """Test is_encrypted returns True for Fernet-encrypted data."""
        ciphertext = encryption_service.encrypt("test data")
        assert is_encrypted(ciphertext) is True

    def test_is_encrypted_with_json(self) -> None:
        """Test is_encrypted returns False for plain JSON."""
        json_data = json.dumps({"access_token": "xxx"})
        assert is_encrypted(json_data) is False

    def test_is_encrypted_with_empty_string(self) -> None:
        """Test is_encrypted returns False for empty string."""
        assert is_encrypted("") is False

    def test_is_encrypted_with_short_string(self) -> None:
        """Test is_encrypted returns False for short strings."""
        assert is_encrypted("short") is False

    def test_is_encrypted_with_none(self) -> None:
        """Test is_encrypted handles None gracefully."""
        # type: ignore because we're testing edge case
        assert is_encrypted(None) is False  # type: ignore[arg-type]


class TestGetEncryptionService:
    """Test get_encryption_service singleton."""

    def test_get_encryption_service_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing ENCRYPTION_KEY raises error."""
        reset_encryption_service()
        monkeypatch.setenv("ENCRYPTION_KEY", "")

        # Reset settings cache
        from bo1.config import reset_settings

        reset_settings()

        from backend.services.encryption import get_encryption_service

        with pytest.raises(
            EncryptionError, match="ENCRYPTION_KEY environment variable is required"
        ):
            get_encryption_service()

    def test_get_encryption_service_with_valid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that valid ENCRYPTION_KEY returns service."""
        reset_encryption_service()
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", key)

        # Reset settings cache
        from bo1.config import reset_settings

        reset_settings()

        from backend.services.encryption import get_encryption_service

        service = get_encryption_service()
        assert service is not None

        # Test it works
        ciphertext = service.encrypt("test")
        assert service.decrypt(ciphertext) == "test"
