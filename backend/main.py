import os
import json
import time
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.database import (
    init_db,
    create_user, get_user_by_id, get_user_by_username, get_user_by_email,
    get_user_by_google_sub, update_user, delete_user,
    save_pdf_record, get_pdf_by_id, get_user_pdfs, delete_pdf as db_delete_pdf, delete_user_pdfs,
    save_quiz, get_quiz_by_id, get_user_quizzes, delete_user_quizzes,
    save_quiz_attempt, get_user_analytics, delete_user_quiz_attempts,
    create_password_reset_token, get_password_reset_token, mark_reset_token_used,
    save_flashcard_deck, get_flashcard_deck, get_user_flashcard_decks, delete_flashcard_deck,
    delete_user_flashcard_decks,
)
from backend.auth import (
    hash_password, verify_password,
    create_session, verify_session, delete_session,
    verify_google_id_token,
)
from backend.pdf_parser import generate_quiz, generate_flashcards, extract_text_from_pdf, _is_arabic_text, translate_text_to_english
from backend.storage import generate_upload_signed_url, get_public_url, delete_object, download_to_temp
from backend.email_service import send_password_reset_email
from backend.session_store import delete_all_user_sessions

app = FastAPI(title="Dafoor AI")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/apple-touch-icon.png", include_in_schema=False)
def apple_touch():
    return Response(status_code=204)

# Health check endpoint — used by Cloud Run liveness probes and Dockerfile HEALTHCHECK
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "timestamp": int(time.time())}

# Enable CORS for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on server start (warms Firestore connection)
@app.on_event("startup")
def on_startup():
    init_db()

# Dependency to authenticate users via token header
# NOTE: user_id is now a string (Firestore document ID), not an int.
def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Support both "Bearer <token>" and raw "<token>"
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        
    user_id = verify_session(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired or invalid token")
    return user_id


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION API
# ═══════════════════════════════════════════════════════════════════════════════

class RegisterUser(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class LoginUser(BaseModel):
    username: str
    password: str

class GoogleAuthRequest(BaseModel):
    id_token: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@app.post("/api/auth/signup")
def signup(data: RegisterUser):
    username = data.username.strip()
    password = data.password
    email = data.email.strip().lower() if data.email else None
    
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
    # Check if user already exists
    existing = get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=400, detail="Username is already taken")

    # Check if email already in use
    if email:
        existing_email = get_user_by_email(email)
        if existing_email:
            raise HTTPException(status_code=400, detail="This email is already associated with an account")
        
    pwd_hash = hash_password(password)
    try:
        user_id = create_user(
            username=username,
            password_hash=pwd_hash,
            email=email,
            auth_provider="local",
        )
        token = create_session(user_id)
        return {"token": token, "username": username}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@app.post("/api/auth/login")
def login(data: LoginUser):
    username = data.username.strip()
    password = data.password
    
    user = get_user_by_username(username)
    if not user or not user.get("password_hash") or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    token = create_session(user["id"])
    return {"token": token, "username": username}


@app.post("/api/auth/google")
def google_auth(data: GoogleAuthRequest):
    """Sign in or sign up using a Google ID token from the frontend."""
    google_info = verify_google_id_token(data.id_token)
    if not google_info:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_sub = google_info["sub"]
    email = google_info.get("email", "")
    name = google_info.get("name", "")

    # Check if user already exists with this Google account
    user = get_user_by_google_sub(google_sub)

    if user:
        # Existing Google user — log them in
        token = create_session(user["id"])
        return {"token": token, "username": user["username"]}

    # Check if a local user exists with the same email — link accounts
    if email:
        user = get_user_by_email(email)
        if user:
            # Link Google account to existing local user
            update_user(user["id"], {"google_sub": google_sub})
            token = create_session(user["id"])
            return {"token": token, "username": user["username"]}

    # New user — auto-register
    # Generate a unique username from the Google name
    base_username = name.replace(" ", "").lower()[:20] if name else "user"
    username = base_username
    counter = 1
    while get_user_by_username(username):
        username = f"{base_username}{counter}"
        counter += 1

    user_id = create_user(
        username=username,
        password_hash=None,  # OAuth user — no password
        email=email,
        display_name=name,
        auth_provider="google",
        google_sub=google_sub,
    )
    token = create_session(user_id)
    return {"token": token, "username": username, "is_new_user": True}


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        delete_session(token)
    return {"success": True}


@app.get("/api/auth/me")
def get_me(user_id: str = Depends(get_current_user_id)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "username": user["username"],
        "email": user.get("email"),
        "display_name": user.get("display_name"),
        "auth_provider": user.get("auth_provider", "local"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  PASSWORD RESET API
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    """Send a password reset email if the email exists in the system."""
    email = data.email.strip().lower()

    # Always return success to prevent email enumeration
    user = get_user_by_email(email)
    if not user:
        return {"message": "If an account with that email exists, a reset link has been sent."}

    # Don't allow password reset for OAuth-only accounts
    if user.get("auth_provider") != "local" and not user.get("password_hash"):
        return {"message": "If an account with that email exists, a reset link has been sent."}

    token = create_password_reset_token(user["id"])
    send_password_reset_email(
        to_email=email,
        reset_token=token,
        username=user["username"],
    )

    return {"message": "If an account with that email exists, a reset link has been sent."}


@app.post("/api/auth/reset-password")
def reset_password(data: ResetPasswordRequest):
    """Reset a user's password using a valid reset token."""
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    token_data = get_password_reset_token(data.token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    user_id = token_data["user_id"]
    new_hash = hash_password(data.new_password)

    update_user(user_id, {"password_hash": new_hash})
    mark_reset_token_used(data.token)

    # Invalidate all existing sessions for security
    delete_all_user_sessions(user_id)

    return {"message": "Password has been reset successfully. Please log in with your new password."}


# ═══════════════════════════════════════════════════════════════════════════════
#  USER SETTINGS API
# ═══════════════════════════════════════════════════════════════════════════════

class UpdateSettingsRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@app.get("/api/user/settings")
def get_user_settings(user_id: str = Depends(get_current_user_id)):
    """Get the current user's settings / profile info."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "username": user["username"],
        "email": user.get("email"),
        "display_name": user.get("display_name"),
        "auth_provider": user.get("auth_provider", "local"),
        "has_password": bool(user.get("password_hash")),
        "has_google": bool(user.get("google_sub")),
        "created_at": user.get("created_at").isoformat() if hasattr(user.get("created_at"), "isoformat") else str(user.get("created_at", "")),
    }


@app.put("/api/user/settings")
def update_settings(data: UpdateSettingsRequest, user_id: str = Depends(get_current_user_id)):
    """Update profile settings (display name, email)."""
    updates = {}

    if data.display_name is not None:
        name = data.display_name.strip()
        if len(name) < 1:
            raise HTTPException(status_code=400, detail="Display name cannot be empty")
        updates["display_name"] = name

    if data.email is not None:
        email = data.email.strip().lower()
        if email:
            # Check if email is already in use by another user
            existing = get_user_by_email(email)
            if existing and existing["id"] != user_id:
                raise HTTPException(status_code=400, detail="This email is already associated with another account")
        updates["email"] = email if email else None

    if not updates:
        raise HTTPException(status_code=400, detail="No changes provided")

    update_user(user_id, updates)
    return {"message": "Settings updated successfully", **updates}


@app.put("/api/user/password")
def change_password(data: ChangePasswordRequest, user_id: str = Depends(get_current_user_id)):
    """Change the current user's password (requires current password)."""
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not user.get("password_hash") or not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = hash_password(data.new_password)
    update_user(user_id, {"password_hash": new_hash})

    return {"message": "Password changed successfully"}


@app.delete("/api/user/account")
def delete_account(user_id: str = Depends(get_current_user_id)):
    """Permanently delete the user's account and ALL associated data."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. Delete all PDFs from GCS
    gcs_paths = delete_user_pdfs(user_id)
    for path in gcs_paths:
        if path:
            try:
                delete_object(path)
            except Exception:
                pass

    # 2. Delete all quizzes and quiz attempts
    delete_user_quizzes(user_id)
    delete_user_quiz_attempts(user_id)

    # 3. Delete all sessions
    delete_all_user_sessions(user_id)

    # 4. Delete the user record
    delete_user(user_id)

    return {"message": "Account deleted successfully"}


# ═══════════════════════════════════════════════════════════════════════════════
#  PDF MANAGEMENT API
# ═══════════════════════════════════════════════════════════════════════════════

# ── Step 1 of GCS upload flow ────────────────────────────────────────────────
class RequestUploadBody(BaseModel):
    filename: str        # original filename from the browser
    file_size: int       # byte size reported by the browser

@app.post("/api/pdfs/request-upload")
def request_upload(
    body: RequestUploadBody,
    user_id: str = Depends(get_current_user_id)
):
    """Return a signed GCS PUT URL.

    The client should PUT the PDF bytes directly to `signed_url` with
    Content-Type: application/pdf, then call /api/pdfs/confirm-upload.
    """
    if not body.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        result = generate_upload_signed_url(
            user_id=user_id,
            original_filename=body.filename
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not generate upload URL: {exc}")

    return {
        "signed_url": result["signed_url"],
        "gcs_path":   result["gcs_path"],
        "expires_at": result["expires_at"],
    }


# ── Step 2 of GCS upload flow ────────────────────────────────────────────────
class ConfirmUploadBody(BaseModel):
    filename: str    # original filename (for display)
    gcs_path: str    # object path returned by request-upload
    file_size: int   # byte size (client-reported, for display)

@app.post("/api/pdfs/confirm-upload")
def confirm_upload(
    body: ConfirmUploadBody,
    user_id: str = Depends(get_current_user_id)
):
    """Record PDF metadata in the database after a successful GCS upload."""
    # Basic sanity check — make sure the path belongs to this user
    expected_prefix = f"pdfs/{user_id}/"
    if not body.gcs_path.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Invalid GCS path for this user")

    public_url = get_public_url(body.gcs_path)

    pdf_id = save_pdf_record(
        user_id=user_id,
        filename=body.filename,
        file_path=body.gcs_path,
        file_size=body.file_size,
    )

    return {
        "id":         pdf_id,
        "filename":   body.filename,
        "file_size":  body.file_size,
        "public_url": public_url,
    }


@app.get("/api/pdfs")
def list_pdfs(user_id: str = Depends(get_current_user_id)):
    pdfs = get_user_pdfs(user_id)
    # Attach a public URL to each row
    for pdf in pdfs:
        pdf["public_url"] = get_public_url(pdf["file_path"])
    return pdfs


@app.delete("/api/pdfs/{pdf_id}")
def delete_pdf_endpoint(pdf_id: str, user_id: str = Depends(get_current_user_id)):
    pdf = get_pdf_by_id(pdf_id, user_id)
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF document not found")

    # Delete object from GCS
    delete_object(pdf["file_path"])

    # Remove metadata from DB
    db_delete_pdf(pdf_id)
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════════
#  QUIZ API
# ═══════════════════════════════════════════════════════════════════════════════

class QuizGenRequest(BaseModel):
    pdf_id: Optional[str] = None
    num_questions: int
    difficulty: str
    time_limit: int
    gemini_api_key: Optional[str] = None
    language_mode: Optional[str] = "auto"  # 'auto' | 'arabic' | 'translate'
    question_types: Optional[List[str]] = None  # ['mcq','truefalse','fillblank','mixed']


@app.get("/api/pdfs/{pdf_id}/language")
def detect_pdf_language(
    pdf_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Download a PDF from GCS, extract text, and detect if it's Arabic."""
    pdf = get_pdf_by_id(pdf_id, user_id)
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")

    tmp_path = None
    try:
        tmp_path = download_to_temp(pdf["file_path"])
        text = extract_text_from_pdf(tmp_path)
        language = "arabic" if _is_arabic_text(text) else "english"
        return {"language": language, "pdf_id": pdf_id}
    except Exception as e:
        # If we can't read it, default to english so no disruption
        return {"language": "english", "pdf_id": pdf_id, "note": str(e)}
    finally:
        if tmp_path:
            try:
                import os as _os
                _os.remove(tmp_path)
            except Exception:
                pass

@app.post("/api/quizzes/generate")
def generate_new_quiz(
    req: QuizGenRequest,
    user_id: str = Depends(get_current_user_id)
):
    pdf_path = None
    title = "General Knowledge Quiz"
    
    effective_pdf_id = req.pdf_id if (req.pdf_id and str(req.pdf_id).lower() not in ("null", "nan", "undefined", "")) else None

    if effective_pdf_id:
        pdf = get_pdf_by_id(effective_pdf_id, user_id)
        if not pdf:
            raise HTTPException(status_code=404, detail="Selected PDF not found")
        pdf_path = pdf["file_path"]
        title = f"Quiz from {pdf['filename']}"
        
    # Generate questions using parser engine
    tmp_path = None
    try:
        if pdf_path:
            # Download GCS object to a temp file so pdfminer can read it
            tmp_path = download_to_temp(pdf_path)
        
        # Handle language mode for Arabic PDFs
        effective_language_mode = req.language_mode or "auto"
        if tmp_path and effective_language_mode == "translate" and req.gemini_api_key:
            # Translate Arabic content to English first, then generate questions
            from backend.pdf_parser import extract_text_from_pdf as _extract
            raw_text = _extract(tmp_path)
            translated_text = translate_text_to_english(raw_text, req.gemini_api_key)
            questions = generate_quiz(
                pdf_path=None,  # pass None so we use text directly
                count=req.num_questions,
                difficulty=req.difficulty,
                api_key=req.gemini_api_key,
                pre_extracted_text=translated_text
            )
        else:
            questions = generate_quiz(
                pdf_path=tmp_path,
                count=req.num_questions,
                difficulty=req.difficulty,
                api_key=req.gemini_api_key,
                language_mode=effective_language_mode,
                question_types=req.question_types,
            )
    finally:
        if tmp_path:
            try:
                import os as _os
                _os.remove(tmp_path)
            except Exception:
                pass
    
    if not questions:
        raise HTTPException(status_code=500, detail="Failed to generate questions. Try another document.")
        
    config_json = json.dumps({
        "num_questions": req.num_questions,
        "difficulty": req.difficulty,
        "time_limit": req.time_limit
    })
    
    questions_json = json.dumps(questions)
    
    # Store full quiz in DB (including answers)
    quiz_id = save_quiz(
        user_id=user_id,
        pdf_id=effective_pdf_id,
        title=title,
        config_json=config_json,
        questions_json=questions_json,
    )
    
    # Create safe version of questions to send to client (removing answers)
    client_questions = []
    for idx, q in enumerate(questions):
        client_questions.append({
            "index": idx,
            "question": q["question"],
            "choices": q["choices"]
        })
        
    return {
        "quiz_id": quiz_id,
        "title": title,
        "time_limit": req.time_limit,
        "questions": client_questions
    }


@app.get("/api/quizzes/history")
def get_user_quiz_history(user_id: str = Depends(get_current_user_id)):
    """List all saved quizzes for the current user (used for multiplayer host mode)."""
    quizzes = get_user_quizzes(user_id)
    return {"quizzes": quizzes}

class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: List  # int index for mcq/truefalse, str for fillblank, -1/"" for skipped
    time_spent_seconds: int

@app.post("/api/quizzes/submit")
def submit_quiz_answers(
    req: QuizSubmitRequest,
    user_id: str = Depends(get_current_user_id)
):
    # Fetch quiz from DB
    quiz = get_quiz_by_id(req.quiz_id, user_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz session not found")
        
    original_questions = json.loads(quiz["questions"])
    submitted_answers = req.answers
    
    if len(submitted_answers) != len(original_questions):
        raise HTTPException(status_code=400, detail="Incorrect number of answers submitted")
        
    correct_count = 0
    breakdown = []
    
    for idx, q in enumerate(original_questions):
        user_ans = submitted_answers[idx]
        correct_ans = q["correct_index"]
        qtype = q.get("type", "mcq")

        if qtype == "fillblank":
            # Strict exact match (case-insensitive, stripped)
            correct_text = str(q.get("correct_answer_text", "")).strip().lower()
            user_text = str(user_ans or "").strip().lower()
            is_correct = (user_text == correct_text) and bool(correct_text)
        else:
            # MCQ and True/False: compare integer indices
            try:
                is_correct = int(user_ans) == correct_ans
            except (TypeError, ValueError):
                is_correct = False

        if is_correct:
            correct_count += 1
            
        breakdown.append({
            "index": idx,
            "question": q["question"],
            "type": qtype,
            "choices": q.get("choices", []),
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "correct_answer_text": q.get("correct_answer_text", ""),
            "is_correct": is_correct,
            "explanation": q.get("explanation", "")
        })
        
    score = (correct_count / len(original_questions)) * 100.0
    
    # Save attempt in DB
    save_quiz_attempt(
        user_id=user_id,
        quiz_id=req.quiz_id,
        score=score,
        total_questions=len(original_questions),
        correct_answers=correct_count,
        time_spent_seconds=req.time_spent_seconds,
    )
    
    return {
        "score": round(score, 1),
        "total_questions": len(original_questions),
        "correct_answers": correct_count,
        "time_spent_seconds": req.time_spent_seconds,
        "breakdown": breakdown
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS API
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/analytics")
def get_analytics(user_id: str = Depends(get_current_user_id)):
    return get_user_analytics(user_id)


# ═══════════════════════════════════════════════════════════════════════════
#  FLASHCARDS API
# ═══════════════════════════════════════════════════════════════════════════

class FlashcardGenRequest(BaseModel):
    pdf_id: Optional[str] = None
    card_count: int = 20
    gemini_api_key: Optional[str] = None


@app.post("/api/flashcards/generate")
def generate_flashcard_deck(
    req: FlashcardGenRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Generate a flashcard deck from a PDF (or general content) and save it."""
    title = "General Flashcards"
    text = ""
    pdf_id = req.pdf_id

    if pdf_id:
        pdf = get_pdf_by_id(pdf_id, user_id)
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        title = f"Flashcards: {pdf['filename']}"
        tmp_path = None
        try:
            tmp_path = download_to_temp(pdf["file_path"])
            text = extract_text_from_pdf(tmp_path)
        finally:
            if tmp_path:
                try:
                    import os as _os
                    _os.remove(tmp_path)
                except Exception:
                    pass

    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from the PDF. Try another document.")

    cards = generate_flashcards(text=text, count=req.card_count, api_key=req.gemini_api_key)
    if not cards:
        raise HTTPException(status_code=500, detail="Could not generate flashcards. Try providing a Gemini API key.")

    deck_id = save_flashcard_deck(
        user_id=user_id,
        pdf_id=pdf_id,
        title=title,
        cards_json=json.dumps(cards),
    )
    return {"deck_id": deck_id, "title": title, "card_count": len(cards), "cards": cards}


@app.get("/api/flashcards")
def list_flashcard_decks(user_id: str = Depends(get_current_user_id)):
    """List all saved flashcard decks for the current user."""
    return get_user_flashcard_decks(user_id)


@app.get("/api/flashcards/{deck_id}")
def get_flashcard_deck_endpoint(deck_id: str, user_id: str = Depends(get_current_user_id)):
    """Get a specific flashcard deck with all cards."""
    deck = get_flashcard_deck(deck_id, user_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Flashcard deck not found")
    return deck


@app.delete("/api/flashcards/{deck_id}")
def delete_flashcard_deck_endpoint(deck_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete a flashcard deck."""
    deck = get_flashcard_deck(deck_id, user_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Flashcard deck not found")
    delete_flashcard_deck(deck_id)
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════
#  MULTIPLAYER ROOMS API
# ═══════════════════════════════════════════════════════════════════════════

from backend import rooms as room_mgr

class CreateRoomRequest(BaseModel):
    quiz_id: str
    time_limit_per_q: Optional[int] = 20  # seconds per question

class JoinRoomRequest(BaseModel):
    username: Optional[str] = None  # override display name

class AnswerRequest(BaseModel):
    answer: object  # int for mcq/truefalse, str for fillblank


@app.post("/api/rooms/create")
def create_room(
    req: CreateRoomRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Host creates a live quiz room from an existing quiz."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    quiz = get_quiz_by_id(req.quiz_id, user_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    full_questions = json.loads(quiz["questions"])
    client_questions = [
        {
            "index": i,
            "type": q.get("type", "mcq"),
            "question": q["question"],
            "choices": q.get("choices", []),
        }
        for i, q in enumerate(full_questions)
    ]

    host_username = user.get("display_name") or user["username"]
    code = room_mgr.create_room(
        host_user_id=user_id,
        host_username=host_username,
        quiz_id=req.quiz_id,
        client_questions=client_questions,
        full_questions=full_questions,
        time_limit_per_q=req.time_limit_per_q or 20,
    )
    return {"code": code, "quiz_title": quiz["title"], "total_questions": len(full_questions)}


@app.post("/api/rooms/{code}/join")
def join_room(
    code: str,
    req: JoinRoomRequest,
    user_id: str = Depends(get_current_user_id)
):
    """A player joins an existing room."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    username = req.username or user.get("display_name") or user["username"]
    result = room_mgr.join_room(code.upper(), user_id, username)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/rooms/{code}/state")
def get_room_state(
    code: str,
    user_id: str = Depends(get_current_user_id)
):
    """Poll room state.  Also checks for question timeout and auto-reveals."""
    room_mgr.check_and_advance(code.upper())
    state = room_mgr.get_client_state(code.upper(), user_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Room not found or expired")
    return state


@app.post("/api/rooms/{code}/start")
def start_room(
    code: str,
    user_id: str = Depends(get_current_user_id)
):
    """Host starts the quiz."""
    result = room_mgr.start_room(code.upper(), user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/rooms/{code}/answer")
def submit_room_answer(
    code: str,
    req: AnswerRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Submit an answer for the current question."""
    result = room_mgr.submit_answer(code.upper(), user_id, req.answer)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/rooms/{code}/next")
def advance_room(
    code: str,
    user_id: str = Depends(get_current_user_id)
):
    """Host advances to the next question."""
    result = room_mgr.advance_question(code.upper(), user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.delete("/api/rooms/{code}")
def delete_room(
    code: str,
    user_id: str = Depends(get_current_user_id)
):
    """Host ends and deletes the room."""
    room_mgr.delete_room(code.upper())
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════════
#  SERVE FRONTEND SPA
# ═══════════════════════════════════════════════════════════════════════════════

# Mount static files folder
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static"), html=True), name="static")
