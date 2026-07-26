"""
Agent Memory — short-term scratchpad + long-term persistent memory.

Short-term: in-context, cleared per agent run.
Long-term: SQLite-backed with importance scoring and time decay.
"""

import json
import sqlite3
import time
import math
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "memory"


@dataclass
class MemoryEntry:
    id: Optional[int] = None
    content: str = ""
    category: str = "general"
    importance: float = 0.5
    created_at: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def decay_score(self) -> float:
        age_hours = (time.time() - self.created_at) / 3600
        decay = math.exp(-0.01 * age_hours)
        return self.importance * decay * (1 + 0.1 * self.access_count)


class Scratchpad:
    """In-context short-term memory for a single agent run."""

    def __init__(self):
        self._entries: List[Dict[str, Any]] = []

    def add(self, role: str, content: str, **metadata):
        self._entries.append({"role": role, "content": content, **metadata})

    def add_observation(self, content: str):
        self.add("observation", content)

    def add_thought(self, content: str):
        self.add("thought", content)

    def add_action(self, tool: str, result: str):
        self.add("action", f"Called {tool}: {result[:500]}")

    def to_messages(self) -> List[Dict[str, str]]:
        return [{"role": "user" if e["role"] != "thought" else "assistant",
                 "content": f"[{e['role']}] {e['content']}"}
                for e in self._entries]

    def clear(self):
        self._entries.clear()

    @property
    def summary(self) -> str:
        if not self._entries:
            return "Empty scratchpad."
        return "\n".join(f"[{e['role']}] {e['content'][:200]}" for e in self._entries[-10:])


class LongTermMemory:
    """SQLite-backed persistent memory with importance scoring."""

    def __init__(self, db_path: Optional[str] = None):
        db = Path(db_path) if db_path else MEMORY_DIR / "longterm.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db), check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance REAL DEFAULT 0.5,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )"""
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_category ON memories(category)")
        self._conn.commit()

    def store(self, content: str, category: str = "general", importance: float = 0.5, **metadata) -> int:
        now = time.time()
        cur = self._conn.execute(
            """INSERT INTO memories (content, category, importance, created_at, last_accessed, access_count, metadata)
               VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (content, category, importance, now, now, json.dumps(metadata)),
        )
        self._conn.commit()
        return cur.lastrowid

    def recall(self, query: str = "", category: Optional[str] = None, limit: int = 10) -> List[MemoryEntry]:
        sql = "SELECT * FROM memories"
        conditions = []
        params = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if query:
            conditions.append("content LIKE ?")
            params.append(f"%{query}%")
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY importance DESC, last_accessed DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        entries = []
        for r in rows:
            entries.append(MemoryEntry(
                id=r[0], content=r[1], category=r[2], importance=r[3],
                created_at=r[4], last_accessed=r[5], access_count=r[6],
                metadata=json.loads(r[7]),
            ))
        return entries

    def access(self, memory_id: int):
        self._conn.execute(
            "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
            (time.time(), memory_id),
        )
        self._conn.commit()

    def forget(self, memory_id: int):
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.commit()

    def decay_cleanup(self, min_importance: float = 0.1):
        """Remove memories that have decayed below threshold."""
        entries = self.recall(limit=1000)
        removed = 0
        for e in entries:
            if e.decay_score < min_importance and e.access_count == 0:
                self.forget(e.id)
                removed += 1
        return removed


_ltm: Optional[LongTermMemory] = None


def get_long_term_memory() -> LongTermMemory:
    global _ltm
    if _ltm is None:
        _ltm = LongTermMemory()
    return _ltm
