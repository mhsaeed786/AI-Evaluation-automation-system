"""Wrapper around the EvalPlus harness (HumanEval+ / MBPP+).

EvalPlus augments the original HumanEval/MBPP test suites with many more
hand-written tests, giving a stricter pass\\@1 than vanilla execution. It
supports any OpenAI-compatible endpoint via ``--base-url`` / ``--api-key``.

Invoked as a subprocess; the resulting ``eval_results.json`` is parsed into a
:class:`ResultRecord`.

Requirements (Tier 2): ``pip install -r requirements-harness.txt`` on
Python 3.11 or 3.12. EvalPlus is *not* torch-light for evaluation (it shells
out to execute samples), but its deps lag on 3.14.

Reference
---------
- https://github.com/evalplus/evalplus — ``python -m evalplus.evaluate --help``
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from src.config import Config
from src.ollama_client import OllamaCloudClient
from src.results import ResultRecord

# Map our benchmark names -> EvalPlus dataset flags.
DATASET_MAP = {
    "humaneval_plus": "humaneval",
    "mbpp_plus": "mbpp",
    "humaneval": "humaneval",   # if someone explicitly routes vanilla HE here
    "mbpp": "mbpp",
}


def run_evalplus(cfg: Config, client: OllamaCloudClient, model: str, benchmark: str,
                 spec: dict, *, quick: bool = False) -> ResultRecord:
    dataset = DATASET_MAP.get(benchmark)
    if dataset is None:
        rec = _empty(cfg, model, benchmark, spec)
        rec.errors.append(f"no evalplus dataset for '{benchmark}' (use humaneval_plus/mbpp_plus)")
        return rec

    out_dir = Path("results") / "evalplus"
    out_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.setdefault("OPENAI_API_KEY", cfg.api_key)

    # No --backend flag: EvalPlus defaults to its augmented (Plus) test suite,
    # which is exactly what we want for humaneval_plus/mbpp_plus. pass@1 needs
    # exactly one sample per problem. --i-just-wanna-run runs generate+evaluate
    # end-to-end in one shot.
    cmd = [
        sys.executable, "-m", "evalplus.evaluate",
        "--dataset", dataset,
        "--model", model,
        "--base-url", cfg.base_url,
        "--api-key", cfg.api_key,
        "--n-samples", "1",
        "--temperature", str(cfg.sampling.temperature),
        "--i-just-wanna-run",
    ]
    if quick:
        # Subsample the dataset for a fast end-to-end check. If the installed
        # EvalPlus does not recognise this flag the subprocess will error and we
        # surface that gracefully (see below) rather than crashing our process.
        cmd += ["--subsample-size", "20"]

    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                              cwd=str(out_dir), timeout=3600)
    except FileNotFoundError:
        rec = _empty(cfg, model, benchmark, spec)
        rec.errors.append("evalplus not installed (pip install -r requirements-harness.txt)")
        return rec
    if proc.returncode != 0:
        rec = _empty(cfg, model, benchmark, spec)
        rec.errors.append(
            f"evalplus exit {proc.returncode}: "
            f"{proc.stderr.strip()[-600:] or proc.stdout.strip()[-600:]}"
        )
        return rec

    return _parse_evalplus_output(out_dir, cfg, model, benchmark, spec, proc.stdout)


def _parse_evalplus_output(out_dir: Path, cfg, model, benchmark, spec, stdout: str) -> ResultRecord:
    # EvalPlus writes eval_results.json under out_dir/dataset/model/.
    jsons = list(out_dir.rglob("eval_results.json"))
    score = None
    if jsons:
        try:
            data = json.loads(jsons[0].read_text(encoding="utf-8"))
            score = _find_passk(data, "pass@1")
        except (json.JSONDecodeError, OSError):
            score = None

    # Fallback: EvalPlus prints "pass@1 = 0.75" to stdout.
    if score is None:
        m = re.search(r"pass@1[:\s=]+([0-9]*\.?[0-9]+)", stdout)
        if m:
            score = float(m.group(1)) / (100.0 if float(m.group(1)) > 1.5 else 1.0)

    if score is None:
        rec = _empty(cfg, model, benchmark, spec)
        rec.errors.append("evalplus produced no pass@1 score")
        return rec

    n = spec.get("limit") or (164 if benchmark.startswith("humaneval") else 378)
    return ResultRecord(
        model=model, benchmark=benchmark, metric="pass@1",
        score=float(score), n_items=int(n), engine="evalplus", base_url=cfg.base_url,
        seed=cfg.sampling.seed, temperature=cfg.sampling.temperature,
        n_shot=int(spec.get("n_shot", 0)), limit=spec.get("limit"),
    )


def _find_passk(obj, key: str):
    """Recursively look for a 'pass@1' float at any nesting depth."""
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], (int, float)):
            return obj[key]
        for v in obj.values():
            found = _find_passk(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_passk(v, key)
            if found is not None:
                return found
    return None


def _empty(cfg, model, benchmark, spec) -> ResultRecord:
    return ResultRecord(model=model, benchmark=benchmark, metric="pass@1",
                        score=float("nan"), n_items=0, engine="evalplus",
                        base_url=cfg.base_url, seed=cfg.sampling.seed,
                        temperature=cfg.sampling.temperature, n_shot=int(spec.get("n_shot", 0)),
                        limit=spec.get("limit"))
