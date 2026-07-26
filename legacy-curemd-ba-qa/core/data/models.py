"""
Data Layer — SQLModel models and shared database.

Provides ORM models for the core system tables:
- LLM call logs, budget tracking, module registry, scheduled jobs, etc.
Reuses the existing config/databases.py for CureMD SQL Server connections.
"""

import sqlite3
import json
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CORE_DB = DATA_DIR / "oneagent.db"


class CoreDB:
    """SQLite database for OneAgent core data."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = Path(db_path) if db_path else CORE_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS modules (
                name TEXT PRIMARY KEY,
                description TEXT,
                version TEXT DEFAULT '1.0',
                enabled INTEGER DEFAULT 1,
                manifest_json TEXT DEFAULT '{}',
                registered_at REAL
            );

            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT,
                task_class TEXT,
                prompt TEXT,
                result_preview TEXT,
                success INTEGER,
                cost_usd REAL,
                duration_ms INTEGER,
                created_at REAL
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL
            );

            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                source TEXT,
                payload TEXT,
                created_at REAL
            );
        """)
        self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> List[Dict]:
        cursor = self._conn.execute(sql, params)
        if sql.strip().upper().startswith("SELECT"):
            return [dict(row) for row in cursor.fetchall()]
        self._conn.commit()
        return [{"affected": cursor.rowcount}]

    def register_module(self, name: str, description: str, manifest: Dict):
        self._conn.execute(
            """INSERT OR REPLACE INTO modules (name, description, manifest_json, registered_at)
               VALUES (?, ?, ?, ?)""",
            (name, description, json.dumps(manifest), time.time()),
        )
        self._conn.commit()

    def get_module(self, name: str) -> Optional[Dict]:
        row = self._conn.execute("SELECT * FROM modules WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    def list_modules(self) -> List[Dict]:
        return [dict(r) for r in self._conn.execute("SELECT * FROM modules ORDER BY name").fetchall()]

    def log_task(self, module: str, task_class: str, prompt: str, result: str, success: bool, cost: float, duration_ms: int):
        self._conn.execute(
            """INSERT INTO task_history (module, task_class, prompt, result_preview, success, cost_usd, duration_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (module, task_class, prompt[:500], result[:500], int(success), cost, duration_ms, time.time()),
        )
        self._conn.commit()

    def set_preference(self, key: str, value: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )
        self._conn.commit()

    def get_preference(self, key: str, default: str = "") -> str:
        row = self._conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def log_event(self, event_type: str, source: str = "", payload: str = ""):
        self._conn.execute(
            "INSERT INTO event_log (event_type, source, payload, created_at) VALUES (?, ?, ?, ?)",
            (event_type, source, payload, time.time()),
        )
        self._conn.commit()

    def close(self):
        self._conn.close()


_db: Optional[CoreDB] = None


def get_core_db() -> CoreDB:
    global _db
    if _db is None:
        _db = CoreDB()
    return _db
