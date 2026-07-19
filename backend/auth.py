"""
Authentication helpers for Dafoor AI.

Password hashing:  PBKDF2-HMAC-SHA256 (stored in Firestore — persistent).
Session management: Delegated entirely to session_store.py (Firestore).
Google OAuth:      Verifies Google ID tokens using google-auth library.

The public API (create_session / verify_session / delete_session)
is unchanged so existing main.py session calls still work.
"""

import hashlib
import logging
import os
import secrets

from backend.session_store import (
    create_session  as _store_create,
    verify_session  as _store_verify,
    delete_session  as _store_delete,
)

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


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


# ── Google OAuth helpers ──────────────────────────────────────────────────────

def verify_google_id_token(id_token: str) -> dict | None:
    """Verify a Google ID token and return the user's profile info.

    Returns a dict with keys: sub, email, name, picture (or None on failure).

    Uses the google-auth library to verify the token against Google's
    public keys and checks the audience matches our GOOGLE_CLIENT_ID.
    """
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID not configured — cannot verify Google tokens")
        return None

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        # Verify the token — this checks signature, expiry, audience, and issuer
        idinfo = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )

        # Ensure the token was issued by Google
        if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            logger.warning("Google ID token has unexpected issuer: %s", idinfo.get("iss"))
            return None

        return {
            "sub": idinfo["sub"],            # Unique Google user ID
            "email": idinfo.get("email"),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
        }
    except ValueError as e:
        logger.warning("Google ID token verification failed: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error verifying Google ID token: %s", e)
        return None


# ── Session helpers (thin wrappers around Firestore store) ───────────────────
# These keep the same signatures that main.py already calls — no changes needed
# there.  NOTE: user_id is now a string (Firestore document ID), not an int.

def create_session(user_id: str) -> str:
    """Generate a secure token, persist it to Firestore, and return it."""
    token = secrets.token_hex(32)
    _store_create(token, user_id)
    return token


def verify_session(token: str) -> str | None:
    """Return user_id if the token is valid and not expired, else None."""
    return _store_verify(token)


def delete_session(token: str) -> None:
    """Delete a session from Firestore (called on logout)."""
    _store_delete(token)
