"""
LLM Response Cache — avoids re-calling providers for identical prompts.

SQLite-backed with content-hash keys. Same prompt + model = same response,
returned instantly with $0 cost.
"""

import hashlib
import json
import sqlite3
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "llm_cache"


def _content_hash(messages: list[dict], model: str, **kwargs) -> str:
    """Deterministic hash of prompt + model + relevant params."""
    payload = json.dumps(
        {"messages": messages, "model": model, "k": {k: v for k, v in kwargs.items() if k in ("temperature", "max_tokens", "response_format")}},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class LLMCache:
    """SQLite-backed prompt/response cache."""

    def __init__(self, db_path: Optional[str] = None):
        db = Path(db_path) if db_path else CACHE_DIR / "cache.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db), check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS cache (
                hash TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                response TEXT NOT NULL,
                created_at REAL NOT NULL,
                last_used REAL NOT NULL,
                hit_count INTEGER DEFAULT 1
            )"""
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_last_used ON cache(last_used)")
        self._conn.commit()

    def get(self, messages: list[dict], model: str, **kwargs) -> Optional[Dict[str, Any]]:
        h = _content_hash(messages, model, **kwargs)
        row = self._conn.execute(
            "SELECT response, hit_count FROM cache WHERE hash = ?", (h,)
        ).fetchone()
        if row is None:
            return None
        self._conn.execute(
            "UPDATE cache SET last_used = ?, hit_count = ? WHERE hash = ?",
            (time.time(), row[1] + 1, h),
        )
        self._conn.commit()
        return json.loads(row[0])

    def put(
        self,
        messages: list[dict],
        model: str,
        response: Dict[str, Any],
        provider: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        **kwargs,
    ):
        h = _content_hash(messages, model, **kwargs)
        now = time.time()
        self._conn.execute(
            """INSERT OR REPLACE INTO cache
               (hash, provider, model, prompt_tokens, completion_tokens, response, created_at, last_used, hit_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (h, provider, model, prompt_tokens, completion_tokens, json.dumps(response), now, now),
        )
        self._conn.commit()

    def evict(self, max_age_days: int = 30):
        """Remove entries older than max_age_days."""
        cutoff = time.time() - (max_age_days * 86400)
        cur = self._conn.execute("DELETE FROM cache WHERE last_used < ?", (cutoff,))
        self._conn.commit()
        return cur.rowcount

    def stats(self) -> Dict[str, Any]:
        total = self._conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        hits = self._conn.execute("SELECT SUM(hit_count) FROM cache").fetchone()[0] or 0
        tokens_saved = self._conn.execute(
            "SELECT SUM(prompt_tokens + completion_tokens) FROM cache"
        ).fetchone()[0] or 0
        return {"entries": total, "total_hits": hits, "tokens_saved": tokens_saved}

    def close(self):
        self._conn.close()


_cache: Optional[LLMCache] = None


def get_cache() -> LLMCache:
    global _cache
    if _cache is None:
        _cache = LLMCache()
    return _cache
