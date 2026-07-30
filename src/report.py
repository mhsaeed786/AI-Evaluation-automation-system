from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from .config import Config, REPORTS_DIR, load_config
from .compare import build_comparison, measured_matrix

console = Console()


def render_html_dashboard(cfg: Config, rows, models: list[str], benches: list[str], grid: dict) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    # Calculate stats
    evaluated_scores = [grid[(m, b)] for m in models for b in benches if grid[(m, b)] is not None]
    avg_score = (sum(evaluated_scores) / len(evaluated_scores)) if evaluated_scores else 0.0
    
    # Model max scores
    model_bests = {}
    for m in models:
        m_scores = [grid[(m, b)] for b in benches if grid[(m, b)] is not None]
        if m_scores:
            model_bests[m] = max(m_scores)
    top_model = max(model_bests, key=model_bests.get) if model_bests else "N/A"
    top_score = model_bests.get(top_model, 0.0) if model_bests else 0.0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Cloud Frontier AI & AGI Evaluation Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0d1117;
            --card-bg: rgba(22, 27, 34, 0.8);
            --border-color: #30363d;
            --text-main: #c9d1d9;
            --text-muted: #8b949e;
            --accent-cyan: #58a6ff;
            --accent-green: #3fb950;
            --accent-yellow: #d29922;
            --accent-red: #f85149;
            --accent-purple: #bc8cff;
        }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
            line-height: 1.5;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 1.8rem;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header .meta {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            backdrop-filter: blur(10px);
        }}
        .stat-card .label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
        .stat-card .value {{
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--accent-cyan);
        }}
        .controls {{
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .controls input, .controls select {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9rem;
            outline: none;
        }}
        .controls input {{
            flex-grow: 1;
            min-width: 200px;
        }}
        .table-container {{
            overflow-x: auto;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin-bottom: 32px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            text-align: left;
        }}
        th, td {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{
            background: rgba(30, 36, 46, 0.9);
            color: var(--text-muted);
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background: rgba(45, 55, 72, 0.4);
        }}
        .score-pill {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.8rem;
        }}
        .score-100 {{ background: rgba(63, 185, 80, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }}
        .score-high {{ background: rgba(210, 153, 34, 0.2); color: var(--accent-yellow); border: 1px solid var(--accent-yellow); }}
        .score-low {{ background: rgba(248, 81, 73, 0.2); color: var(--accent-red); border: 1px solid var(--accent-red); }}
        .score-none {{ color: var(--text-muted); }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Multi-Cloud Frontier AI Evaluation Dashboard</h1>
            <div class="meta">Generated: {timestamp} | Endpoint: {cfg.base_url}</div>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="label">Total Models Evaluated</div>
            <div class="value">{len(models)}</div>
        </div>
        <div class="stat-card">
            <div class="label">Total Benchmarks Available</div>
            <div class="value">{len(benches)}</div>
        </div>
        <div class="stat-card">
            <div class="label">Average Accuracy</div>
            <div class="value">{avg_score:.1f}%</div>
        </div>
        <div class="stat-card">
            <div class="label">Top Model Score</div>
            <div class="value" style="color: var(--accent-green);">{top_score:.1f}%</div>
        </div>
    </div>

    <div class="controls">
        <input type="text" id="searchInput" placeholder="Search model or benchmark..." onkeyup="filterTable()">
    </div>

    <div class="table-container">
        <table id="resultsTable">
            <thead>
                <tr>
                    <th>Model</th>
                    {"".join(f"<th>{b}</th>" for b in benches)}
                </tr>
            </thead>
            <tbody>
    """
    
    for m in models:
        html += f"<tr><td><strong>{m}</strong></td>"
        for b in benches:
            v = grid[(m, b)]
            if v is None:
                html += "<td><span class='score-pill score-none'>—</span></td>"
            else:
                cls = "score-100" if v >= 95 else "score-high" if v >= 70 else "score-low"
                html += f"<td><span class='score-pill {cls}'>{v:.1f}%</span></td>"
        html += "</tr>"

    html += """
            </tbody>
        </table>
    </div>

    <script>
        function filterTable() {
            let input = document.getElementById("searchInput").value.toLowerCase();
            let rows = document.querySelectorAll("#resultsTable tbody tr");
            rows.forEach(row => {
                let text = row.innerText.toLowerCase();
                row.style.display = text.includes(input) ? "" : "none";
            });
        }
    </script>
</body>
</html>
"""
    return html


def render_markdown(cfg: Config) -> str:
    rows = build_comparison(cfg)
    models, benches, grid = measured_matrix(cfg)

    lines: list[str] = []
    lines.append("# Ollama Cloud — Evaluation Report")
    lines.append("")
    lines.append(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_  ")
    lines.append(f"_Endpoint: `{cfg.base_url}` · engine(s) as noted per row_")
    lines.append("")
    lines.append("> **Methodology caveat.** Measured scores use the builtin engine "
                 "(single-letter logprob / generate-parse for MCQ; final-answer exact-match "
                 "for math; subprocess execution for code). Vendor-advertised scores use "
                 "loglikelihood MCQ and pass\\@1 with more samples. A delta therefore mixes "
                 "**model quality and methodology** — not a pure quality verdict. See README.")
    lines.append("")

    # --- Measured matrix ------------------------------------------------
    lines.append("## Measured scores (model × benchmark)")
    lines.append("")
    if not models:
        lines.append("_No results yet — run `python -m src.runner` first._")
    else:
        header = "| Model | " + " | ".join(benches) + " |"
        sep = "|---" * (len(benches) + 1) + "|"
        lines += [header, sep]
        for m in models:
            cells = []
            for b in benches:
                v = grid[(m, b)]
                cells.append(f"{v}%" if v is not None else "—")
            lines.append(f"| {m} | " + " | ".join(cells) + " |")
    lines.append("")

    # --- Delta table ----------------------------------------------------
    lines.append("## Measured vs advertised (delta)")
    lines.append("")
    delta_rows = [r for r in rows if r.delta is not None]
    if not delta_rows:
        lines.append("_No benchmarks with both a measured score and a published reference yet._")
    else:
        lines.append("| Model | Benchmark | Measured | Advertised | Δ (meas−adv) | n |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for r in sorted(delta_rows, key=lambda x: x.delta):
            sign = "+" if r.delta >= 0 else ""
            lines.append(f"| {r.model} | {r.benchmark} | {r.measured}% | "
                         f"{r.advertised}% | {sign}{r.delta} | {r.n_items} |")
    lines.append("")

    # --- Skipped / errored ---------------------------------------------
    skipped = [r for r in rows if r.measured is None]
    if skipped:
        lines.append("## Skipped / not evaluated")
        lines.append("")
        lines.append("| Model | Benchmark | Reason |")
        lines.append("|---|---|---|")
        for r in skipped:
            lines.append(f"| {r.model} | {r.benchmark} | {r.note or 'no items'} |")
        lines.append("")

    lines.append("---")
    lines.append("_Numbers are reproducible given the same key, seed, and sampling defaults. "
                 "Re-run a benchmark to refresh its row._")
    return "\n".join(lines)


def main() -> int:
    cfg = load_config(require_key=False)
    rows = build_comparison(cfg)
    models, benches, grid = measured_matrix(cfg)

    # 1. Generate Markdown Report
    md = render_markdown(cfg)
    now_str = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out_md = REPORTS_DIR / f"comparison_{now_str}.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write(md)
    console.print(f"[green]Markdown Report written:[/green] {out_md}")

    # 2. Generate Interactive HTML Dashboard
    html = render_html_dashboard(cfg, rows, models, benches, grid)
    out_html = REPORTS_DIR / f"dashboard_{now_str}.html"
    with open(out_html, "w", encoding="utf-8") as fh:
        fh.write(html)
    console.print(f"[green]Interactive HTML Dashboard written:[/green] {out_html}")

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    console.print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())

