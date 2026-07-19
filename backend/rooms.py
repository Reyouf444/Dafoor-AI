"""
Multiplayer room management for Dafoor AI Live Quiz.

Rooms are stored in Firestore under the "rooms" collection, keyed by a
6-character uppercase code (e.g. "A3F8C2").  This allows multiple Cloud Run
instances to share state without in-memory coupling.

Room lifecycle:
  lobby    → question → reveal → question → reveal → ... → ended

Polling flow (frontend polls /api/rooms/{code}/state every 1.5 s):
  - Host POST /api/rooms/create      create room + quiz
  - Guests POST /api/rooms/{code}/join
  - Host POST /api/rooms/{code}/start
  - Players POST /api/rooms/{code}/answer
  - Server auto-reveals when all answered OR time expires (checked on poll)
  - Host POST /api/rooms/{code}/next  advance to next question
  - Final state "ended" shown to all
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

QUESTION_TIME_LIMIT_SECONDS = 20   # per-question countdown
ROOM_TTL_HOURS = 4                 # rooms auto-expire after 4 hours


# ── Lazy Firestore client (reuse database._get_db) ───────────────────────────

def _db():
    from backend.database import _get_db
    return _get_db()


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def create_room(
    host_user_id: str,
    host_username: str,
    quiz_id: str,
    client_questions: list,   # stripped questions (no answers) sent to clients
    full_questions: list,     # full questions with correct_index / correct_answer_text
    time_limit_per_q: int = QUESTION_TIME_LIMIT_SECONDS,
) -> str:
    """Create a new room. Returns the 6-char room code."""
    code = _unique_code()
    now = datetime.now(tz=timezone.utc)

    _db().collection("rooms").document(code).set({
        "host_user_id":      host_user_id,
        "host_username":     host_username,
        "quiz_id":           quiz_id,
        "client_questions":  client_questions,    # list — safe to send to all players
        "full_questions":    full_questions,      # list — server-only grading data
        "status":            "lobby",
        "current_q_idx":     -1,
        "question_started_at": None,
        "question_time_limit": time_limit_per_q,
        "participants": {
            host_user_id: {
                "username": host_username,
                "score": 0,
                "answered": False,
                "answer": None,
                "answered_at": None,
                "is_host": True,
            }
        },
        "created_at": now,
        "expires_at": now + timedelta(hours=ROOM_TTL_HOURS),
    })
    logger.info("Room %s created by %s", code, host_username)
    return code


def get_room(code: str) -> dict | None:
    """Fetch full room document or None."""
    doc = _db().collection("rooms").document(code).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["code"] = doc.id

    # Lazy expiry check
    expires_at = data.get("expires_at")
    if expires_at and datetime.now(tz=timezone.utc) > expires_at:
        try:
            doc.reference.delete()
        except Exception:
            pass
        return None

    return data


def join_room(code: str, user_id: str, username: str) -> dict:
    """Add a participant to the lobby.  Returns {'ok': True} or {'error': str}."""
    room = get_room(code)
    if not room:
        return {"error": "Room not found or has expired"}
    if room["status"] != "lobby":
        return {"error": "This session has already started"}

    _db().collection("rooms").document(code).update({
        f"participants.{user_id}": {
            "username": username,
            "score": 0,
            "answered": False,
            "answer": None,
            "answered_at": None,
            "is_host": False,
        }
    })
    return {"ok": True}


def start_room(code: str, host_user_id: str) -> dict:
    """Host starts the quiz. Transitions lobby → question (index 0)."""
    room = get_room(code)
    if not room:
        return {"error": "Room not found"}
    if room["host_user_id"] != host_user_id:
        return {"error": "Only the host can start the quiz"}
    if room["status"] != "lobby":
        return {"error": "Quiz already started"}

    now = datetime.now(tz=timezone.utc)
    _db().collection("rooms").document(code).update({
        "status":              "question",
        "current_q_idx":       0,
        "question_started_at": now,
        # Reset all participant answers for question 0
        **{f"participants.{uid}.answered": False for uid in room["participants"]},
        **{f"participants.{uid}.answer": None for uid in room["participants"]},
    })
    return {"ok": True}


def submit_answer(code: str, user_id: str, answer: Any) -> dict:
    """Record a player's answer.  Auto-reveals if everyone has answered."""
    room = get_room(code)
    if not room:
        return {"error": "Room not found"}
    if room["status"] != "question":
        return {"error": "Not currently accepting answers"}
    if user_id not in room["participants"]:
        return {"error": "You are not in this room"}
    if room["participants"][user_id].get("answered"):
        return {"error": "Already answered"}

    now = datetime.now(tz=timezone.utc)
    _db().collection("rooms").document(code).update({
        f"participants.{user_id}.answered":    True,
        f"participants.{user_id}.answer":      answer,
        f"participants.{user_id}.answered_at": now,
    })

    # Re-fetch to check if everyone answered
    updated = get_room(code)
    if updated and all(p.get("answered") for p in updated["participants"].values()):
        _reveal(code, updated)

    return {"ok": True}


def check_and_advance(code: str) -> bool:
    """Called during state polling.  If current question timed out, reveal it."""
    room = get_room(code)
    if not room or room["status"] != "question":
        return False

    started_at = room.get("question_started_at")
    if not started_at:
        return False

    time_limit = room.get("question_time_limit", QUESTION_TIME_LIMIT_SECONDS)
    elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()

    if elapsed >= time_limit:
        _reveal(code, room)
        return True
    return False


def advance_question(code: str, host_user_id: str) -> dict:
    """Host advances to the next question (called after reveal phase)."""
    room = get_room(code)
    if not room:
        return {"error": "Room not found"}
    if room["host_user_id"] != host_user_id:
        return {"error": "Only the host can advance"}
    if room["status"] not in ("reveal", "question"):
        return {"error": "Cannot advance in current state"}

    next_idx = room["current_q_idx"] + 1
    total = len(room["client_questions"])

    if next_idx >= total:
        # Quiz finished
        _db().collection("rooms").document(code).update({"status": "ended"})
        return {"ok": True, "ended": True}

    now = datetime.now(tz=timezone.utc)
    _db().collection("rooms").document(code).update({
        "status":              "question",
        "current_q_idx":       next_idx,
        "question_started_at": now,
        **{f"participants.{uid}.answered": False for uid in room["participants"]},
        **{f"participants.{uid}.answer": None for uid in room["participants"]},
    })
    return {"ok": True, "ended": False}


def delete_room(code: str) -> None:
    """Delete a room document."""
    try:
        _db().collection("rooms").document(code).delete()
    except Exception as exc:
        logger.warning("Could not delete room %s: %s", code, exc)


def get_client_state(code: str, user_id: str) -> dict | None:
    """
    Return room state appropriate for a polling client.

    - During 'question': hides correct answers.
    - During 'reveal': includes correct answer + per-player correctness.
    - Always: includes scores, participant list, countdown info.
    """
    room = get_room(code)
    if not room:
        return None

    status = room["status"]
    idx = room["current_q_idx"]
    participants = room["participants"]
    total_q = len(room["client_questions"])

    # Build participant summary (sanitized)
    participant_list = [
        {
            "user_id":  uid,
            "username": p["username"],
            "score":    p["score"],
            "answered": p.get("answered", False),
            "is_host":  p.get("is_host", False),
        }
        for uid, p in participants.items()
    ]
    participant_list.sort(key=lambda x: -x["score"])  # leaderboard order

    answered_count = sum(1 for p in participants.values() if p.get("answered"))

    state: dict = {
        "code":             code,
        "status":           status,
        "host_username":    room["host_username"],
        "participant_list": participant_list,
        "answered_count":   answered_count,
        "total_players":    len(participants),
        "current_q_idx":    idx,
        "total_questions":  total_q,
        "is_host":          user_id == room["host_user_id"],
    }

    # Countdown information
    started_at = room.get("question_started_at")
    time_limit  = room.get("question_time_limit", QUESTION_TIME_LIMIT_SECONDS)
    if started_at and status == "question":
        elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
        state["seconds_remaining"] = max(0, time_limit - elapsed)
        state["time_limit"] = time_limit
    else:
        state["seconds_remaining"] = 0
        state["time_limit"] = time_limit

    # Current question
    if status in ("question", "reveal") and 0 <= idx < total_q:
        q_client = room["client_questions"][idx]
        state["question"] = q_client

        if status == "reveal":
            # Include correct answer during reveal
            q_full = room["full_questions"][idx]
            state["correct_index"]       = q_full.get("correct_index", -1)
            state["correct_answer_text"] = q_full.get("correct_answer_text", "")
            state["explanation"]         = q_full.get("explanation", "")
            state["question_type"]       = q_full.get("type", "mcq")
            # Include my answer
            my_p = participants.get(user_id, {})
            state["my_answer"]   = my_p.get("answer")
            state["my_answered"] = my_p.get("answered", False)

    return state


# ── Internal helpers ──────────────────────────────────────────────────────────

def _reveal(code: str, room: dict) -> None:
    """Grade current question answers and transition to reveal state."""
    idx = room["current_q_idx"]
    full_questions = room.get("full_questions", [])

    if idx < 0 or idx >= len(full_questions):
        _db().collection("rooms").document(code).update({"status": "reveal"})
        return

    q = full_questions[idx]
    qtype = q.get("type", "mcq")
    correct_idx = q.get("correct_index", -1)
    correct_text = q.get("correct_answer_text", "").strip().lower()

    participants = room.get("participants", {})
    score_updates: dict = {}

    for uid, p in participants.items():
        if not p.get("answered"):
            continue

        answer = p.get("answer")
        is_correct = False

        if qtype == "fillblank":
            is_correct = str(answer or "").strip().lower() == correct_text
        else:
            try:
                is_correct = int(answer) == correct_idx
            except (TypeError, ValueError):
                pass

        if is_correct:
            # Bonus: answer faster = more points (max 1000, min 500)
            answered_at = p.get("answered_at")
            started_at  = room.get("question_started_at")
            time_limit  = room.get("question_time_limit", QUESTION_TIME_LIMIT_SECONDS)

            speed_bonus = 0
            if answered_at and started_at:
                elapsed = max(0, (answered_at - started_at).total_seconds())
                fraction_remaining = max(0, 1 - elapsed / max(time_limit, 1))
                speed_bonus = int(500 * fraction_remaining)

            base_points = 500
            points_earned = base_points + speed_bonus
        else:
            points_earned = 0

        new_score = p.get("score", 0) + points_earned
        score_updates[f"participants.{uid}.score"] = new_score

    updates = {"status": "reveal", **score_updates}
    _db().collection("rooms").document(code).update(updates)
    logger.debug("Room %s: revealed Q%d, awarded scores", code, idx)


def _unique_code() -> str:
    """Generate a unique 6-char room code."""
    db = _db()
    for _ in range(10):
        code = secrets.token_hex(3).upper()
        if not db.collection("rooms").document(code).get().exists:
            return code
    return uuid.uuid4().hex[:6].upper()
