"""
LEAP Module — merged from 5 LEAP forks (scaling, RWT, analytics, support, UDS+).

Provides tools for LEAP-related analytics, reporting, and workflow automation.
"""

import logging
from typing import Any, Dict, List, Optional

from core.agents.tools import get_registry, tool

logger = logging.getLogger(__name__)


@tool(name="leap_analytics", description="Generate LEAP analytics reports for 10g and 11x environments", module="leap")
def leap_analytics(report_type: str = "summary", db_key: str = "release01_fhir", pipeline: str = "LEAP-10G") -> Dict:
    """Generate analytics reports for LEAP pipelines."""
    from config.databases import get_db_manager
    db = get_db_manager()

    queries = {
        "summary": "SELECT ResourceName, COUNT(*) as count FROM FHIR_RecordQueue GROUP BY ResourceName ORDER BY count DESC",
        "coverage": "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME",
        "status": "SELECT TOP 50 * FROM FHIR_RecordQueue ORDER BY QueueID DESC",
    }

    query = queries.get(report_type, queries["summary"])
    try:
        results = db.execute_query(query, db_key=db_key)
        return {"report_type": report_type, "pipeline": pipeline, "data": results}
    except Exception as e:
        return {"error": str(e)}


@tool(name="leap_scaling_report", description="Generate LEAP scaling analysis report", module="leap")
def leap_scaling_report(db_key: str = "release01_fhir") -> Dict:
    """Analyze LEAP scaling metrics."""
    from config.databases import get_db_manager
    db = get_db_manager()
    try:
        tables = db.get_tables(db_key)
        triggers = db.get_triggers(db_key)
        fhir_resources = db.execute_query(
            "SELECT ResourceName, COUNT(*) as cnt FROM FHIR_RecordQueue GROUP BY ResourceName",
            db_key=db_key,
        )
        return {
            "total_tables": len(tables),
            "total_triggers": len(triggers),
            "fhir_resources": fhir_resources,
            "environment": db_key,
        }
    except Exception as e:
        return {"error": str(e)}


@tool(name="leap_uds_report", description="Generate UDS+ report for LEAP pipeline", module="leap")
def leap_uds_report(db_key: str = "baseline11x_muii") -> Dict:
    """Generate UDS+ specific report from 11x environment."""
    from config.databases import get_db_manager
    db = get_db_manager()
    try:
        tables = db.get_tables(db_key)
        return {"environment": "11x", "database": db_key, "tables_count": len(tables), "status": "generated"}
    except Exception as e:
        return {"error": str(e)}


@tool(name="leap_rwt_analysis", description="RWT (Revenue Workstream Tracker) analysis for LEAP", module="leap")
def leap_rwt_analysis(db_key: str = "release01_fhir") -> Dict:
    """Analyze RWT data across LEAP pipelines."""
    from config.databases import get_db_manager
    db = get_db_manager()
    try:
        sps = db.get_stored_procedures(db_key)
        return {"stored_procedures": len(sps), "environment": db_key}
    except Exception as e:
        return {"error": str(e)}


def register():
    return {
        "name": "leap",
        "description": "LEAP analytics — scaling, RWT, UDS+, support metrics",
        "version": "2.0.0",
        "tools": ["leap_analytics", "leap_scaling_report", "leap_uds_report", "leap_rwt_analysis"],
        "routes": [
            {"method": "GET", "path": "/leap/analytics", "handler": "leap_analytics"},
            {"method": "GET", "path": "/leap/scaling", "handler": "leap_scaling_report"},
            {"method": "GET", "path": "/leap/uds", "handler": "leap_uds_report"},
            {"method": "GET", "path": "/leap/rwt", "handler": "leap_rwt_analysis"},
        ],
    }
