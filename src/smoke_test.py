"""Connectivity smoke test.

Run after pasting your key into .env:

    python -m src.smoke_test

This is the RUNTIME step that pins whether OLLAMA_BASE_URL is correct. It:

  1. Lists the models your key can actually reach (GET /v1/models).
  2. Reconciles them against config/models.yaml (curated reference).
  3. Sends one tiny chat request + one logprobs request to confirm the
     endpoint answers normally AND returns top_logprobs (which MCQ scoring
     depends on).
  4. Prints a clear PASS/FAIL summary.

Exit code 0 = ready to benchmark. Non-zero = endpoint/key problem to fix.
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from .config import load_config
from .ollama_client import OllamaCloudClient, LetterScores

console = Console()


def curated_models(cfg) -> set[str]:
    return {m["id"] for m in cfg.models.get("models", [])}


def main() -> int:
    console.rule("[bold cyan]Ollama Cloud — smoke test[/bold cyan]")
    try:
        cfg = load_config()
    except SystemExit as e:
        console.print(f"[red]CONFIG ERROR:[/red] {e}")
        return 2

    console.print(f"base_url : [cyan]{cfg.base_url}[/cyan]")
    console.print(f"key      : [dim]{cfg.api_key[:6]}…{cfg.api_key[-4:]}[/dim]")
    console.print(f"seed/temp: {cfg.sampling.seed} / {cfg.sampling.temperature}\n")

    client = OllamaCloudClient(
        cfg.base_url, cfg.api_key, timeout=cfg.sampling.timeout,
        seed=cfg.sampling.seed, temperature=cfg.sampling.temperature, org_id=cfg.org_id,
    )

    # --- 1. list models ---------------------------------------------------
    console.print("[1/3] Listing models via GET /v1/models …")
    try:
        live = sorted(client.list_models())
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]FAILED to reach {cfg.base_url}[/red]")
        console.print(f"      {type(e).__name__}: {e}")
        console.print(
            "\n[yellow]Likely causes:[/yellow]\n"
            "  • Wrong base URL — edit OLLAMA_BASE_URL in .env and retry\n"
            "    (see README 'Pinning the endpoint' for candidate URLs)\n"
            "  • Invalid/expired key — regenerate at https://ollama.com/cloud\n"
            "  • Proxy / network blocking the request\n"
        )
        return 1

    if not live:
        console.print("[yellow]Endpoint reachable but returned no models.[/yellow]")
        console.print("      Your Pro plan may have no models enabled — check the dashboard.")
        return 1

    curated = curated_models(cfg)
    t = Table(title=f"Live models ({len(live)})", show_lines=False)
    t.add_column("Model id", style="cyan")
    t.add_column("In config?", justify="center")
    for m in live:
        in_cfg = "[green]yes[/green]" if m in curated else "[dim]no (auto)[/dim]"
        t.add_row(m, in_cfg)
    console.print(t)
    console.print(
        f"[dim]{len(live)} live, {len(curated)} curated, "
        f"{len(curated & set(live))} overlap.[/dim]\n"
    )

    # --- 2. sanity chat request ------------------------------------------
    probe = live[0]
    console.print(f"[2/3] Chat probe on [cyan]{probe}[/cyan] …")
    try:
        text = client.chat_text(
            model=probe,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=8, temperature=0.0,
        )
        console.print(f"      reply: [green]{text!r}[/green]\n")
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Chat request failed: {type(e).__name__}: {e}[/red]\n")
        return 1

    # --- 3. logprobs capability ------------------------------------------
    console.print(f"[3/3] logprobs probe on [cyan]{probe}[/cyan] …")
    mcq = [
        {"role": "user", "content": "What is 2+2? A) 3  B) 4  C) 5  D) 6\nAnswer:"},
    ]
    try:
        ls: LetterScores = client.answer_letter_logprob(model=probe, prompt_messages=mcq)
        if ls.present:
            probs = ls.softmax_probs()
            console.print("      [green]top_logprobs supported[/green] — MCQ scoring via logprobs.")
            for letter, p in sorted(probs.items(), key=lambda kv: -kv[1]):
                console.print(f"        {letter}: {p*100:5.1f}%")
        else:
            console.print(
                "      [yellow]top_logprobs NOT returned by endpoint.[/yellow]\n"
                "      MCQ benchmarks will fall back to generate-and-parse\n"
                "      (slightly noisier but still valid)."
            )
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]logprobs probe errored: {type(e).__name__}: {e}[/yellow]")
        console.print("      MCQ scoring will use the generate-and-parse fallback.")

    console.print("\n[bold green]READY.[/bold green] Add benchmark names to the runner, e.g.")
    console.print("    python -m src.runner --models all --benchmarks mmlu,gsm8k,humaneval --quick")
    return 0


if __name__ == "__main__":
    sys.exit(main())
