"""Shared state and helpers for the dashboard blueprints."""
from __future__ import annotations

import os

from flask import jsonify, request

from ..config import load_config

# Cache config once; invalidated when settings change.
cfg_cache: dict = {"cfg": load_config(require_key=False)}


def get_cfg():
    return cfg_cache["cfg"]


def invalidate_cfg() -> None:
    cfg_cache["cfg"] = load_config(require_key=False)


def check_auth():
    """Require X-Auth-Token to match AUTH_TOKEN env when it is set.

    Returns a JSON error response when unauthorized, else None.
    """
    expected = os.environ.get("AUTH_TOKEN")
    if not expected:
        return None  # auth unset -> backwards-compatible open access
    if request.headers.get("X-Auth-Token") != expected:
        return jsonify({"error": "unauthorized"}), 401
    return None
