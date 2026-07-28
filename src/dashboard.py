"""Data layer for the web dashboard.

Pure functions that read results/ + config/ and return JSON-friendly structures.
Also handles config writes (settings page), report export, and industry
benchmark reference data.
"""
from __future__ import annotations

import csv
import io
import json
import time
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .config import Config, PROVIDERS, RESULTS_DIR, REPORTS_DIR, CONFIG_DIR
from .results import load_all_results

# ---------------------------------------------------------------------------
# Cache (so 6 endpoints share one read per 5s window)
# ---------------------------------------------------------------------------
_RECORDS_CACHE = {"t": 0.0, "data": None}
_RECORDS_TTL = 5.0


def _records() -> list:
    now = time.time()
    if _RECORDS_CACHE["data"] is None or now - _RECORDS_CACHE["t"] > _RECORDS_TTL:
        _RECORDS_CACHE["data"] = load_all_results()
        _RECORDS_CACHE["t"] = now
    return _RECORDS_CACHE["data"]


def invalidate_cache():
    _RECORDS_CACHE["data"] = None


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------
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
    if not rec.get("n_items"):
        return None
    try:
        return round(float(rec.get("score")) * 100.0, 2)
    except (TypeError, ValueError):
        return None


def _latest(records) -> dict:
    best: dict = {}
    for r in records:
        key = (provider_for_base_url(r.get("base_url", "")),
               r.get("model"), r.get("benchmark"))
        prev = best.get(key)
        if prev is None or (r.get("timestamp", "") or "") >= (prev.get("timestamp", "") or ""):
            best[key] = r
    return best


# ---------------------------------------------------------------------------
# Dashboard views
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Settings page — read/write config
# ---------------------------------------------------------------------------
def settings_view(cfg: Config) -> dict:
    """Return the full editable configuration for the settings page."""
    pm = cfg.models.get("provider_models", {})
    providers_info = []
    for name, (api_type, url_var, key_var, default_url) in PROVIDERS.items():
        url, key = "", ""
        try:
            from .config import get_provider_credentials
            url, key = get_provider_credentials(name)
        except Exception:
            pass
        providers_info.append({
            "name": name, "api_type": api_type,
            "url_env": url_var, "key_env": key_var,
            "url": url, "has_key": bool(key),
            "models": pm.get(name, []),
        })
    benchmarks = []
    for bname, bspec in cfg.benchmarks.get("benchmarks", {}).items():
        benchmarks.append({
            "name": bname, "kind": bspec.get("kind", ""),
            "metric": bspec.get("metric", ""), "n_shot": bspec.get("n_shot", 0),
            "enabled": bname not in _disabled_benchmarks(cfg),
        })
    profiles = {}
    for pname, pspec in cfg.models.get("profiles", {}).items():
        profiles[pname] = pspec.get("benchmarks", [])
    return {
        "providers": providers_info,
        "benchmarks": benchmarks,
        "profiles": profiles,
        "default_profile": cfg.models.get("default_profile", "general"),
        "sampling": {"seed": cfg.sampling.seed, "temperature": cfg.sampling.temperature,
                      "timeout": cfg.sampling.timeout},
    }


def _disabled_benchmarks(cfg: Config) -> set:
    """Benchmarks disabled via a 'disabled:' list in benchmarks.yaml."""
    return set(cfg.benchmarks.get("disabled", []))


def save_settings(cfg: Config, body: dict) -> dict:
    """Save settings from the UI. Writes providers.yaml + benchmarks.yaml disabled list."""
    saved = []
    # 1) Save per-provider model lists
    pm = body.get("provider_models", {})
    if pm:
        path = CONFIG_DIR / "providers.yaml"
        existing = {}
        if path.exists():
            existing = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        existing["provider_models"] = pm
        path.write_text(yaml.safe_dump(existing, sort_keys=False, allow_unicode=True, width=10000),
                        encoding="utf-8")
        saved.append("providers.yaml")
    # 2) Save disabled benchmarks
    disabled = body.get("disabled_benchmarks", [])
    if disabled is not None:
        path = CONFIG_DIR / "benchmarks.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data["disabled"] = list(disabled)
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=10000),
                        encoding="utf-8")
        saved.append("benchmarks.yaml (disabled list)")
    # 3) Save sampling defaults
    sampling = body.get("sampling", {})
    if sampling:
        # Write to .env (append/replace)
        env_path = cfg.project_root / ".env"
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        out = []
        seen_seed = seen_temp = seen_timeout = False
        for line in lines:
            if line.startswith("OLLAMA_SEED="):
                out.append(f"OLLAMA_SEED={sampling.get('seed', 1234)}"); seen_seed = True
            elif line.startswith("OLLAMA_TEMPERATURE="):
                out.append(f"OLLAMA_TEMPERATURE={sampling.get('temperature', 0.0)}"); seen_temp = True
            elif line.startswith("OLLAMA_TIMEOUT="):
                out.append(f"OLLAMA_TIMEOUT={sampling.get('timeout', 120)}"); seen_timeout = True
            else:
                out.append(line)
        if not seen_seed: out.append(f"OLLAMA_SEED={sampling.get('seed', 1234)}")
        if not seen_temp: out.append(f"OLLAMA_TEMPERATURE={sampling.get('temperature', 0.0)}")
        if not seen_timeout: out.append(f"OLLAMA_TIMEOUT={sampling.get('timeout', 120)}")
        env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
        saved.append(".env (sampling)")
    invalidate_cache()
    return {"saved": saved}


# ---------------------------------------------------------------------------
# Report export
# ---------------------------------------------------------------------------
def export_csv(cfg: Config) -> str:
    """Export all results as CSV."""
    best = _latest(_records())
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["provider", "model", "benchmark", "metric", "measured_pct",
                "advertised_pct", "delta", "n_items", "engine", "timestamp"])
    for (prov, model, bench), r in sorted(best.items()):
        measured = _pct(r)
        adv = cfg.advertised(model, bench)
        delta = round(measured - adv, 2) if (measured is not None and adv is not None) else ""
        w.writerow([prov, model, bench, r.get("metric", ""), measured or "",
                    adv or "", delta, r.get("n_items", 0), r.get("engine", ""),
                    r.get("timestamp", "")])
    return out.getvalue()


def export_json(cfg: Config) -> str:
    """Export all results as JSON."""
    best = _latest(_records())
    rows = []
    for (prov, model, bench), r in sorted(best.items()):
        measured = _pct(r)
        adv = cfg.advertised(model, bench)
        rows.append({
            "provider": prov, "model": model, "benchmark": bench,
            "metric": r.get("metric", ""), "measured_pct": measured,
            "advertised_pct": adv,
            "delta": round(measured - adv, 2) if (measured is not None and adv is not None) else None,
            "n_items": r.get("n_items", 0), "engine": r.get("engine", ""),
            "timestamp": r.get("timestamp", ""),
        })
    return json.dumps(rows, indent=2, ensure_ascii=False)


def export_markdown(cfg: Config) -> str:
    """Export a full markdown report."""
    from .report import render_markdown
    return render_markdown(cfg)


# ---------------------------------------------------------------------------
# Industry benchmark reference data
# ---------------------------------------------------------------------------
# Curated from official model cards / leaderboards. These are the canonical
# "advertised" scores vendors publish. The deltas tab compares measured vs these.
INDUSTRY_BENCHMARKS = {
    "mmlu": {"name": "MMLU", "kind": "Knowledge", "max_score": 100,
             "description": "57-subject multiple-choice knowledge"},
    "mmlu_pro": {"name": "MMLU-Pro", "kind": "Knowledge", "max_score": 100,
                 "description": "10-option harder knowledge"},
    "gpqa": {"name": "GPQA", "kind": "Reasoning", "max_score": 100,
             "description": "Graduate-level science (gated)"},
    "gsm8k": {"name": "GSM8K", "kind": "Math", "max_score": 100,
              "description": "Grade-school math word problems"},
    "math": {"name": "MATH", "kind": "Math", "max_score": 100,
             "description": "Competition mathematics"},
    "humaneval": {"name": "HumanEval", "kind": "Code", "max_score": 100,
                  "description": "Python function pass@1"},
    "mbpp": {"name": "MBPP", "kind": "Code", "max_score": 100,
             "description": "Basic Python programs pass@1"},
    "arc_challenge": {"name": "ARC-Challenge", "kind": "Reasoning", "max_score": 100,
                      "description": "Grade-school science reasoning"},
    "hellaswag": {"name": "HellaSwag", "kind": "Reasoning", "max_score": 100,
                  "description": "Sentence completion / common sense"},
    "winogrande": {"name": "WinoGrande", "kind": "Reasoning", "max_score": 100,
                   "description": "Coreference resolution"},
    "truthfulqa": {"name": "TruthfulQA", "kind": "Truthfulness", "max_score": 100,
                   "description": "Resistance to common falsehoods (MC1)"},
    "bbh": {"name": "BIG-Bench Hard", "kind": "Reasoning", "max_score": 100,
            "description": "23 challenging reasoning tasks"},
    "math_500": {"name": "MATH-500", "kind": "Math", "max_score": 100,
                 "description": "500-problem MATH subset"},
    "aime_2024": {"name": "AIME 2024", "kind": "Math", "max_score": 100,
                  "description": "American Invitational Math Exam 2024"},
    "aime_2025": {"name": "AIME 2025", "kind": "Math", "max_score": 100,
                  "description": "American Invitational Math Exam 2025"},
    "aime_2026": {"name": "AIME 2026", "kind": "Math", "max_score": 100,
                  "description": "American Invitational Math Exam 2026"},
    "simpleqa": {"name": "SimpleQA", "kind": "Factuality", "max_score": 100,
                 "description": "Short-form factual QA"},
    "hle": {"name": "HLE", "kind": "Expert", "max_score": 100,
            "description": "Humanity's Last Exam"},
    "livecodebench": {"name": "LiveCodeBench", "kind": "Code", "max_score": 100,
                      "description": "Contest code stdin/stdout"},
    "bigcodebench": {"name": "BigCodeBench", "kind": "Code", "max_score": 100,
                     "description": "Heavy Python library tasks"},
    "swebench_lite": {"name": "SWE-bench Lite", "kind": "Agent", "max_score": 100,
                      "description": "GitHub issue fixing (300 instances)"},
    "swebench_verified": {"name": "SWE-bench Verified", "kind": "Agent", "max_score": 100,
                          "description": "Human-validated SWE (500 instances)"},
    "bfcl": {"name": "BFCL", "kind": "Function-calling", "max_score": 100,
             "description": "Berkeley Function Calling Leaderboard"},
    "gaia": {"name": "GAIA", "kind": "Agent", "max_score": 100,
             "description": "General assistant benchmark"},
    "mixeval": {"name": "MixEval", "kind": "Multi-domain", "max_score": 100,
                "description": "Dynamic real-world evaluation"},
    "gpqa_diamond": {"name": "GPQA Diamond", "kind": "Reasoning", "max_score": 100,
                     "description": "Gold-standard GPQA subset"},
    "ifeval": {"name": "IFEval", "kind": "Instruction-following", "max_score": 100,
               "description": "Instruction Following Evaluation"},
    "musr": {"name": "MuSR", "kind": "Reasoning", "max_score": 100,
             "description": "Multistep Soft Reasoning"},
}


def industry_reference(cfg: Config) -> dict:
    """Return industry benchmark reference data + published scores."""
    published = cfg.published_scores
    models_block = published.get("models", {})
    extended_block = published.get("extended", {})
    # Merge into one flat {model: {benchmark: score}}
    all_refs: dict = {}
    for model_id, entry in models_block.items():
        adv = entry.get("advertised", {})
        all_refs[model_id] = {k: v for k, v in adv.items()}
    for model_id, scores in extended_block.items():
        if model_id not in all_refs:
            all_refs[model_id] = {}
        all_refs[model_id].update(scores)
    return {
        "benchmarks": INDUSTRY_BENCHMARKS,
        "published_scores": all_refs,
        "defaults": published.get("defaults", {}),
    }


def model_comparison(cfg: Config, model_a: str, model_b: str) -> dict:
    """Compare two models side-by-side across all benchmarks they share."""
    best = _latest(_records())
    a_data = {b: _pct(r) for (p, m, b), r in best.items() if m == model_a}
    b_data = {b: _pct(r) for (p, m, b), r in best.items() if m == model_b}
    a_adv = {b: cfg.advertised(model_a, b) for b in a_data}
    b_adv = {b: cfg.advertised(model_b, b) for b in b_data}
    shared = sorted(set(a_data) | set(b_data))
    rows = []
    for b in shared:
        rows.append({
            "benchmark": b,
            "a_measured": a_data.get(b), "b_measured": b_data.get(b),
            "a_advertised": a_adv.get(b), "b_advertised": b_adv.get(b),
        })
    return {"model_a": model_a, "model_b": model_b, "rows": rows}