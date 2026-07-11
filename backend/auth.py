import hashlib
import secrets
from backend.database import execute_write, execute_read_one

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # Iterations
    )
    return f"{salt}:{key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its PBKDF2 hash."""
    try:
        salt, key_hex = hashed.split(":")
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return secrets.compare_digest(key, new_key)
    except Exception:
        return False

def create_session(user_id: int) -> str:
    """Create a new session token for the user."""
    token = secrets.token_hex(32)
    execute_write(
        "INSERT INTO sessions (token, user_id) VALUES (?, ?)",
        (token, user_id)
    )
    return token

def verify_session(token: str) -> int:
    """Verify session token and return user_id, or None if invalid."""
    if not token:
        return None
    session = execute_read_one(
        "SELECT user_id FROM sessions WHERE token = ?",
        (token,)
    )
    return session['user_id'] if session else None

def delete_session(token: str):
    """Delete a session token (logout)."""
    if token:
        execute_write("DELETE FROM sessions WHERE token = ?", (token,))
