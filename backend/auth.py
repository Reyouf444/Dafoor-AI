"""
Authentication helpers for Dafoor AI.

Password hashing:  PBKDF2-HMAC-SHA256 (stored in SQLite — that's fine, user
                   records don't need to survive ephemeral restarts).

Session management: Delegated entirely to session_store.py (Firestore).
                    The public API (create_session / verify_session / delete_session)
                    is unchanged so main.py requires no edits.
"""

import hashlib
import secrets

from backend.session_store import (
    create_session  as _store_create,
    verify_session  as _store_verify,
    delete_session  as _store_delete,
)


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = secrets.token_hex(16)
    key  = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,         # NIST-recommended minimum iteration count
    )
    return f"{salt}:{key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    try:
        salt, key_hex = hashed.split(":")
        key     = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        )
        return secrets.compare_digest(key, new_key)
    except Exception:
        return False


# ── Session helpers (thin wrappers around Firestore store) ───────────────────
# These keep the same signatures that main.py already calls — no changes needed
# there.

def create_session(user_id: int) -> str:
    """Generate a secure token, persist it to Firestore, and return it."""
    token = secrets.token_hex(32)
    _store_create(token, user_id)
    return token


def verify_session(token: str) -> int | None:
    """Return user_id if the token is valid and not expired, else None."""
    return _store_verify(token)


def delete_session(token: str) -> None:
    """Delete a session from Firestore (called on logout)."""
    _store_delete(token)
