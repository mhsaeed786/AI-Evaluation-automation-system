"""Top-level runner / CLI.

Examples
--------
    # Discover live models, run a fast end-to-end check:
    python -m src.runner --models auto --benchmarks mmlu,gsm8k,humaneval --quick

    # Full run of every configured benchmark on every live model:
    python -m src.runner --models auto --benchmarks all

    # One specific model, the coding profile:
    python -m src.runner --models qwen3-coder --benchmarks coding

    # Drive benchmarks through the lm-eval harness instead of the builtin engine:
    python -m src.runner --models deepseek-v3 --benchmarks mmlu,gpqa --engine lm_eval

Multiple providers run IN PARALLEL by default (one thread each), so an OpenAI,
an Anthropic and a Gemini key are exercised at the same time. Use --jobs 1 for
strictly sequential runs (cleaner logs). Providers without a key in .env are
skipped. Each provider speaks its own API dialect (openai / anthropic / gemini)
via src/provider_clients.make_client.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table

from .config import load_config, get_provider_credentials, PROVIDERS
from .provider_clients import make_client
from .results import save_result, ResultRecord
from .engines import run_builtin

console = Console()
log = logging.getLogger("ollama_eval.runner")


# ----------------------------------------------------------------------
# Plan resolution
# ----------------------------------------------------------------------
def _profile_benchmarks(cfg, profile_names: list[str]) -> list[str]:
    profiles = cfg.models.get("profiles", {})
    out, seen = [], set()
    for p in profile_names:
        for b in profiles.get(p, {}).get("benchmarks", []):
            if b not in seen:
                seen.add(b)
                out.append(b)
    return out


def _curated_entry(cfg, model_id: str) -> dict | None:
    for m in cfg.models.get("models", []):
        if m["id"] == model_id:
            return m
    return None


_NON_TEXT = ("whisper", "-tts", "tts-", "speech", "orpheus", "audio",
             "stable-diffusion", "sora", "dall-e", "embedding", "-embed",
             "guard", "classify", "moderation", "rerank", "-image", "i2v",
             "t2v", "r2v", "video", "-wan", "happyhorse", "flux", "diffus",
             "sdxl", "-vl", "-vision", "guardrail", "-gguf", "transcribe")


def _is_text_model(model_id: str) -> bool:
    m = (model_id or "").lower()
    return not any(b in m for b in _NON_TEXT)


def resolve_models(cfg, client, models_arg: str, provider_name: str = "ollama") -> list[str]:
    """Resolve the model list for a provider, honouring the curated per-provider
    lists in config/providers.yaml and the free/paid + text-only filters."""
    prov = provider_name.lower()
    if models_arg in ("auto", "all"):
        try:
            live = client.list_models()
        except Exception as e:  # noqa: BLE001
            log.warning("model discovery failed for %s: %s", prov, e)
            live = []
        pm = cfg.models.get("provider_models", {})
        if prov in pm:
            entry = pm[prov]
            if entry == "auto":                 # paid: all live models
                cand = live
            else:                               # free: curated list (intersect live)
                cand = [m for m in entry if (not live or m in live)] or list(entry)
        else:
            cand = live
        if prov == "openrouter":                # free tier: :free models only
            cand = [m for m in cand if m.endswith(":free")]
        cand = [m for m in cand if _is_text_model(m)]
        if not cand:
            console.print(f"[yellow][{provider_name}] No usable models after tier/text filters.[/yellow]")
            return []
        console.print(f"[green][{provider_name}] Using {len(cand)} model(s):[/green] {', '.join(cand[:8])}{' ...' if len(cand)>8 else ''}")
        return sorted(set(cand))

    wanted = [m.strip() for m in models_arg.split(",") if m.strip()]
    return wanted


def resolve_benchmarks(cfg, models, benchmarks_arg: str) -> dict[str, list[str]]:
    """Return {model_id: [benchmark names]}."""
    all_bench = list(cfg.benchmarks.get("benchmarks", {}).keys())
    profiles = cfg.models.get("profiles", {})

    if benchmarks_arg == "all":
        return {m: list(all_bench) for m in models}
    if benchmarks_arg in profiles:  # a profile name
        bs = _profile_benchmarks(cfg, [benchmarks_arg])
        return {m: bs for m in models}

    # Explicit comma list -> same set for every model.
    explicit = [b.strip() for b in benchmarks_arg.split(",") if b.strip()]
    unknown = [b for b in explicit if b not in all_bench]
    if unknown:
        console.print(f"[yellow]Unknown benchmark(s) (skipping):[/yellow] {', '.join(unknown)}")
    explicit = [b for b in explicit if b in all_bench]
    return {m: list(explicit) for m in models}


def benchmark_set_per_model(cfg, models, benchmarks_arg: str) -> dict[str, list[str]]:
    """If benchmarks_arg == 'per_profile', use each model's own profiles."""
    if benchmarks_arg == "per_profile":
        out = {}
        for m in models:
            entry = _curated_entry(cfg, m)
            profs = entry["profiles"] if entry and entry.get("profiles") else \
                [cfg.models.get("default_profile", "general")]
            out[m] = _profile_benchmarks(cfg, profs)
        return out
    return resolve_benchmarks(cfg, models, benchmarks_arg)


# ----------------------------------------------------------------------
# Engine dispatch
# ----------------------------------------------------------------------
def run_one(cfg, client, model, benchmark, *, quick, engine):
    spec = cfg.benchmark(benchmark)
    if engine == "builtin":
        rec = run_builtin(client, model, benchmark, spec, quick=quick,
                          quick_table=cfg.benchmarks.get("quick_limits", {}),
                          seed=cfg.sampling.seed, temperature=cfg.sampling.temperature)
    elif engine == "lm_eval":
        from harnesses.lm_eval_runner import run_lm_eval  # lazy import
        rec = run_lm_eval(cfg, client, model, benchmark, spec, quick=quick)
    elif engine == "evalplus":
        from harnesses.evalplus_runner import run_evalplus  # lazy import
        rec = run_evalplus(cfg, client, model, benchmark, spec, quick=quick)
    else:
        raise SystemExit(f"Unknown engine '{engine}'")
    return rec


# ----------------------------------------------------------------------
# Per-provider worker (runs in its own thread when parallel)
# ----------------------------------------------------------------------
def run_provider(cfg, prov, args) -> list[ResultRecord]:
    """Run the full model x benchmark plan for ONE provider. Thread-safe:
    each provider gets its own client and writes its own result files."""
    from .config import provider_api_type

    finished: list[ResultRecord] = []
    if not get_provider_credentials(prov)[1]:
        console.print(f"[yellow]Skipping provider '{prov}': API key not set in .env[/yellow]")
        return finished

    api_type = provider_api_type(prov)
    console.rule(f"[bold magenta]Provider: {prov.upper()} [{api_type}][/bold magenta]")
    try:
        client = make_client(prov, cfg)
    except Exception as e:  # noqa: BLE001 -- keep other providers running
        console.print(f"[red]Could not build client for '{prov}' ({api_type}): {e}[/red]")
        log.exception("client build failed for %s", prov)
        return finished

    try:
        models = resolve_models(cfg, client, args.models, provider_name=prov)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Failed to resolve models for provider '{prov}': {e}[/red]")
        log.exception("model discovery failed for %s", prov)
        return finished
    if not models:
        return finished

    plan = benchmark_set_per_model(cfg, models, args.benchmarks)
    for model in models:
        for benchmark in plan.get(model, []):
            try:
                rec = run_one(cfg, client, model, benchmark,
                              quick=args.quick, engine=args.engine)
                save_result(rec)
                finished.append(rec)
                tag = f"{rec.metric}={rec.percent}%" if rec.n_items else "no items"
                console.print(f"  [{prov}] {model} / {benchmark} -> {tag}")
            except KeyboardInterrupt:
                raise
            except Exception as e:  # noqa: BLE001
                log.exception("%s/%s/%s failed", prov, model, benchmark)
                console.print(f"  [red][{prov}] {model}/{benchmark} FAILED[/red] "
                              f"{type(e).__name__}: {e}")
    return finished


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ollama-eval", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", default="ollama",
                    help="provider name (openai, anthropic, gemini, ollama, qwen, groq, "
                         "openrouter, cerebras, hf, together, ... or 'all')")
    ap.add_argument("--models", default="auto",
                    help="comma list, 'auto' (live model list), or 'all'")
    ap.add_argument("--benchmarks", default="mmlu,gsm8k",
                    help="comma list, 'all', a profile name (general/coding/reasoning), "
                         "or 'per_profile'")
    ap.add_argument("--engine", default="builtin", choices=["builtin", "lm_eval", "evalplus"])
    ap.add_argument("--quick", action="store_true",
                    help="use small per-benchmark limits for a fast end-to-end check")
    ap.add_argument("--jobs", type=int, default=0,
                    help="max providers to run in parallel (0 = all capped at 8; 1 = sequential)")
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cfg = load_config()

    pm = cfg.models.get("provider_models", {})
    if args.provider.lower() == "all":
        target_providers = [p for p in PROVIDERS if p in pm]
    else:
        target_providers = [p.strip() for p in args.provider.split(",") if p.strip()]

    runnable = [p for p in target_providers if get_provider_credentials(p)[1]]
    for p in target_providers:
        if p not in runnable:
            console.print(f"[yellow]Skipping provider '{p}': API key not set in .env[/yellow]")
    if args.provider.lower() == "all":
        console.print(f"[green]Curated providers ({len(runnable)}):[/green] {', '.join(runnable)}")

    if not runnable:
        console.print("[red]No providers with an API key configured. Edit .env and retry.[/red]")
        return 1

    finished: list[ResultRecord] = []
    sequential = (args.jobs == 1) or len(runnable) <= 1
    if sequential:
        if len(runnable) > 1:
            console.print("[dim]Running providers sequentially (--jobs 1).[/dim]")
        for prov in runnable:
            finished.extend(run_provider(cfg, prov, args))
    else:
        jobs = max(1, (args.jobs if args.jobs > 0 else min(len(runnable), 8)))
        os.environ["OLLAMA_EVAL_QUIET"] = "1"  # tame interleaving tqdm bars across threads
        console.print(f"[green]Running {len(runnable)} provider(s) in parallel "
                      f"(jobs={jobs})[/green]")
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            futs = {ex.submit(run_provider, cfg, prov, args): prov for prov in runnable}
            for fut in as_completed(futs):
                prov = futs[fut]
                try:
                    finished.extend(fut.result())
                except Exception as e:  # noqa: BLE001 -- one provider must not kill the rest
                    log.exception("provider %s crashed", prov)
                    console.print(f"[red]Provider {prov} crashed: {e}[/red]")

    _print_summary(finished)
    return 0


def _print_summary(records: list[ResultRecord]) -> None:
    if not records:
        console.print("\n[dim]No completed records.[/dim]")
        return
    t = Table(title="Summary", show_lines=True)
    t.add_column("Model", style="cyan")
    t.add_column("Benchmark")
    t.add_column("Metric")
    t.add_column("Score", justify="right", style="green")
    t.add_column("n", justify="right")
    for r in records:
        if r.n_items:
            t.add_row(r.model, r.benchmark, r.metric, f"{r.percent}%", str(r.n_items))
        else:
            t.add_row(r.model, r.benchmark, r.metric, "—", "0")
    console.print(t)


if __name__ == "__main__":
    sys.exit(main())
