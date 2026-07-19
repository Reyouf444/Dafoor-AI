"""
Firestore-backed database layer for Dafoor AI.

Migrated from SQLite to Firestore to solve the critical data-loss problem:
SQLite lived inside the ephemeral Cloud Run container — every time Cloud Run
scaled down (min-instances=0, ~15-20 min idle) or replaced a container,
ALL user data was destroyed.

Firestore is a serverless, fully managed NoSQL database on GCP.  Data persists
across container restarts, scale events, and re-deployments.

Collections:
    users/{user_id}           — user accounts + auth info
    pdfs/{pdf_id}             — PDF metadata (files live in GCS)
    quizzes/{quiz_id}         — generated quiz content
    quiz_attempts/{attempt_id} — score history
    password_resets/{token}   — time-limited password reset tokens

Environment variables:
    FIRESTORE_PROJECT_ID  — GCP project (optional: defaults to ADC project)
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

FIRESTORE_PROJECT = os.getenv("FIRESTORE_PROJECT_ID")  # None → uses ADC project

# ── Lazy Firestore client ─────────────────────────────────────────────────────

_db = None


def _get_db():
    """Return a cached Firestore client, initialising it on first call."""
    global _db
    if _db is None:
        try:
            from google.cloud import firestore
            _db = firestore.Client(project=FIRESTORE_PROJECT)
            logger.info("Firestore database layer initialised (project=%s)", _db.project)
        except Exception as exc:
            logger.error("Failed to initialise Firestore client: %s", exc)
            raise
    return _db


# ── Initialisation (no-op for Firestore — schemaless) ────────────────────────

def init_db():
    """Initialise the database.

    For Firestore this simply warms the client connection.
    No schema creation is needed — collections are created on first write.
    """
    _get_db()
    logger.info("Firestore database ready.")


# ══════════════════════════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════════════════════════

def create_user(
    username: str,
    password_hash: str | None = None,
    email: str | None = None,
    display_name: str | None = None,
    auth_provider: str = "local",
    google_sub: str | None = None,
) -> str:
    """Create a new user and return their generated user_id (string)."""
    db = _get_db()
    user_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc)

    doc_data = {
        "username": username,
        "password_hash": password_hash,
        "email": email,
        "display_name": display_name or username,
        "auth_provider": auth_provider,
        "google_sub": google_sub,
        "created_at": now,
        "updated_at": now,
    }
    db.collection("users").document(user_id).set(doc_data)
    logger.info("User created: id=%s, username=%s, provider=%s", user_id, username, auth_provider)
    return user_id


def get_user_by_id(user_id: str) -> dict | None:
    """Fetch a user document by ID.  Returns dict with 'id' key, or None."""
    doc = _get_db().collection("users").document(user_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def get_user_by_username(username: str) -> dict | None:
    """Fetch a user by username (unique lookup)."""
    db = _get_db()
    docs = db.collection("users").where("username", "==", username).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def get_user_by_email(email: str) -> dict | None:
    """Fetch a user by email address."""
    if not email:
        return None
    db = _get_db()
    docs = db.collection("users").where("email", "==", email).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def get_user_by_google_sub(google_sub: str) -> dict | None:
    """Fetch a user by Google OAuth subject ID."""
    db = _get_db()
    docs = db.collection("users").where("google_sub", "==", google_sub).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def update_user(user_id: str, updates: dict) -> None:
    """Partial update of a user document."""
    updates["updated_at"] = datetime.now(tz=timezone.utc)
    _get_db().collection("users").document(user_id).update(updates)
    logger.info("User updated: id=%s, fields=%s", user_id, list(updates.keys()))


def delete_user(user_id: str) -> None:
    """Delete a user document."""
    _get_db().collection("users").document(user_id).delete()
    logger.info("User deleted: id=%s", user_id)


# ══════════════════════════════════════════════════════════════════════════════
#  PDFs
# ══════════════════════════════════════════════════════════════════════════════

def save_pdf_record(user_id: str, filename: str, file_path: str, file_size: int) -> str:
    """Store PDF metadata in Firestore. Returns the generated pdf_id."""
    db = _get_db()
    pdf_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc)

    db.collection("pdfs").document(pdf_id).set({
        "user_id": user_id,
        "filename": filename,
        "file_path": file_path,
        "file_size": file_size,
        "uploaded_at": now,
    })
    return pdf_id


def get_pdf_by_id(pdf_id: str, user_id: str) -> dict | None:
    """Fetch a single PDF owned by the given user."""
    doc = _get_db().collection("pdfs").document(pdf_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    if data.get("user_id") != user_id:
        return None
    data["id"] = doc.id
    return data


def get_user_pdfs(user_id: str) -> list[dict]:
    """List all PDFs for a user, most recent first."""
    db = _get_db()
    docs = db.collection("pdfs").where("user_id", "==", user_id).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        # Convert Firestore timestamp to ISO string for JSON serialisation
        if hasattr(data.get("uploaded_at"), "isoformat"):
            data["uploaded_at"] = data["uploaded_at"].isoformat()
        results.append(data)
    results.sort(key=lambda x: str(x.get("uploaded_at", "")), reverse=True)
    return results


def delete_pdf(pdf_id: str) -> None:
    """Delete a PDF metadata document."""
    _get_db().collection("pdfs").document(pdf_id).delete()


def delete_user_pdfs(user_id: str) -> list[str]:
    """Delete all PDF records for a user.  Returns list of GCS paths for cleanup."""
    db = _get_db()
    docs = db.collection("pdfs").where("user_id", "==", user_id).stream()
    gcs_paths = []
    for doc in docs:
        data = doc.to_dict()
        gcs_paths.append(data.get("file_path", ""))
        doc.reference.delete()
    return gcs_paths


# ══════════════════════════════════════════════════════════════════════════════
#  QUIZZES
# ══════════════════════════════════════════════════════════════════════════════

def save_quiz(user_id: str, pdf_id: str | None, title: str, config_json: str, questions_json: str) -> str:
    """Store a generated quiz. Returns the quiz_id."""
    db = _get_db()
    quiz_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc)

    db.collection("quizzes").document(quiz_id).set({
        "user_id": user_id,
        "pdf_id": pdf_id,
        "title": title,
        "config": config_json,
        "questions": questions_json,
        "created_at": now,
    })
    return quiz_id


def get_quiz_by_id(quiz_id: str, user_id: str) -> dict | None:
    """Fetch a quiz owned by the given user."""
    doc = _get_db().collection("quizzes").document(quiz_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    if data.get("user_id") != user_id:
        return None
    data["id"] = doc.id
    return data


def get_user_quizzes(user_id: str) -> list[dict]:
    """List all saved quizzes for a user, most recent first."""
    db = _get_db()
    docs = db.collection("quizzes").where("user_id", "==", user_id).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append({
            "id": doc.id,
            "title": data.get("title", "Untitled Quiz"),
            "pdf_id": data.get("pdf_id"),
            "created_at": data.get("created_at").isoformat() if hasattr(data.get("created_at"), "isoformat") else str(data.get("created_at", "")),
        })
    results.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return results


def delete_user_quizzes(user_id: str) -> None:
    """Delete all quizzes for a user."""
    db = _get_db()
    docs = db.collection("quizzes").where("user_id", "==", user_id).stream()
    for doc in docs:
        doc.reference.delete()


# ══════════════════════════════════════════════════════════════════════════════
#  QUIZ ATTEMPTS (Score History)
# ══════════════════════════════════════════════════════════════════════════════

def save_quiz_attempt(
    user_id: str,
    quiz_id: str,
    score: float,
    total_questions: int,
    correct_answers: int,
    time_spent_seconds: int,
) -> str:
    """Record a quiz attempt. Returns the attempt_id."""
    db = _get_db()
    attempt_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc)

    db.collection("quiz_attempts").document(attempt_id).set({
        "user_id": user_id,
        "quiz_id": quiz_id,
        "score": score,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "time_spent_seconds": time_spent_seconds,
        "attempted_at": now,
    })
    return attempt_id


def get_user_analytics(user_id: str) -> dict:
    """Compute analytics for a user: summary stats + history list.

    Returns:
        {
            "summary": {"total_quizzes": int, "avg_score": float, "total_time_seconds": int},
            "history": [ {score, time_spent_seconds, attempted_at, title}, ... ]
        }
    """
    db = _get_db()

    # Fetch all attempts for this user
    attempts_docs = db.collection("quiz_attempts").where("user_id", "==", user_id).stream()

    attempts = []
    total_score = 0.0
    total_time = 0

    for doc in attempts_docs:
        data = doc.to_dict()
        attempts.append(data)
        total_score += data.get("score", 0)
        total_time += data.get("time_spent_seconds", 0)

    attempts.sort(key=lambda x: str(x.get("attempted_at", "")))

    total_quizzes = len(attempts)
    avg_score = round(total_score / total_quizzes, 1) if total_quizzes > 0 else 0.0

    # Enrich history with quiz titles (batch-read quiz docs)
    quiz_id_set = {a.get("quiz_id") for a in attempts if a.get("quiz_id")}
    quiz_titles = {}
    for qid in quiz_id_set:
        qdoc = db.collection("quizzes").document(qid).get()
        if qdoc.exists:
            quiz_titles[qid] = qdoc.to_dict().get("title", "Untitled Quiz")
        else:
            quiz_titles[qid] = "Deleted Quiz"

    history = []
    for a in attempts:
        attempted_at = a.get("attempted_at")
        if hasattr(attempted_at, "isoformat"):
            attempted_at = attempted_at.isoformat()
        history.append({
            "score": a.get("score"),
            "time_spent_seconds": a.get("time_spent_seconds"),
            "attempted_at": attempted_at,
            "title": quiz_titles.get(a.get("quiz_id"), "Unknown Quiz"),
        })

    return {
        "summary": {
            "total_quizzes": total_quizzes,
            "avg_score": avg_score,
            "total_time_seconds": total_time,
        },
        "history": history,
    }


def delete_user_quiz_attempts(user_id: str) -> None:
    """Delete all quiz attempts for a user."""
    db = _get_db()
    docs = db.collection("quiz_attempts").where("user_id", "==", user_id).stream()
    for doc in docs:
        doc.reference.delete()


# ══════════════════════════════════════════════════════════════════════════════
#  PASSWORD RESETS
# ══════════════════════════════════════════════════════════════════════════════

PASSWORD_RESET_TTL_MINUTES = 60  # reset links valid for 1 hour


def create_password_reset_token(user_id: str) -> str:
    """Generate and store a password reset token. Returns the token string."""
    import secrets
    db = _get_db()
    token = secrets.token_urlsafe(48)
    now = datetime.now(tz=timezone.utc)

    db.collection("password_resets").document(token).set({
        "user_id": user_id,
        "created_at": now,
        "expires_at": now + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
        "used": False,
    })
    return token


def get_password_reset_token(token: str) -> dict | None:
    """Fetch a password reset token document if it's valid and unused."""
    doc = _get_db().collection("password_resets").document(token).get()
    if not doc.exists:
        return None
    data = doc.to_dict()

    # Check expiry
    expires_at = data.get("expires_at")
    if expires_at and datetime.now(tz=timezone.utc) > expires_at:
        # Lazily delete expired token
        doc.reference.delete()
        return None

    # Check if already used
    if data.get("used"):
        return None

    data["token"] = doc.id
    return data


def mark_reset_token_used(token: str) -> None:
    """Mark a password reset token as used."""
    _get_db().collection("password_resets").document(token).update({"used": True})


# ══════════════════════════════════════════════════════════════════════════════
#  FLASHCARD DECKS
# ══════════════════════════════════════════════════════════════════════════════

def save_flashcard_deck(user_id: str, pdf_id: str | None, title: str, cards_json: str) -> str:
    """Store a flashcard deck. Returns the deck_id."""
    import json as _json
    db = _get_db()
    deck_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc)

    db.collection("flashcard_decks").document(deck_id).set({
        "user_id": user_id,
        "pdf_id": pdf_id,
        "title": title,
        "cards": cards_json,
        "card_count": len(_json.loads(cards_json)),
        "created_at": now,
    })
    return deck_id


def get_flashcard_deck(deck_id: str, user_id: str) -> dict | None:
    """Fetch a flashcard deck owned by the given user."""
    doc = _get_db().collection("flashcard_decks").document(deck_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    if data.get("user_id") != user_id:
        return None
    data["id"] = doc.id
    if hasattr(data.get("created_at"), "isoformat"):
        data["created_at"] = data["created_at"].isoformat()
    return data


def get_user_flashcard_decks(user_id: str) -> list[dict]:
    """List all flashcard decks for a user, most recent first."""
    db = _get_db()
    docs = db.collection("flashcard_decks").where("user_id", "==", user_id).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if hasattr(data.get("created_at"), "isoformat"):
            data["created_at"] = data["created_at"].isoformat()
        data.pop("cards", None)  # Don't include full card data in index
        results.append(data)
    results.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return results


def delete_flashcard_deck(deck_id: str) -> None:
    """Delete a flashcard deck."""
    _get_db().collection("flashcard_decks").document(deck_id).delete()


def delete_user_flashcard_decks(user_id: str) -> None:
    """Delete all flashcard decks for a user."""
    db = _get_db()
    docs = db.collection("flashcard_decks").where("user_id", "==", user_id).stream()
    for doc in docs:
        doc.reference.delete()

