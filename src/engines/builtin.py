"""Builtin evaluation engine.

Runs one benchmark for one model directly against Ollama Cloud, scoring every
item and returning a :class:`~src.results.ResultRecord`. Per-item failures are
counted and logged but never abort the run.
"""
from __future__ import annotations

import logging

from tqdm import tqdm

from ..loaders import load_benchmark, DatasetUnavailable
from ..ollama_client import OllamaCloudClient
from ..results import ResultRecord
from .. import scorers

log = logging.getLogger("ollama_eval.engine")

# Per-kind generation budget. The extended (agent_*/code_io) kinds need real
# room — a default of 16 would silently truncate SWE diffs and ARC grids and
# make those benchmarks report garbage. Every kind the engine can dispatch to
# has an explicit entry; the lookup default (1024) only applies to unknown
# kinds, which are skipped before generation anyway.
MAX_TOKENS = {
    "mcq": 8,
    "math": 1024,
    "code": 1024,
    "code_io": 2048,
    "agent_swe": 4096,    # unified diffs can be long
    "agent_arc": 2048,    # output-grid JSON
    "agent_bfcl": 512,    # one function-call JSON object
    "agent_terminal": 1024,
    "agent_gaia": 1024,
}

# Explicit kind -> builtin-scorer map. NOT a getattr-by-name lookup: several
# kinds (agent_swe, agent_arc, agent_bfcl, agent_gaia) map to scorers whose
# names follow the benchmark, not the kind key, and a by-name miss must never
# fall through to score_code (which would execute the item prompt as Python).
# A kind absent from this map is recorded as an error and skipped.
EXTENDED_SCORERS = {
    "code": scorers.score_code,
    "code_io": scorers.score_code_io,
    "agent_swe": scorers.score_swe,
    "agent_arc": scorers.score_arc_agi,
    "agent_bfcl": scorers.score_function_call,
    "agent_terminal": scorers.score_agent_terminal,
    "agent_gaia": scorers.score_gaia,
}


def _resolve_limit(spec: dict, quick: bool, quick_table: dict, name: str) -> int | None:
    if quick:
        return quick_table.get(name)
    return spec.get("limit")


def _shots_for(items: list[dict], n_shot: int, idx: int) -> list[dict]:
    if n_shot <= 0:
        return []
    # Deterministic few-shot: take the first usable items, skipping the current.
    shots = []
    for j, it in enumerate(items):
        if len(shots) >= n_shot:
            break
        if j == idx:
            continue
        # Only reuse items that have a usable gold.
        if it.get("gold") is not None or it.get("gold_text"):
            shots.append(it)
    return shots


def run_builtin(client: OllamaCloudClient, model: str, name: str, spec: dict, *,
                quick: bool = False, quick_table: dict | None = None,
                seed: int = 1234, temperature: float = 0.0) -> ResultRecord:
    quick_table = quick_table or {}
    limit = _resolve_limit(spec, quick, quick_table, name)

    try:
        items = load_benchmark(name, spec, limit=limit)
    except DatasetUnavailable as e:
        log.warning("Skipping %s/%s: %s", model, name, e)
        rec = ResultRecord(model=model, benchmark=name, metric=spec.get("metric", "acc"),
                           score=float("nan"), n_items=0, engine="builtin",
                           base_url=client.base_url, seed=seed, temperature=temperature,
                           n_shot=spec.get("n_shot", 0), limit=limit,
                           cot=bool(spec.get("cot")))
        rec.errors.append(f"dataset_unavailable: {e}")
        return rec

    kind = spec.get("kind", "mcq")
    n_shot = int(spec.get("n_shot", 0))
    cot = bool(spec.get("cot"))
    max_tokens = MAX_TOKENS.get(kind, 1024) if not cot else 2048

    correct = 0
    evaluated = 0
    errors: list[str] = []
    samples: list[dict] = []

    for idx, item in enumerate(tqdm(items, desc=f"{model}/{name}", unit="q")):
        try:
            if kind == "mcq":
                if item.get("choices"):
                    shots = _shots_for(items, n_shot, idx)
                    res = scorers.score_mcq(client, model, item, shots=shots, cot=cot,
                                            temperature=temperature, max_tokens=max_tokens)
                else:
                    # Free-text MCQ (e.g. BBH): generate + match gold_text.
                    res = _score_text_match(client, model, item, temperature, max_tokens)
                ok = bool(res.get("correct"))
            elif kind == "math":
                shots = _shots_for(items, n_shot, idx)
                res = scorers.score_math(client, model, item, shots=shots,
                                         temperature=temperature, max_tokens=max_tokens)
                ok = bool(res.get("correct"))
            elif kind in EXTENDED_SCORERS:
                # Extended kinds route through their own scorer. A kind without
                # a real scorer (e.g. agent_tau/tau_bench) is deliberately NOT
                # in this map and falls through to the else branch, where it is
                # recorded and skipped — never executed as Python.
                res = EXTENDED_SCORERS[kind](client, model, item,
                                             temperature=temperature, max_tokens=max_tokens)
                ok = bool(res.get("passed"))
            else:
                errors.append(f"unknown_kind:{kind}")
                continue

            evaluated += 1
            if ok:
                correct += 1
            if len(samples) < 12:
                samples.append({"id": item.get("id"), **{k: v for k, v in res.items()
                                if k != "raw"}})
        except Exception as e:  # noqa: BLE001 -- keep the run alive
            errors.append(f"item {item.get('id')}: {type(e).__name__}: {e}")
            log.debug("item error %s: %s", item.get("id"), e)

    score = (correct / evaluated) if evaluated else float("nan")
    metric = spec.get("metric", "acc")
    rec = ResultRecord(
        model=model, benchmark=name, metric=metric, score=score, n_items=evaluated,
        engine="builtin", base_url=client.base_url, seed=seed, temperature=temperature,
        n_shot=n_shot, limit=limit, cot=cot, errors=errors, sample_predictions=samples,
    )
    log.info("%s/%s: %s=%.4f over %d items (%d errors)",
             model, name, metric, score, evaluated, len(errors))
    return rec


def _score_text_match(client: OllamaCloudClient, model: str, item: dict,
                      temperature: float, max_tokens: int) -> dict:
    text = client.chat_text(
        model=model,
        messages=[
            {"role": "system", "content": "Answer the question. End with 'Answer: <answer>'."},
            {"role": "user", "content": item["question"]},
        ],
        temperature=temperature, max_tokens=max_tokens if max_tokens > 32 else 256,
    )
    m = None
    import re
    mm = re.search(r"answer[:\s]*(.+?)(?:\.|$)", text, re.IGNORECASE)
    if mm:
        m = mm.group(1).strip()
    gold = item.get("gold_text", "")
    return {"correct": m is not None and m.lower() == gold.lower(),
            "predicted": m, "gold": gold, "method": "text_match"}

