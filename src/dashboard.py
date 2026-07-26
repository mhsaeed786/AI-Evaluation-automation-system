"""Data layer for the web dashboard.

Pure functions that read ``results/`` + the YAML configs and return
JSON-friendly structures. Kept separate from the Flask app (``src/server.py``)
so the logic can be reused and unit-tested without a web framework, and so a
``report.py``-style static generator could share it later.

Every lookup collapses the full run history to the NEWEST record per
(provider, model, benchmark) — re-running a benchmark simply refreshes its
value. Provider is derived from each record's ``base_url``.
"""
from __future__ import annotations

from urllib.parse import urlparse

from .config import Config, PROVIDERS
from .results import load_all_results

# Best-effort reverse map: default base_url -> provider name.
_URL_TO_PROVIDER = {
    default.rstrip("/").lower(): name
    for name, (_api_type, _url_var, _key_var, default) in PROVIDERS.items()
}


def provider_for_base_url(base_url: str) -> str:
    if not base_url:
        return "unknown"
    key = base_url.rstrip("/").lower()
    if key in _URL_TO_PROVIDER:
        return _URL_TO_PROVIDER[key]
    host = (urlparse(base_url).hostname or base_url or "unknown").lower()
    return host


def _pct(rec: dict):
    """Measured percent for one record, or None when nothing was evaluated."""
    if not rec.get("n_items"):
        return None
    try:
        return round(float(rec.get("score")) * 100.0, 2)
    except (TypeError, ValueError):
        return None


def _latest(records) -> dict:
    """Newest record per (provider, model, benchmark)."""
    best: dict = {}
    for r in records:
        key = (provider_for_base_url(r.get("base_url", "")),
               r.get("model"), r.get("benchmark"))
        prev = best.get(key)
        if prev is None or (r.get("timestamp", "") or "") >= (prev.get("timestamp", "") or ""):
            best[key] = r
    return best


def _records() -> list:
    return load_all_results()


def overview(cfg: Config) -> dict:
    best = _latest(_records())
    vals = [v for v in (_pct(r) for r in best.values()) if v is not None]
    avg = round(sum(vals) / len(vals), 2) if vals else 0.0
    model_best: dict = {}
    for (_prov, model, _bench), r in best.items():
        p = _pct(r)
        if p is not None:
            model_best.setdefault(model, []).append(p)
    if model_best:
        top_model, top_score = max(((m, max(ps)) for m, ps in model_best.items()),
                                   key=lambda kv: kv[1])
    else:
        top_model, top_score = None, 0.0
    model_avg = {m: round(sum(ps) / len(ps), 2) for m, ps in model_best.items()}
    return {
        "n_models": len({m for (_p, m, _b) in best}),
        "n_benchmarks": len({b for (_p, _m, b) in best}),
        "n_providers": len({p for (p, _m, _b) in best}),
        "n_runs": len(_records()),
        "avg_score": avg,
        "top_model": top_model,
        "top_score": top_score,
        "providers": sorted({p for (p, _m, _b) in best}),
        "model_avg": model_avg,
    }


def matrix(cfg: Config) -> dict:
    best = _latest(_records())
    models = sorted({m for (_p, m, _b) in best})
    benches = sorted({b for (_p, _m, b) in best})
    cells: dict = {}
    meta: dict = {}
    for (prov, model, bench), r in best.items():
        cells.setdefault(model, {})[bench] = _pct(r)
        meta[f"{model}::{bench}"] = {"engine": r.get("engine", "?"),
                                     "provider": prov, "n": r.get("n_items", 0)}
    return {"models": models, "benchmarks": benches, "cells": cells, "meta": meta}


def deltas(cfg: Config) -> dict:
    best = _latest(_records())
    rows = []
    for (prov, model, bench), r in best.items():
        measured = _pct(r)
        if measured is None:
            continue
        advertised = cfg.advertised(model, bench)
        rows.append({
            "provider": prov, "model": model, "benchmark": bench,
            "measured": measured, "advertised": advertised,
            "delta": round(measured - advertised, 2) if advertised is not None else None,
            "n": r.get("n_items", 0), "engine": r.get("engine", "?"),
        })
    rows.sort(key=lambda x: (x["delta"] is None, x["delta"] if x["delta"] is not None else 0))
    return {"rows": rows}


def providers_view(cfg: Config) -> dict:
    best = _latest(_records())
    provs = sorted({p for (p, _m, _b) in best})
    models = sorted({m for (_p, m, _b) in best})
    benches = sorted({b for (_p, _m, b) in best})
    cells: dict = {}
    for (prov, model, bench), r in best.items():
        cells.setdefault(prov, {}).setdefault(model, {})[bench] = _pct(r)
    return {"providers": provs, "models": models, "benchmarks": benches, "cells": cells}


def run_history(cfg: Config) -> dict:
    records = sorted(_records(), key=lambda r: r.get("timestamp", "") or "", reverse=True)
    out = []
    for r in records[:500]:
        out.append({
            "timestamp": r.get("timestamp", ""),
            "provider": provider_for_base_url(r.get("base_url", "")),
            "model": r.get("model"), "benchmark": r.get("benchmark"),
            "engine": r.get("engine", "?"), "metric": r.get("metric", ""),
            "score": _pct(r), "n": r.get("n_items", 0),
        })
    return {"runs": out}
