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

Structure: application factory (`create_app`) + blueprints under src/webapp/
(results, compare, settings). Configuration comes from environment variables.
Errors are handled centrally: clients receive {error, correlationId} while the
detailed traceback is only logged server-side.

Uses threaded=True so concurrent API calls don't block each other.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid

from .config import PROJECT_ROOT

try:
    from flask import Flask, jsonify
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "The web UI needs Flask. Install it with:\n"
        "    pip install flask\n"
    ) from e

from .webapp import compare, results, settings  # noqa: E402

INDEX = PROJECT_ROOT / "templates" / "index.html"
APP_VERSION = "1.0.0"

logger = logging.getLogger("src.server")


class Config:
    """Environment-driven configuration for the dashboard app."""

    HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
    PORT = int(os.environ.get("DASHBOARD_PORT", "5000"))
    DEBUG = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    JSON_SORT_KEYS = False


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    # --- Health ---
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "version": APP_VERSION})

    # --- Page ---
    @app.get("/")
    def index():
        return INDEX.read_text(encoding="utf-8")

    # --- Blueprints ---
    app.register_blueprint(results.bp)
    app.register_blueprint(compare.bp)
    app.register_blueprint(settings.bp)

    # --- Centralized error handling ---
    @app.errorhandler(404)
    def not_found(err):
        return jsonify({"error": "not found",
                        "correlationId": str(uuid.uuid4())}), 404

    @app.errorhandler(405)
    def method_not_allowed(err):
        return jsonify({"error": "method not allowed",
                        "correlationId": str(uuid.uuid4())}), 405

    @app.errorhandler(Exception)
    def internal_error(err):
        cid = str(uuid.uuid4())
        logger.exception("Unhandled error [correlationId=%s]", cid)
        if app.config.get("DEBUG"):
            raise err  # let the dev server show the traceback when debugging
        return jsonify({"error": "internal error", "correlationId": cid}), 500

    return app


def main() -> int:
    ap = argparse.ArgumentParser(prog="ollama-eval-dashboard", description=__doc__)
    ap.add_argument("--host", default=Config.HOST)
    ap.add_argument("--port", type=int, default=Config.PORT)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    print(f"Dashboard: http://{args.host}:{args.port}   (Ctrl-C to stop)")
    create_app().run(host=args.host, port=args.port,
                     debug=args.debug or Config.DEBUG, threaded=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
