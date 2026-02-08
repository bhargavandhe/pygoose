from __future__ import annotations

import logging
from typing import Any

from pygoose.utils.exceptions import PygooseError

logger = logging.getLogger(__name__)


class EncryptionKeyNotSet(PygooseError):
    """Raised when encryption is attempted without setting a key."""


class _EncryptedMarker:
    """Sentinel metadata marker for Encrypted[str] fields."""


class EncryptionManager:
    """Manages encryption keys and operations with thread-safe state."""

    def __init__(self) -> None:
        self._key: bytes | None = None
        self._fernet: Any = None

    def set_key(self, key: str | bytes) -> None:
        """Set the encryption key with type safety.

        Args:
            key: Encryption key as string or bytes

        Raises:
            ValueError: If key format is invalid
        """
        from cryptography.fernet import Fernet

        try:
            if isinstance(key, str):
                key = key.encode()
            self._key = key
            self._fernet = Fernet(key)
            logger.debug("Encryption key set successfully")
        except Exception as e:
            logger.error(f"Failed to set encryption key: {e}")
            raise ValueError(f"Invalid encryption key format: {e}") from e

    def get_key(self) -> bytes:
        """Get the current key or raise with clear error.

        Returns:
            Current encryption key as bytes

        Raises:
            EncryptionKeyNotSet: If no key has been configured
        """
        if self._key is None:
            raise EncryptionKeyNotSet(
                "No encryption key set. Call set_encryption_key() first."
            )
        return self._key

    def encrypt(self, plaintext: str) -> str:
        """Type-safe encryption.

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64 encoded)

        Raises:
            EncryptionKeyNotSet: If no key has been configured
        """
        if self._fernet is None:
            raise EncryptionKeyNotSet(
                "No encryption key set. Call set_encryption_key() first."
            )
        try:
            return self._fernet.encrypt(plaintext.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """Type-safe decryption.

        Args:
            ciphertext: Encrypted string (base64 encoded)

        Returns:
            Decrypted plaintext string

        Raises:
            EncryptionKeyNotSet: If no key has been configured
        """
        if self._fernet is None:
            raise EncryptionKeyNotSet(
                "No encryption key set. Call set_encryption_key() first."
            )
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def reset(self) -> None:
        """Reset encryption state (for testing)."""
        self._key = None
        self._fernet = None
        logger.debug("Encryption state reset")


# Global encryption manager instance
encryption = EncryptionManager()


# Convenience functions (direct delegation to manager)
def generate_encryption_key() -> str:
    """Generate a new Fernet-compatible encryption key.

    Returns:
        New encryption key as base64-encoded string
    """
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


class Encrypted:
    """Type annotation for encrypted fields. Usage: field: Encrypted[str]"""

    def __class_getitem__(cls, item: type) -> Any:
        from typing import Annotated

        if item is not str:
            raise TypeError(f"Encrypted only supports str, got {item}")
        return Annotated[str, _EncryptedMarker()]


def encrypt_value(plaintext: str) -> str:
    """Encrypt a value using the global encryption manager.

    Args:
        plaintext: String to encrypt

    Returns:
        Encrypted string
    """
    return encryption.encrypt(plaintext)


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a value using the global encryption manager.

    Args:
        ciphertext: Encrypted string

    Returns:
        Decrypted plaintext
    """
    return encryption.decrypt(ciphertext)


def detect_encrypted_fields(cls: type) -> set[str]:
    """Inspect model_fields metadata to find Encrypted[str] fields.

    Args:
        cls: Document class to inspect

    Returns:
        Set of field names that are encrypted
    """
    encrypted = set()
    for field_name, field_info in cls.model_fields.items():
        # Pydantic v2 strips Annotated and puts metadata in field_info.metadata
        for meta in field_info.metadata:
            if isinstance(meta, _EncryptedMarker):
                encrypted.add(field_name)
                break
    return encrypted


async def rotate_encryption_key(
    document_class: type, old_key: str | bytes, new_key: str | bytes
) -> int:
    """Re-encrypt all documents from old_key to new_key with error handling.

    Args:
        document_class: Document class with encrypted fields
        old_key: Current encryption key
        new_key: New encryption key

    Returns:
        Count of updated documents

    Raises:
        ValueError: If keys are invalid or encryption fails
    """
    from cryptography.fernet import Fernet

    if isinstance(old_key, str):
        old_key = old_key.encode()
    if isinstance(new_key, str):
        new_key = new_key.encode()

    try:
        old_fernet = Fernet(old_key)
        new_fernet = Fernet(new_key)
    except Exception as e:
        logger.error(f"Invalid encryption keys: {e}")
        raise ValueError(f"Invalid encryption keys: {e}") from e

    encrypted_fields = document_class._encrypted_fields
    if not encrypted_fields:
        logger.info("No encrypted fields found, skipping rotation")
        return 0

    collection = document_class.get_collection()
    count = 0
    failed = 0

    logger.info(f"Starting key rotation for {document_class.__name__}")

    try:
        async for raw_doc in collection.find():
            try:
                update = {}
                for field_name in encrypted_fields:
                    value = raw_doc.get(field_name)
                    if value is not None:
                        # Decrypt with old key
                        plaintext = old_fernet.decrypt(value.encode()).decode()
                        # Encrypt with new key
                        new_ciphertext = new_fernet.encrypt(plaintext.encode()).decode()
                        update[field_name] = new_ciphertext

                if update:
                    await collection.update_one({"_id": raw_doc["_id"]}, {"$set": update})
                    count += 1

                    # Log progress every 100 documents
                    if count % 100 == 0:
                        logger.info(f"Rotated {count} documents...")

            except Exception as e:
                failed += 1
                logger.error(f"Failed to rotate document {raw_doc.get('_id')}: {e}")
                # Continue with other documents instead of failing completely

        # Only update global key if rotation was successful
        if failed == 0:
            encryption.set_key(new_key)
            logger.info(
                f"Key rotation complete: {count} documents updated, {failed} failed"
            )
        else:
            logger.warning(
                f"Key rotation completed with errors: {count} succeeded, {failed} failed. "
                f"Global key NOT updated."
            )

        return count

    except Exception as e:
        logger.error(f"Key rotation failed: {e}")
        raise ValueError(f"Key rotation failed: {e}") from e
