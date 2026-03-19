"""Token encryption/decryption utilities using Fernet symmetric encryption."""

import base64
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive token values.

    Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
    The encryption key must be a base64-encoded 32-byte value stored in
    the ENCRYPTION_KEY environment variable.
    """

    def __init__(self, key: str | None = None) -> None:
        """Initialize the encryption service.

        Args:
            key: Optional base64-encoded Fernet key. Defaults to ENCRYPTION_KEY from settings.
        """
        raw_key = key or settings.ENCRYPTION_KEY
        if not raw_key:
            raise ValueError(
                "ENCRYPTION_KEY is not set. Generate one with encryption.generate_key()."
            )
        self._fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return a base64-encoded ciphertext.

        Args:
            plaintext: The string to encrypt (e.g. an OAuth token).

        Returns:
            Base64-encoded encrypted ciphertext string.
        """
        logger.debug("Encrypting value: ***")
        ciphertext_bytes = self._fernet.encrypt(plaintext.encode("utf-8"))
        return ciphertext_bytes.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext string.

        Args:
            ciphertext: The encrypted ciphertext produced by :meth:`encrypt`.

        Returns:
            The original plaintext string.

        Raises:
            InvalidToken: If the ciphertext is invalid or has been tampered with.
            ValueError: If the ciphertext is empty.
        """
        if not ciphertext:
            raise ValueError("ciphertext must not be empty")
        logger.debug("Decrypting value: ***")
        try:
            plaintext_bytes = self._fernet.decrypt(ciphertext.encode("utf-8"))
        except InvalidToken as exc:
            logger.error("Failed to decrypt value (invalid token): ***")
            raise InvalidToken("Decryption failed: invalid or tampered ciphertext") from exc
        return plaintext_bytes.decode("utf-8")


def generate_key() -> str:
    """Generate a new Fernet-compatible base64-encoded 32-byte key.

    Returns:
        A URL-safe base64-encoded string suitable for use as ENCRYPTION_KEY.

    Example::

        key = generate_key()
        # Store in your .env: ENCRYPTION_KEY=<key>
    """
    key_bytes = Fernet.generate_key()
    return key_bytes.decode("utf-8")
