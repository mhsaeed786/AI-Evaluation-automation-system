"""Result records + persistence.

Each (model, benchmark) run is stored as one JSON file under ``results/``.
The report/comparison layer reads the whole directory back to build tables and
deltas. Records are intentionally self-describing (they carry the config that
produced them) so a stale result is never confused with a fresh one.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import RESULTS_DIR


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


@dataclass
class ResultRecord:
    model: str
    benchmark: str
    metric: str
    score: float                       # 0..1
    n_items: int
    engine: str
    base_url: str
    seed: int
    temperature: float
    n_shot: int
    limit: int | None
    cot: bool = False
    timestamp: str = ""
    errors: list[str] = field(default_factory=list)
    sample_predictions: list[dict] = field(default_factory=list)

    @property
    def percent(self) -> float:
        return round(self.score * 100.0, 2)

    def to_dict(self) -> dict:
        return asdict(self)


def save_result(record: ResultRecord, results_dir: Path = RESULTS_DIR) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    if not record.timestamp:
        record.timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"{_safe(record.model)}__{_safe(record.benchmark)}__{record.timestamp}.json"
    path = results_dir / fname
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record.to_dict(), fh, indent=2, ensure_ascii=False)
    return path


def load_all_results(results_dir: Path = RESULTS_DIR) -> list[dict]:
    if not results_dir.exists():
        return []
    out = []
    for p in sorted(results_dir.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                out.append(json.load(fh))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def latest_per_model_benchmark(results_dir: Path = RESULTS_DIR) -> dict[tuple[str, str], dict]:
    """Collapse to the most recent record per (model, benchmark)."""
    records = load_all_results(results_dir)
    best: dict[tuple[str, str], dict] = {}
    for r in records:
        key = (r.get("model"), r.get("benchmark"))
        prev = best.get(key)
        if prev is None or r.get("timestamp", "") >= prev.get("timestamp", ""):
            best[key] = r
    return best
