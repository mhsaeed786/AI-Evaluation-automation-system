"""Wrapper around EleutherAI's lm-evaluation-harness.

Runs a benchmark through lm-eval pointed at Ollama Cloud's OpenAI-compatible
endpoint, then folds the result into a :class:`ResultRecord`.

We invoke lm-eval as a *subprocess* (rather than importing its Python API)
because (a) its internal API shifts between releases, (b) it imports torch and
other heavy wheels that may be absent on Python 3.14, and (c) subprocess
isolation lets us set OPENAI_API_KEY / OPENAI_BASE_URL cleanly per run.

Requirements (Tier 2): ``pip install -r requirements-harness.txt`` on
Python 3.11 or 3.12.

References
----------
- local-completions / local-chat-completions model types:
  https://github.com/EleutherAI/lm-evaluation-harness/blob/main/lm_eval/models/openai_completions.py
- Driving an OpenAI-compatible server:
  https://github.com/EleutherAI/lm-evaluation-harness/blob/main/lm_eval/models/local-completions.yaml
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from src.config import Config
from src.ollama_client import OllamaCloudClient
from src.results import ResultRecord

# Map our benchmark names -> lm-eval task names (or task groups).
TASK_MAP = {
    "mmlu": "mmlu",
    "mmlu_pro": "mmlu_pro",
    "arc_challenge": "arc_challenge",
    "hellaswag": "hellaswag",
    "winogrande": "winogrande",
    "truthfulqa": "truthfulqa_mc1",
    "gpqa": "gpqa",
    "gsm8k": "gsm8k",
    "math": "minerva_math",
    "bbh": "bbh",
    "agieval": "agieval",
}

# Preferred metric per task (lm-eval reports several; pick the headline one).
METRIC_MAP = {
    "mmlu": "acc,none",
    "mmlu_pro": "acc,none",
    "arc_challenge": "acc_norm,none",
    "hellaswag": "acc_norm,none",
    "winogrande": "acc,none",
    "truthfulqa_mc1": "acc,none",
    "gpqa": "acc_norm,none",
    "gsm8k": "exact_match,strict-match",
    "minerva_math": "exact_match,none",
    "bbh": "acc,none",
    "agieval": "acc,none",
}


def run_lm_eval(cfg: Config, client: OllamaCloudClient, model: str, benchmark: str,
                spec: dict, *, quick: bool = False) -> ResultRecord:
    task = TASK_MAP.get(benchmark)
    if task is None:
        rec = _empty(cfg, client, model, benchmark, spec)
        rec.errors.append(f"no lm-eval task mapping for '{benchmark}'")
        return rec

    limit = 50 if quick else None
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        env = dict(os.environ)
        # lm-eval's local-completions reads the standard OpenAI env vars for auth/base.
        env["OPENAI_API_KEY"] = cfg.api_key
        env["OPENAI_BASE_URL"] = cfg.base_url

        model_args = (
            f"model={model},"
            f"base_url={cfg.base_url}/chat/completions,"
            f"num_concurrent=8,"
            f"max_retries=5,"
            f"tokenized_requests=False,"
            f"timeout={int(cfg.sampling.timeout)}"
        )
        cmd = [
            sys.executable, "-m", "lm_eval",
            "--model", "local-chat-completions",
            "--model_args", model_args,
            "--tasks", task,
            "--output_path", str(out_dir),
            "--batch_size", "8",
        ]
        if limit:
            cmd += ["--limit", str(limit)]
        if int(spec.get("n_shot", 0)) == 0 and task in {"mmlu", "mmlu_pro", "arc_challenge"}:
            cmd += ["--num_fewshot", str(spec.get("n_shot", 0))]

        try:
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                                  timeout=3600)
        except FileNotFoundError:
            rec = _empty(cfg, client, model, benchmark, spec)
            rec.errors.append("lm_eval not installed (pip install -r requirements-harness.txt)")
            return rec
        if proc.returncode != 0:
            rec = _empty(cfg, client, model, benchmark, spec)
            rec.errors.append(
                f"lm_eval exit {proc.returncode}: "
                f"{proc.stderr.strip()[-600:] or proc.stdout.strip()[-600:]}"
            )
            return rec

        return _parse_lm_eval_output(out_dir, cfg, client, model, benchmark, spec, task)


def _parse_lm_eval_output(out_dir: Path, cfg, client, model, benchmark, spec, task) -> ResultRecord:
    # lm-eval writes <out_dir>/eval_results.json (or a results folder). Find it.
    jsons = list(out_dir.rglob("*.json"))
    if not jsons:
        rec = _empty(cfg, client, model, benchmark, spec)
        rec.errors.append("lm_eval produced no output json")
        return rec
    try:
        data = json.loads(jsons[0].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        rec = _empty(cfg, client, model, benchmark, spec)
        rec.errors.append(f"could not parse lm_eval output: {e}")
        return rec

    results = data.get("results", {})
    task_results = results.get(task) or next(iter(results.values()), {}) if results else {}
    metric_key = METRIC_MAP.get(task, "acc,none")
    value = task_results.get(metric_key)
    if value is None and task_results:
        # fall back to the first *_acc / *_norm-ish value
        for k, v in task_results.items():
            if isinstance(v, (int, float)):
                value, metric_key = v, k
                break

    n = task_results.get("n", 0) or spec.get("limit") or 0
    score = float(value) if isinstance(value, (int, float)) else float("nan")
    return ResultRecord(
        model=model, benchmark=benchmark, metric=metric_key.split(",")[0],
        score=score, n_items=int(n), engine="lm_eval", base_url=cfg.base_url,
        seed=cfg.sampling.seed, temperature=cfg.sampling.temperature,
        n_shot=int(spec.get("n_shot", 0)), limit=spec.get("limit"),
        cot=bool(spec.get("cot")),
    )


def _empty(cfg, client, model, benchmark, spec) -> ResultRecord:
    return ResultRecord(model=model, benchmark=benchmark, metric=spec.get("metric", "acc"),
                        score=float("nan"), n_items=0, engine="lm_eval",
                        base_url=cfg.base_url, seed=cfg.sampling.seed,
                        temperature=cfg.sampling.temperature, n_shot=int(spec.get("n_shot", 0)),
                        limit=spec.get("limit"))
