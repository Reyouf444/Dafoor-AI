"""
Firestore-backed session store for Dafoor AI.

Why Firestore?
- Zero extra infrastructure — it's a GCP managed service
- Cloud Run's service account can access it with a single IAM binding
- Survives container restarts, instance scale-in/out, and re-deployments
- Built-in TTL via Firestore's document expiry (no cron needed)

Collection layout:
    sessions/
        <token>/
            user_id:    int
            created_at: timestamp
            expires_at: timestamp   ← used for TTL + validation

Environment variables:
    FIRESTORE_PROJECT_ID  — GCP project ID (optional: defaults to ADC project)
    SESSION_TTL_HOURS     — how long a session lives (default: 72 hours)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

SESSION_TTL_HOURS   = int(os.getenv("SESSION_TTL_HOURS", "72"))
FIRESTORE_PROJECT   = os.getenv("FIRESTORE_PROJECT_ID")   # None → uses ADC project
COLLECTION_NAME     = "sessions"

# ── Lazy Firestore client ─────────────────────────────────────────────────────
# We initialise once and reuse — Firestore client is thread-safe.

_db = None

def _get_db():
    """Return a cached Firestore client, initialising it on first call."""
    global _db
    if _db is None:
        try:
            from google.cloud import firestore
            _db = firestore.Client(project=FIRESTORE_PROJECT)
            logger.info("Firestore session store initialised (project=%s)", _db.project)
        except Exception as exc:
            logger.error(
                "Failed to initialise Firestore client: %s. "
                "Sessions will NOT persist across restarts.",
                exc,
            )
            raise
    return _db


# ── Public API ────────────────────────────────────────────────────────────────

def create_session(token: str, user_id: str) -> None:
    """Write a new session document to Firestore."""
    now        = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(hours=SESSION_TTL_HOURS)

    _get_db().collection(COLLECTION_NAME).document(token).set({
        "user_id":    user_id,
        "created_at": now,
        "expires_at": expires_at,
    })
    logger.debug("Session created for user_id=%s, expires=%s", user_id, expires_at)


def verify_session(token: str) -> str | None:
    """Return user_id for a valid, non-expired token, or None."""
    if not token:
        return None

    try:
        doc = _get_db().collection(COLLECTION_NAME).document(token).get()
    except Exception as exc:
        logger.error("Firestore read error during session verify: %s", exc)
        return None

    if not doc.exists:
        return None

    data       = doc.to_dict()
    expires_at = data.get("expires_at")

    # Guard against expired sessions (Firestore TTL may not have cleaned up yet)
    if expires_at and datetime.now(tz=timezone.utc) > expires_at:
        # Lazily delete the stale document
        try:
            doc.reference.delete()
        except Exception:
            pass
        return None

    return data.get("user_id")


def delete_session(token: str) -> None:
    """Remove a session document (logout)."""
    if not token:
        return
    try:
        _get_db().collection(COLLECTION_NAME).document(token).delete()
        logger.debug("Session deleted: %s…", token[:8])
    except Exception as exc:
        logger.warning("Could not delete session from Firestore: %s", exc)


def delete_all_user_sessions(user_id: str) -> None:
    """Remove every session belonging to a user (e.g. force-logout all devices)."""
    try:
        db   = _get_db()
        docs = db.collection(COLLECTION_NAME).where("user_id", "==", user_id).stream()
        for doc in docs:
            doc.reference.delete()
        logger.info("All sessions deleted for user_id=%s", user_id)
    except Exception as exc:
        logger.warning("Could not delete all sessions for user %s: %s", user_id, exc)
