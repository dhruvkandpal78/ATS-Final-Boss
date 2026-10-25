"""SQLite database storage for user authentication and CV analysis history.

Zero external dependencies: uses Python standard library sqlite3 and hashlib.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data" / "ats_history.db"

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Database:
    def __init__(self, db_path: Optional[str | Path] = None):
        if db_path is None:
            env_path = os.environ.get("ATS_DB_PATH")
            self.db_path = Path(env_path) if env_path else DEFAULT_DB_PATH
        elif str(db_path) == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path)

        if self.db_path != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._shared_conn = None
        else:
            # In-memory database must keep a single persistent connection
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")

        self.init_db()

    @contextmanager
    def _connect(self):
        if self._shared_conn is not None:
            yield self._shared_conn
            return
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        with self._connect() as conn:
            if self.db_path != ":memory:":
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")

            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    document_name TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    snippet TEXT NOT NULL DEFAULT '',
                    decision TEXT NOT NULL,
                    score REAL,
                    score_kind TEXT DEFAULT '',
                    findings_count INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_submissions_user_id ON submissions(user_id);
                CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON submissions(created_at);
            """)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()

    def register_user(self, username: str, email: str, password: str) -> dict[str, Any]:
        username = (username or "").strip()
        email = (email or "").strip().lower()

        if not USERNAME_RE.match(username):
            raise ValueError("Username must be 3-30 characters with letters, numbers, underscores, or hyphens.")
        if not EMAIL_RE.match(email) or len(email) > 100:
            raise ValueError("A valid email address is required.")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")
        if len(password) > 256:
            raise ValueError("Password is too long (maximum 256 characters).")

        salt = secrets.token_hex(16)
        pwd_hash = self._hash_password(password, salt)
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            # Check existing username
            existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                raise ValueError("Username is already taken. Please choose another.")
            existing_email = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing_email:
                raise ValueError("An account with this email already exists.")

            cursor = conn.execute(
                "INSERT INTO users (username, email, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, email, pwd_hash, salt, now),
            )
            user_id = cursor.lastrowid

        return {"id": user_id, "username": username, "email": email, "created_at": now}

    def authenticate_user(self, username_or_email: str, password: str) -> dict[str, Any]:
        identifier = (username_or_email or "").strip()
        if not identifier or not password:
            raise ValueError("Username/email and password are required.")

        with self._connect() as conn:
            user = conn.execute(
                "SELECT id, username, email, password_hash, salt, created_at FROM users WHERE username = ? OR email = ?",
                (identifier, identifier.lower()),
            ).fetchone()

        if not user:
            raise ValueError("Invalid username/email or password.")

        expected_hash = self._hash_password(password, user["salt"])
        if not hmac.compare_digest(expected_hash, user["password_hash"]):
            raise ValueError("Invalid username/email or password.")

        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "created_at": user["created_at"],
        }

    def create_session(self, user_id: int, days: int = 30) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        created_at = now.isoformat()
        expires_at = (now + timedelta(days=days)).isoformat()

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, created_at, expires_at),
            )
        return token

    def get_user_by_session(self, token: Optional[str]) -> Optional[dict[str, Any]]:
        if not token or not isinstance(token, str):
            return None
        token = token.strip()
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.username, u.email, u.created_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ? AND s.expires_at > ?
                """,
                (token, now),
            ).fetchone()

        if row:
            return {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "created_at": row["created_at"],
            }
        return None

    def delete_session(self, token: Optional[str]) -> bool:
        if not token:
            return False
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE token = ?", (token.strip(),))
            return cursor.rowcount > 0

    def save_submission(
        self,
        user_id: int,
        document_name: str,
        mode: str,
        snippet: str,
        decision: str,
        score: Optional[float],
        score_kind: str,
        findings_count: int,
        result_json: str,
    ) -> dict[str, Any]:
        document_name = (document_name or "Resume").strip()[:150]
        mode = mode if mode in ("text", "pdf") else "text"
        snippet = (snippet or "").strip()[:500]
        decision = decision or "unknown"
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO submissions (
                    user_id, document_name, mode, snippet, decision, score, score_kind, findings_count, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, document_name, mode, snippet, decision, score, score_kind, findings_count, result_json, now),
            )
            submission_id = cursor.lastrowid

        return {
            "id": submission_id,
            "user_id": user_id,
            "document_name": document_name,
            "mode": mode,
            "snippet": snippet,
            "decision": decision,
            "score": score,
            "score_kind": score_kind,
            "findings_count": findings_count,
            "created_at": now,
        }

    def get_user_submissions(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, document_name, mode, snippet, decision, score, score_kind, findings_count, created_at
                FROM submissions
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, max(1, min(limit, 200))),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_user_submission_count(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM submissions WHERE user_id = ?", (user_id,)).fetchone()
            return row["total"] if row else 0

    def get_submission_detail(self, submission_id: int, user_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, user_id, document_name, mode, snippet, decision, score, score_kind, findings_count, result_json, created_at
                FROM submissions
                WHERE id = ? AND user_id = ?
                """,
                (submission_id, user_id),
            ).fetchone()

        if not row:
            return None
        return dict(row)

    def delete_submission(self, submission_id: int, user_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM submissions WHERE id = ? AND user_id = ?",
                (submission_id, user_id),
            )
            return cursor.rowcount > 0


# Default global instance
_DB_INSTANCE: Optional[Database] = None


def get_db() -> Database:
    global _DB_INSTANCE
    if _DB_INSTANCE is None:
        _DB_INSTANCE = Database()
    return _DB_INSTANCE
