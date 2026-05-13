#!/usr/bin/env python3
"""
PureBrain IR — Authentication module.
User registration, login, session management with bcrypt + signed cookies.
"""

import hashlib
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "purebrain_ir.db"

# Session signing key — generate once, persist in .env
SESSION_SECRET = os.environ.get(
    "PUREBRAIN_IR_SESSION_SECRET",
    "pbir-session-secret-change-in-production-2026",
)
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days in seconds

serializer = URLSafeTimedSerializer(SESSION_SECRET)

MIN_PASSWORD_LENGTH = 8


def _get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_tables():
    """Create users and sessions tables if they don't exist."""
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ir_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ir_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES ir_users(id)
        )
    """)
    conn.commit()
    conn.close()


def seed_default_user():
    """Pre-seed the purebrain/declaration2026 account if it doesn't exist."""
    conn = _get_db()
    existing = conn.execute(
        "SELECT id FROM ir_users WHERE username = ?", ("purebrain",)
    ).fetchone()
    if not existing:
        pw_hash = bcrypt.hashpw(b"declaration2026", bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO ir_users (username, email, password_hash) VALUES (?, ?, ?)",
            ("purebrain", "admin@purebrain.ai", pw_hash),
        )
        conn.commit()
    conn.close()


def register_user(username: str, email: str, password: str) -> dict:
    """Register a new user. Returns dict with success/error."""
    username = username.strip().lower()
    email = email.strip().lower()

    if not username or not email or not password:
        return {"error": "All fields are required."}

    if len(username) < 3:
        return {"error": "Username must be at least 3 characters."}

    if len(password) < MIN_PASSWORD_LENGTH:
        return {"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters."}

    if "@" not in email or "." not in email:
        return {"error": "Please enter a valid email address."}

    conn = _get_db()

    # Check unique username
    if conn.execute("SELECT id FROM ir_users WHERE username = ?", (username,)).fetchone():
        conn.close()
        return {"error": "Username already taken."}

    # Check unique email
    if conn.execute("SELECT id FROM ir_users WHERE email = ?", (email,)).fetchone():
        conn.close()
        return {"error": "Email already registered."}

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn.execute(
        "INSERT INTO ir_users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, pw_hash),
    )
    conn.commit()
    conn.close()
    return {"success": True, "username": username}


def authenticate_user(username: str, password: str) -> dict:
    """Verify credentials. Returns user dict or error."""
    username = username.strip().lower()
    conn = _get_db()
    user = conn.execute(
        "SELECT id, username, email, password_hash FROM ir_users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()

    if not user:
        return {"error": "Invalid username or password."}

    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return {"error": "Invalid username or password."}

    return {"success": True, "user_id": user["id"], "username": user["username"]}


def create_session(user_id: int, username: str) -> str:
    """Create a server-side session and return the session token."""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE)

    conn = _get_db()
    conn.execute(
        "INSERT INTO ir_sessions (session_id, user_id, username, expires_at) VALUES (?, ?, ?, ?)",
        (session_id, user_id, username, expires_at.isoformat()),
    )
    conn.commit()
    conn.close()

    # Sign the session ID for the cookie
    return serializer.dumps(session_id)


def validate_session(token: str) -> dict | None:
    """Validate a session token. Returns user info or None."""
    try:
        session_id = serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

    conn = _get_db()
    session = conn.execute(
        "SELECT user_id, username, expires_at FROM ir_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()

    if not session:
        return None

    # Check expiry
    expires = datetime.fromisoformat(session["expires_at"])
    if datetime.utcnow() > expires:
        destroy_session(token)
        return None

    return {"user_id": session["user_id"], "username": session["username"]}


def destroy_session(token: str):
    """Remove a session from the database."""
    try:
        session_id = serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return

    conn = _get_db()
    conn.execute("DELETE FROM ir_sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def destroy_user_sessions(user_id: int):
    """Revoke all sessions for a user (e.g., on password change)."""
    conn = _get_db()
    conn.execute("DELETE FROM ir_sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def cleanup_expired_sessions():
    """Remove expired sessions from the database."""
    conn = _get_db()
    conn.execute(
        "DELETE FROM ir_sessions WHERE expires_at < ?",
        (datetime.utcnow().isoformat(),),
    )
    conn.commit()
    conn.close()


# Initialize on import
init_tables()
seed_default_user()
