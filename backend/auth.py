from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError

# Single hasher with argon2 defaults. Defaults are a sensible OWASP-aligned
# baseline; we intentionally do not expose tuning knobs to keep this simple.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an argon2 hash (includes algorithm, parameters, and salt)."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if the password matches the hash, False otherwise.

    Returns False (rather than raising) for a wrong password or a malformed or
    empty hash, so callers can treat every failure as a single auth failure.
    """
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (Argon2Error, InvalidHashError):
        return False
