"""
Password hashing.

Argon2id is the current OWASP-recommended password hashing algorithm. It is
deliberately slow and memory-hard, which makes brute-forcing leaked hashes
expensive. We never store or log plain-text passwords.

JWT token creation and verification are added to this module in Sprint 1.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # library defaults follow the OWASP-recommended profile


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True when the stored hash used weaker parameters than today's defaults."""
    return _hasher.check_needs_rehash(password_hash)

