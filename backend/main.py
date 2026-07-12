import os
import shutil
import json
import time
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.database import init_db, execute_write, execute_read_one, execute_read_all
from backend.auth import hash_password, verify_password, create_session, verify_session, delete_session
from backend.pdf_parser import generate_quiz
from backend.storage import generate_upload_signed_url, get_public_url, delete_object

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

# Initialize database tables on server start
@app.on_event("startup")
def on_startup():
    init_db()

# Dependency to authenticate users via token header
def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
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


# --- Authentication API ---

class RegisterUser(BaseModel):
    username: str
    password: str

class LoginUser(BaseModel):
    username: str
    password: str

@app.post("/api/auth/signup")
def signup(data: RegisterUser):
    username = data.username.strip()
    password = data.password
    
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
    # Check if user already exists
    existing = execute_read_one("SELECT id FROM users WHERE username = ?", (username,))
    if existing:
        raise HTTPException(status_code=400, detail="Username is already taken")
        
    pwd_hash = hash_password(password)
    try:
        user_id = execute_write(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, pwd_hash)
        )
        token = create_session(user_id)
        return {"token": token, "username": username}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.post("/api/auth/login")
def login(data: LoginUser):
    username = data.username.strip()
    password = data.password
    
    user = execute_read_one("SELECT * FROM users WHERE username = ?", (username,))
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    token = create_session(user["id"])
    return {"token": token, "username": username}

@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        delete_session(token)
    return {"success": True}

@app.get("/api/auth/me")
def get_me(user_id: int = Depends(get_current_user_id)):
    user = execute_read_one("SELECT username FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user["username"]}


# --- PDF Management API ---

# ── Step 1 of GCS upload flow ────────────────────────────────────────────────
class RequestUploadBody(BaseModel):
    filename: str        # original filename from the browser
    file_size: int       # byte size reported by the browser

@app.post("/api/pdfs/request-upload")
def request_upload(
    body: RequestUploadBody,
    user_id: int = Depends(get_current_user_id)
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
    user_id: int = Depends(get_current_user_id)
):
    """Record PDF metadata in the database after a successful GCS upload."""
    # Basic sanity check — make sure the path belongs to this user
    expected_prefix = f"pdfs/{user_id}/"
    if not body.gcs_path.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Invalid GCS path for this user")

    public_url = get_public_url(body.gcs_path)

    pdf_id = execute_write(
        "INSERT INTO pdfs (user_id, filename, file_path, file_size) VALUES (?, ?, ?, ?)",
        (user_id, body.filename, body.gcs_path, body.file_size)
    )

    return {
        "id":         pdf_id,
        "filename":   body.filename,
        "file_size":  body.file_size,
        "public_url": public_url,
    }


@app.get("/api/pdfs")
def list_pdfs(user_id: int = Depends(get_current_user_id)):
    pdfs = execute_read_all(
        "SELECT id, filename, file_path, file_size, uploaded_at FROM pdfs WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,)
    )
    # Attach a public URL to each row
    for pdf in pdfs:
        pdf["public_url"] = get_public_url(pdf["file_path"])
    return pdfs


@app.delete("/api/pdfs/{pdf_id}")
def delete_pdf(pdf_id: int, user_id: int = Depends(get_current_user_id)):
    pdf = execute_read_one(
        "SELECT * FROM pdfs WHERE id = ? AND user_id = ?",
        (pdf_id, user_id)
    )
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF document not found")

    # Delete object from GCS (file_path now stores the GCS object path)
    delete_object(pdf["file_path"])

    # Remove metadata from DB
    execute_write("DELETE FROM pdfs WHERE id = ?", (pdf_id,))
    return {"success": True}


# --- Quiz API ---

import re

class QuizGenRequest(BaseModel):
    pdf_id: Optional[int] = None
    num_questions: int
    difficulty: str
    time_limit: int
    gemini_api_key: Optional[str] = None

@app.post("/api/quizzes/generate")
def generate_new_quiz(
    req: QuizGenRequest,
    user_id: int = Depends(get_current_user_id)
):
    pdf_path = None
    title = "General Knowledge Quiz"
    
    if req.pdf_id:
        pdf = execute_read_one(
            "SELECT * FROM pdfs WHERE id = ? AND user_id = ?",
            (req.pdf_id, user_id)
        )
        if not pdf:
            raise HTTPException(status_code=404, detail="Selected PDF not found")
        pdf_path = pdf["file_path"]
        title = f"Quiz from {pdf['filename']}"
        
    # Generate questions using parser engine
    questions = generate_quiz(
        pdf_path=pdf_path,
        count=req.num_questions,
        difficulty=req.difficulty,
        api_key=req.gemini_api_key
    )
    
    if not questions:
        raise HTTPException(status_code=500, detail="Failed to generate questions. Try another document.")
        
    config_json = json.dumps({
        "num_questions": req.num_questions,
        "difficulty": req.difficulty,
        "time_limit": req.time_limit
    })
    
    questions_json = json.dumps(questions)
    
    # Store full quiz in DB (including answers)
    quiz_id = execute_write(
        "INSERT INTO quizzes (pdf_id, user_id, title, config, questions) VALUES (?, ?, ?, ?, ?)",
        (req.pdf_id, user_id, title, config_json, questions_json)
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

class QuizSubmitRequest(BaseModel):
    quiz_id: int
    answers: List[int] # List of chosen indices, -1 for skipped
    time_spent_seconds: int

@app.post("/api/quizzes/submit")
def submit_quiz_answers(
    req: QuizSubmitRequest,
    user_id: int = Depends(get_current_user_id)
):
    # Fetch quiz from DB
    quiz = execute_read_one(
        "SELECT * FROM quizzes WHERE id = ? AND user_id = ?",
        (req.quiz_id, user_id)
    )
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
        is_correct = (user_ans == correct_ans)
        if is_correct:
            correct_count += 1
            
        breakdown.append({
            "index": idx,
            "question": q["question"],
            "choices": q["choices"],
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "explanation": q.get("explanation", "")
        })
        
    score = (correct_count / len(original_questions)) * 100.0
    
    # Save attempt in DB
    execute_write(
        """INSERT INTO quiz_attempts 
        (quiz_id, user_id, score, total_questions, correct_answers, time_spent_seconds) 
        VALUES (?, ?, ?, ?, ?, ?)""",
        (req.quiz_id, user_id, score, len(original_questions), correct_count, req.time_spent_seconds)
    )
    
    return {
        "score": round(score, 1),
        "total_questions": len(original_questions),
        "correct_answers": correct_count,
        "time_spent_seconds": req.time_spent_seconds,
        "breakdown": breakdown
    }


# --- Analytics API ---

@app.get("/api/analytics")
def get_analytics(user_id: int = Depends(get_current_user_id)):
    # 1. Historical scores for plotting
    attempts = execute_read_all(
        """SELECT qa.score, qa.time_spent_seconds, qa.attempted_at, q.title 
        FROM quiz_attempts qa
        JOIN quizzes q ON qa.quiz_id = q.id
        WHERE qa.user_id = ? 
        ORDER BY qa.attempted_at ASC""",
        (user_id,)
    )
    
    # 2. General statistics
    summary = execute_read_one(
        """SELECT 
            COUNT(*) as total_quizzes,
            AVG(score) as avg_score,
            SUM(time_spent_seconds) as total_time
        FROM quiz_attempts 
        WHERE user_id = ?""",
        (user_id,)
    )
    
    total_quizzes = summary["total_quizzes"] if summary and summary["total_quizzes"] else 0
    avg_score = round(summary["avg_score"], 1) if summary and summary["avg_score"] is not None else 0.0
    total_time = summary["total_time"] if summary and summary["total_time"] else 0
    
    return {
        "summary": {
            "total_quizzes": total_quizzes,
            "avg_score": avg_score,
            "total_time_seconds": total_time
        },
        "history": attempts
    }


# --- Serve Frontend SPA ---

# Mount static files folder
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static"), html=True), name="static")
