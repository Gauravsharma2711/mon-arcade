"""
Bluff or Bust Cryptographic Commitment and Reveal Module.

Provides:
- Cryptographically secure random salt generation (secrets module)
- Deterministic commitment hashing (SHA-256)
- Constant-time reveal verification (hmac.compare_digest)
- Isolated secret number generation rules (1 to 10)

Does NOT make provably-fair claims; provides deterministic commit-reveal integrity.
"""

import hashlib
import hmac
import secrets
from typing import Tuple, Optional


def generate_salt(byte_length: int = 32) -> str:
    """Generate a cryptographically secure random hexadecimal salt."""
    return secrets.token_hex(byte_length)


def generate_secret_value(min_val: int = 1, max_val: int = 10) -> int:
    """
    Generate a secret card value within the configured bounds (default 1 to 10).
    Uses secrets.randbelow for cryptographically appropriate randomness.
    """
    if min_val > max_val:
        raise ValueError("min_val must be less than or equal to max_val")
    span = max_val - min_val + 1
    return secrets.randbelow(span) + min_val


def create_commitment(secret: int, salt: str) -> str:
    """
    Produce a deterministic cryptographic commitment hash from a secret number and salt.
    Format: sha256("{secret}:{salt}")
    """
    if not isinstance(secret, int):
        raise TypeError("Secret value must be an integer")
    if not salt or not isinstance(salt, str):
        raise ValueError("Salt must be a non-empty string")

    payload = f"{secret}:{salt}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_commitment(secret: int, salt: str, expected_commitment: str) -> bool:
    """
    Recalculate the commitment hash and verify against the expected commitment
    using constant-time string comparison to prevent timing attacks.
    """
    if not isinstance(secret, int) or not salt or not expected_commitment:
        return False

    calculated_commitment = create_commitment(secret, salt)
    return hmac.compare_digest(calculated_commitment.lower(), expected_commitment.lower())


def create_secret_commitment(secret: Optional[int] = None) -> Tuple[int, str, str]:
    """
    Helper to bundle secret value, salt, and commitment hash.
    Returns: (secret_value, salt, commitment_hash)
    """
    val = secret if secret is not None else generate_secret_value()
    salt = generate_salt()
    commitment = create_commitment(val, salt)
    return val, salt, commitment
