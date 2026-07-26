"""
User Profile — stores user info, ambitions, and recurring-task ledger.

The profile drives the meta-agent's decisions about what modules
to generate and how to optimize the user's workflow.
"""

import json
import time
import sqlite3
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROFILE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "profile"


@dataclass
class RecurringTask:
    id: str
    name: str
    description: str
    frequency: str  # daily, weekly, monthly, on-demand
    module: str = ""
    last_run: Optional[float] = None
    run_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class UserProfile:
    """User profile and recurring-task manager."""

    def __init__(self, db_path: Optional[str] = None):
        db = Path(db_path) if db_path else PROFILE_DIR / "profile.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db), check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS profile (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL
            )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS recurring_tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                frequency TEXT,
                module TEXT,
                last_run REAL,
                run_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS task_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT,
                module TEXT,
                count INTEGER DEFAULT 1,
                first_seen REAL,
                last_seen REAL
            )"""
        )
        self._conn.commit()

    def set(self, key: str, value: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO profile (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )
        self._conn.commit()

    def get(self, key: str, default: str = "") -> str:
        row = self._conn.execute("SELECT value FROM profile WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def get_all(self) -> Dict[str, str]:
        rows = self._conn.execute("SELECT key, value FROM profile").fetchall()
        return dict(rows)

    def add_recurring_task(self, task: RecurringTask):
        self._conn.execute(
            """INSERT OR REPLACE INTO recurring_tasks (id, name, description, frequency, module, last_run, run_count, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (task.id, task.name, task.description, task.frequency, task.module, task.last_run, task.run_count, json.dumps(task.metadata)),
        )
        self._conn.commit()

    def get_recurring_tasks(self) -> List[RecurringTask]:
        rows = self._conn.execute("SELECT * FROM recurring_tasks").fetchall()
        return [RecurringTask(
            id=r[0], name=r[1], description=r[2], frequency=r[3],
            module=r[4], last_run=r[5], run_count=r[6],
            metadata=json.loads(r[7]),
        ) for r in rows]

    def record_task_pattern(self, pattern: str, module: str):
        """Track recurring task patterns for the meta-agent."""
        existing = self._conn.execute(
            "SELECT id, count FROM task_patterns WHERE pattern = ? AND module = ?",
            (pattern, module),
        ).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE task_patterns SET count = ?, last_seen = ? WHERE id = ?",
                (existing[1] + 1, time.time(), existing[0]),
            )
        else:
            self._conn.execute(
                "INSERT INTO task_patterns (pattern, module, count, first_seen, last_seen) VALUES (?, ?, 1, ?, ?)",
                (pattern, module, time.time(), time.time()),
            )
        self._conn.commit()

    def get_frequent_patterns(self, min_count: int = 3) -> List[Dict]:
        """Get task patterns that occur frequently — candidates for auto-module generation."""
        rows = self._conn.execute(
            "SELECT pattern, module, count, first_seen, last_seen FROM task_patterns WHERE count >= ? ORDER BY count DESC",
            (min_count,),
        ).fetchall()
        return [
            {"pattern": r[0], "module": r[1], "count": r[2], "first_seen": r[3], "last_seen": r[4]}
            for r in rows
        ]


_profile: Optional[UserProfile] = None


def get_profile() -> UserProfile:
    global _profile
    if _profile is None:
        _profile = UserProfile()
    return _profile
