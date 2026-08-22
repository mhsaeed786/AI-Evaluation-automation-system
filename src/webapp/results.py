"""Results blueprint: read-only eval result views and report exports."""
from __future__ import annotations

from flask import Blueprint, Response, jsonify

from .. import dashboard as D
from .common import get_cfg

bp = Blueprint("results", __name__, url_prefix="/api")


@bp.get("/overview")
def api_overview():
    return jsonify(D.overview(get_cfg()))


@bp.get("/matrix")
def api_matrix():
    return jsonify(D.matrix(get_cfg()))


@bp.get("/deltas")
def api_deltas():
    return jsonify(D.deltas(get_cfg()))


@bp.get("/providers")
def api_providers():
    return jsonify(D.providers_view(get_cfg()))


@bp.get("/runs")
def api_runs():
    return jsonify(D.run_history(get_cfg()))


@bp.get("/industry")
def api_industry():
    return jsonify(D.industry_reference(get_cfg()))


# --- Report export ---
@bp.get("/export/csv")
def export_csv():
    csv_str = D.export_csv(get_cfg())
    return Response(csv_str, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=eval_results.csv"})


@bp.get("/export/json")
def export_json():
    return Response(D.export_json(get_cfg()), mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=eval_results.json"})


@bp.get("/export/markdown")
def export_markdown():
    return Response(D.export_markdown(get_cfg()), mimetype="text/markdown",
                    headers={"Content-Disposition": "attachment; filename=eval_report.md"})
