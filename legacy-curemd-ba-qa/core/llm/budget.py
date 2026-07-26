"""
Budget Tracker — enforces per-day $ ceilings and logs every LLM call.

Every call through the router is logged here. If a budget ceiling is hit,
the router will refuse the call and raise BudgetExceeded.
"""

import sqlite3
import time
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BUDGET_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "budget"


class BudgetExceeded(Exception):
    """Raised when a call would exceed the configured budget."""
    pass


@dataclass
class BudgetConfig:
    daily_limit_usd: float = 5.0
    per_task_limits: Dict[str, float] = field(default_factory=dict)
    per_module_limits: Dict[str, float] = field(default_factory=dict)
    warn_at_pct: float = 0.8


class BudgetTracker:
    """Track and enforce LLM spending."""

    def __init__(self, db_path: Optional[str] = None, config: Optional[BudgetConfig] = None):
        db = Path(db_path) if db_path else BUDGET_DIR / "spend.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db), check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS spend_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                date TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                task_class TEXT,
                module TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                cost_usd REAL NOT NULL,
                cached INTEGER DEFAULT 0
            )"""
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_spend_date ON spend_log(date)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_spend_module ON spend_log(module)")
        self._conn.commit()
        self.config = config or BudgetConfig()

    def log_call(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        task_class: Optional[str] = None,
        module: Optional[str] = None,
        cached: bool = False,
    ):
        now = time.time()
        today = date.today().isoformat()
        self._conn.execute(
            """INSERT INTO spend_log (ts, date, provider, model, task_class, module, prompt_tokens, completion_tokens, cost_usd, cached)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (now, today, provider, model, task_class, module, prompt_tokens, completion_tokens, cost_usd, int(cached)),
        )
        self._conn.commit()

    def check_budget(self, task_class: Optional[str] = None, module: Optional[str] = None) -> bool:
        """Return True if the call is within budget, raise BudgetExceeded if not."""
        today = date.today().isoformat()

        daily_spend = self._conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM spend_log WHERE date = ? AND cached = 0",
            (today,),
        ).fetchone()[0]

        if daily_spend >= self.config.daily_limit_usd:
            raise BudgetExceeded(
                f"Daily limit ${self.config.daily_limit_usd:.2f} reached (${daily_spend:.4f} spent)"
            )

        if daily_spend >= self.config.daily_limit_usd * self.config.warn_at_pct:
            logger.warning(
                f"Budget warning: ${daily_spend:.4f} / ${self.config.daily_limit_usd:.2f} "
                f"({daily_spend / self.config.daily_limit_usd * 100:.0f}%)"
            )

        if task_class and task_class in self.config.per_task_limits:
            task_spend = self._conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM spend_log WHERE date = ? AND task_class = ? AND cached = 0",
                (today, task_class),
            ).fetchone()[0]
            if task_spend >= self.config.per_task_limits[task_class]:
                raise BudgetExceeded(
                    f"Task '{task_class}' limit ${self.config.per_task_limits[task_class]:.2f} reached"
                )

        if module and module in self.config.per_module_limits:
            mod_spend = self._conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM spend_log WHERE date = ? AND module = ? AND cached = 0",
                (today, module),
            ).fetchone()[0]
            if mod_spend >= self.config.per_module_limits[module]:
                raise BudgetExceeded(
                    f"Module '{module}' limit ${self.config.per_module_limits[module]:.2f} reached"
                )

        return True

    def get_daily_summary(self, target_date: Optional[str] = None) -> Dict:
        d = target_date or date.today().isoformat()
        rows = self._conn.execute(
            "SELECT provider, model, SUM(prompt_tokens), SUM(completion_tokens), SUM(cost_usd), COUNT(*) "
            "FROM spend_log WHERE date = ? GROUP BY provider, model",
            (d,),
        ).fetchall()
        total = self._conn.execute(
            "SELECT SUM(cost_usd) FROM spend_log WHERE date = ? AND cached = 0", (d,)
        ).fetchone()[0] or 0
        cached = self._conn.execute(
            "SELECT COUNT(*) FROM spend_log WHERE date = ? AND cached = 1", (d,)
        ).fetchone()[0]
        by_provider = {}
        for r in rows:
            by_provider.setdefault(r[0], []).append({
                "model": r[1], "prompt_tokens": r[2], "completion_tokens": r[3],
                "cost_usd": r[4], "calls": r[5],
            })
        return {"date": d, "total_usd": total, "cached_calls": cached, "by_provider": by_provider}

    def get_module_summary(self, target_date: Optional[str] = None) -> Dict[str, float]:
        d = target_date or date.today().isoformat()
        rows = self._conn.execute(
            "SELECT module, SUM(cost_usd) FROM spend_log WHERE date = ? AND cached = 0 GROUP BY module",
            (d,),
        ).fetchall()
        return {r[0] or "unknown": r[1] for r in rows}


_tracker: Optional[BudgetTracker] = None


def get_budget_tracker() -> BudgetTracker:
    global _tracker
    if _tracker is None:
        _tracker = BudgetTracker()
    return _tracker
