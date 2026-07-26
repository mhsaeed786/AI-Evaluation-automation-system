"""Local web UI for the evaluation system — full application.

    python -m src.server                 # http://127.0.0.1:5000
    python -m src.server --port 8080
    $env:DASHBOARD_PORT=8080; python -m src.server

A proper management application with:
  - Overview / Matrix / Deltas / Provider comparison / Run history tabs
  - Settings page (configure providers, select benchmarks, sampling)
  - Report download (CSV / JSON / Markdown)
  - Industry benchmark reference data
  - Model-vs-model comparison
  - Run trigger (opt-in via OLLAMA_EVAL_ENABLE_RUN=1)

Uses threaded=True so concurrent API calls don't block each other.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .config import PROJECT_ROOT, PROVIDERS, load_config
from . import dashboard as D

try:
    from flask import Flask, jsonify, request, Response
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "The web UI needs Flask. Install it with:\n"
        "    pip install flask\n"
    ) from e

INDEX = PROJECT_ROOT / "templates" / "index.html"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    def _cfg():
        return load_config(require_key=False)

    # --- Page ---
    @app.route("/")
    def index():
        return INDEX.read_text(encoding="utf-8")

    # --- Data APIs ---
    @app.route("/api/overview")
    def api_overview():
        return jsonify(D.overview(_cfg()))

    @app.route("/api/matrix")
    def api_matrix():
        return jsonify(D.matrix(_cfg()))

    @app.route("/api/deltas")
    def api_deltas():
        return jsonify(D.deltas(_cfg()))

    @app.route("/api/providers")
    def api_providers():
        return jsonify(D.providers_view(_cfg()))

    @app.route("/api/runs")
    def api_runs():
        return jsonify(D.run_history(_cfg()))

    @app.route("/api/config")
    def api_config():
        cfg = _cfg()
        return jsonify({
            "models": [m.get("id") for m in cfg.models.get("models", [])],
            "benchmarks": list(cfg.benchmarks.get("benchmarks", {}).keys()),
            "profiles": list(cfg.models.get("profiles", {}).keys()),
            "providers": list(PROVIDERS.keys()),
            "base_url": cfg.base_url,
        })

    # --- Settings ---
    @app.route("/api/settings", methods=["GET"])
    def api_settings_get():
        return jsonify(D.settings_view(_cfg()))

    @app.route("/api/settings", methods=["POST"])
    def api_settings_save():
        body = request.get_json(silent=True) or {}
        return jsonify(D.save_settings(_cfg(), body))

    # --- Industry reference ---
    @app.route("/api/industry")
    def api_industry():
        return jsonify(D.industry_reference(_cfg()))

    @app.route("/api/compare")
    def api_compare():
        a = request.args.get("a", "")
        b = request.args.get("b", "")
        if not a or not b:
            return jsonify({"error": "provide ?a=model1&b=model2"}), 400
        return jsonify(D.model_comparison(_cfg(), a, b))

    # --- Report export ---
    @app.route("/api/export/csv")
    def export_csv():
        csv_str = D.export_csv(_cfg())
        return Response(csv_str, mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=eval_results.csv"})

    @app.route("/api/export/json")
    def export_json():
        return Response(D.export_json(_cfg()), mimetype="application/json",
                        headers={"Content-Disposition": "attachment; filename=eval_results.json"})

    @app.route("/api/export/markdown")
    def export_markdown():
        return Response(D.export_markdown(_cfg()), mimetype="text/markdown",
                        headers={"Content-Disposition": "attachment; filename=eval_report.md"})

    # --- Run trigger ---
    @app.route("/api/run", methods=["POST"])
    def api_run():
        if os.environ.get("OLLAMA_EVAL_ENABLE_RUN") != "1":
            return jsonify({"ok": False,
                            "error": "run trigger disabled (set OLLAMA_EVAL_ENABLE_RUN=1)"}), 403
        cfg = _cfg()
        body = request.get_json(silent=True) or {}
        provider = str(body.get("provider", "all")).lower()
        if provider != "all" and provider not in PROVIDERS:
            provider = "ollama"
        engine = str(body.get("engine", "builtin"))
        if engine not in ("builtin", "lm_eval", "evalplus"):
            engine = "builtin"
        models = str(body.get("models", "auto")) or "auto"
        benchmarks = str(body.get("benchmarks", "mmlu,gsm8k")) or "mmlu,gsm8k"
        quick = bool(body.get("quick", True))
        argv = [sys.executable, "-m", "src.runner",
                "--provider", provider, "--models", models,
                "--benchmarks", benchmarks, "--engine", engine]
        if quick:
            argv.append("--quick")
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_dir / "run.log", "a", encoding="utf-8")
        try:
            subprocess.Popen(argv, cwd=str(PROJECT_ROOT),
                             stdout=log_fh, stderr=subprocess.STDOUT)
            return jsonify({"ok": True, "message": "run started — refresh in ~1 min"})
        except Exception as e:  # noqa: BLE001
            return jsonify({"ok": False, "error": repr(e)}), 500

    return app


def main() -> int:
    ap = argparse.ArgumentParser(prog="ollama-eval-dashboard", description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("DASHBOARD_PORT", "5000")))
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    print(f"Dashboard: http://{args.host}:{args.port}   (Ctrl-C to stop)")
    create_app().run(host=args.host, port=args.port, debug=args.debug, threaded=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())