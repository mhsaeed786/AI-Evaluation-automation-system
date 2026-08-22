"""Settings blueprint: configuration view/save and run trigger."""
from __future__ import annotations

import os
import subprocess
import sys

from flask import Blueprint, jsonify, request

from .. import dashboard as D
from ..config import PROJECT_ROOT, PROVIDERS
from .common import check_auth, get_cfg, invalidate_cfg

bp = Blueprint("settings", __name__, url_prefix="/api")


@bp.get("/config")
def api_config():
    cfg = get_cfg()
    return jsonify({
        "models": [m.get("id") for m in cfg.models.get("models", [])],
        "benchmarks": list(cfg.benchmarks.get("benchmarks", {}).keys()),
        "profiles": list(cfg.models.get("profiles", {}).keys()),
        "providers": list(PROVIDERS.keys()),
        "base_url": cfg.base_url,
    })


@bp.get("/settings")
def api_settings_get():
    return jsonify(D.settings_view(get_cfg()))


@bp.post("/settings")
def api_settings_save():
    denied = check_auth()
    if denied is not None:
        return denied
    body = request.get_json(silent=True) or {}
    result = D.save_settings(get_cfg(), body)
    invalidate_cfg()  # cached config now stale
    return jsonify(result)


# --- Run trigger ---
@bp.post("/run")
def api_run():
    denied = check_auth()
    if denied is not None:
        return denied
    if os.environ.get("OLLAMA_EVAL_ENABLE_RUN") != "1":
        return jsonify({"ok": False,
                        "error": "run trigger disabled (set OLLAMA_EVAL_ENABLE_RUN=1)"}), 403
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
        proc = subprocess.Popen(argv, cwd=str(PROJECT_ROOT),
                                stdout=log_fh, stderr=subprocess.STDOUT)
        log_fh.close()  # parent's copy; child keeps its inherited handles
        return jsonify({"ok": True, "message": "run started — refresh in ~1 min"})
    except Exception:  # noqa: BLE001
        raise  # handled by the app-wide error handler
