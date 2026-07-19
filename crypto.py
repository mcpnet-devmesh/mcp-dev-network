"""AES-256-GCM encryption service for private messages.

Key loaded at module level from ENCRYPTION_KEY env var (32 bytes, base64-encoded).
Crashes on import if key is missing or invalid — requirement 10.6.
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# --- Key loading (fail-fast at import time) ---
_raw_key_b64 = os.environ.get("ENCRYPTION_KEY")
if not _raw_key_b64:
    raise RuntimeError(
        "ENCRYPTION_KEY env var is required (32 bytes, base64-encoded). "
        "Server cannot start without it."
    )

_KEY = base64.b64decode(_raw_key_b64)
if len(_KEY) != 32:
    raise RuntimeError(
        f"ENCRYPTION_KEY must decode to exactly 32 bytes, got {len(_KEY)}"
    )

_aesgcm = AESGCM(_KEY)


def encrypt_message(plaintext: str) -> str:
    """AES-256-GCM encrypt. Returns base64(nonce + ciphertext + tag)."""
    nonce = os.urandom(12)
    ct = _aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # ct already includes the 16-byte tag appended by AESGCM
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_message(ciphertext_b64: str) -> str:
    """AES-256-GCM decrypt from base64(nonce + ciphertext + tag)."""
    raw = base64.b64decode(ciphertext_b64)
    nonce, ct = raw[:12], raw[12:]
    plaintext_bytes = _aesgcm.decrypt(nonce, ct, None)
    return plaintext_bytes.decode("utf-8")
