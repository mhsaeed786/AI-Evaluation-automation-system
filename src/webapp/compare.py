"""Compare blueprint: model-vs-model comparison."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from .. import dashboard as D
from .common import get_cfg

bp = Blueprint("compare", __name__, url_prefix="/api")


@bp.get("/compare")
def api_compare():
    a = request.args.get("a", "")
    b = request.args.get("b", "")
    if not a or not b:
        return jsonify({"error": "provide ?a=model1&b=model2"}), 400
    return jsonify(D.model_comparison(get_cfg(), a, b))
