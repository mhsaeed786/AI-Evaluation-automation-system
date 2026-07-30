"""
Auth — single auth layer for OneAgent.

Supports API key authentication and basic session management.
Reuses HealthOS's existing auth patterns for database access.
"""

import hashlib
import secrets
import time
import sqlite3
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

AUTH_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "auth"


@dataclass
class User:
    username: str
    role: str = "user"  # admin, user, viewer
    api_key: Optional[str] = None
    created_at: float = 0.0
    last_login: float = 0.0
    enabled: bool = True


class AuthManager:
    """Simple API-key-based auth for OneAgent."""

    def __init__(self, db_path: Optional[str] = None):
        db = Path(db_path) if db_path else AUTH_DIR / "auth.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db), check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                role TEXT DEFAULT 'user',
                api_key_hash TEXT,
                api_key_prefix TEXT,
                created_at REAL,
                last_login REAL,
                enabled INTEGER DEFAULT 1
            )"""
        )
        self._conn.commit()

    def create_user(self, username: str, role: str = "user") -> str:
        """Create a user and return their API key."""
        api_key = f"oa_{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:8]
        self._conn.execute(
            """INSERT OR REPLACE INTO users (username, role, api_key_hash, api_key_prefix, created_at, last_login, enabled)
               VALUES (?, ?, ?, ?, ?, 0, 1)""",
            (username, role, key_hash, key_prefix, time.time()),
        )
        self._conn.commit()
        return api_key

    def authenticate(self, api_key: str) -> Optional[User]:
        """Verify an API key and return the user."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        row = self._conn.execute(
            "SELECT username, role, last_login, enabled FROM users WHERE api_key_hash = ?",
            (key_hash,),
        ).fetchone()
        if not row or not row[3]:
            return None
        self._conn.execute(
            "UPDATE users SET last_login = ? WHERE username = ?",
            (time.time(), row[0]),
        )
        self._conn.commit()
        return User(username=row[0], role=row[1], last_login=row[2])

    def list_users(self) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT username, role, api_key_prefix, created_at, last_login, enabled FROM users"
        ).fetchall()
        return [
            {"username": r[0], "role": r[1], "key_prefix": r[2],
             "created_at": r[3], "last_login": r[4], "enabled": bool(r[5])}
            for r in rows
        ]

    def delete_user(self, username: str):
        self._conn.execute("DELETE FROM users WHERE username = ?", (username,))
        self._conn.commit()


_auth: Optional[AuthManager] = None


def get_auth() -> AuthManager:
    global _auth
    if _auth is None:
        _auth = AuthManager()
    return _auth
