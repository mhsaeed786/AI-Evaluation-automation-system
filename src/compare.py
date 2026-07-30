"""Compare measured results against vendor-advertised scores.

Produces comparison rows (measured %, advertised %, delta) plus a wide matrix
of model×benchmark measured scores for the report.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .config import Config
from .results import latest_per_model_benchmark


# Redact credentials / tokens before any error text reaches a shareable report.
# (Result JSON on disk keeps full errors for local diagnostics; only the
# generated Markdown/HTML report is scrubbed, since that is what gets shared.)
_SECRET_RE = re.compile(
    r"(sk-or-v1-[A-Za-z0-9_-]+|sk-[A-Za-z0-9._-]{12,}|gsk_[A-Za-z0-9]+|"
    r"csk[-_][A-Za-z0-9]+|hf_[A-Za-z0-9]+|sk-sp-[A-Za-z0-9._-]+|"
    r"[0-9a-f]{32}\.[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]+|"
    r"keys/[0-9a-fA-F]{8,})",
    re.IGNORECASE,
)


def _redact(s: str, n: int = 200) -> str:
    s = _SECRET_RE.sub("[REDACTED]", s or "")
    return (s[:n] + "…") if len(s) > n else s


@dataclass
class ComparisonRow:
    model: str
    benchmark: str
    metric: str
    measured: float | None      # percent, or None if not run
    advertised: float | None    # percent, or None if no reference
    delta: float | None         # measured - advertised
    n_items: int
    engine: str
    note: str = ""


def build_comparison(cfg: Config) -> list[ComparisonRow]:
    latest = latest_per_model_benchmark()
    rows: list[ComparisonRow] = []
    for (model, benchmark), rec in latest.items():
        measured = round(rec["score"] * 100.0, 2) if rec.get("n_items") else None
        advertised = cfg.advertised(model, benchmark)
        delta = round(measured - advertised, 2) if (measured is not None and advertised is not None) else None
        rows.append(ComparisonRow(
            model=model, benchmark=benchmark, metric=rec.get("metric", "acc"),
            measured=measured, advertised=advertised, delta=delta,
            n_items=rec.get("n_items", 0), engine=rec.get("engine", "?"),
            note=_redact(rec.get("errors", [""])[0]) if rec.get("errors") and not rec.get("n_items") else "",
        ))
    return rows


def measured_matrix(cfg: Config) -> tuple[list[str], list[str], dict[tuple[str, str], float | None]]:
    """Return (models, benchmarks, {(model,bench): measured_pct|None})."""
    latest = latest_per_model_benchmark()
    models = sorted({m for (m, _b) in latest})
    benches = sorted({b for (_m, b) in latest})
    grid: dict[tuple[str, str], float | None] = {}
    for m in models:
        for b in benches:
            rec = latest.get((m, b))
            grid[(m, b)] = round(rec["score"] * 100.0, 2) if rec and rec.get("n_items") else None
    return models, benches, grid
