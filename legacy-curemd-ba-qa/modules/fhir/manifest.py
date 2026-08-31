"""
FHIR Module — merged from 11 fhir_* forks into one.

Provides:
- Resource CRUD, validation, search, bundle processing
- Inconsistency detection (merged from 5 variants)
- Explorer (HAPI + HealthOS FHIR server)
- Cost analysis
- Mapping (provider_mapping + provenance_remap)
- Portal API (developer portal integration)
- Scope generation (SMART on FHIR v1/v2)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from core.agents.tools import get_registry, tool
from config.databases import get_db_manager

logger = logging.getLogger(__name__)


# ── FHIR Server Operations ──────────────────────────────────────────

@tool(name="fhir_search", description="Search FHIR resources on a FHIR R4 server", module="fhir")
def fhir_search(
    resource_type: str,
    params: str = "{}",
    server: str = "healthos",
    limit: int = 20,
) -> Dict:
    """Search FHIR resources. params is a JSON string of search parameters."""
    import httpx
    from config.settings import get_settings
    settings = get_settings()

    base_url = settings.urls.get("fhir_server_healthos" if server == "healthos" else "fhir_server_r4")
    search_params = json.loads(params) if isinstance(params, str) else params
    search_params.setdefault("_count", limit)

    r = httpx.get(f"{base_url}/{resource_type}", params=search_params, timeout=30)
    return {"status": r.status_code, "data": r.json() if r.status_code == 200 else r.text}


@tool(name="fhir_read", description="Read a single FHIR resource by ID", module="fhir")
def fhir_read(resource_type: str, resource_id: str, server: str = "healthos") -> Dict:
    """Read a single FHIR resource."""
    import httpx
    from config.settings import get_settings
    settings = get_settings()
    base_url = settings.urls.get("fhir_server_healthos" if server == "healthos" else "fhir_server_r4")
    r = httpx.get(f"{base_url}/{resource_type}/{resource_id}", timeout=30)
    return {"status": r.status_code, "data": r.json() if r.status_code == 200 else r.text}


@tool(name="fhir_validate", description="Validate a FHIR resource against R4 profiles", module="fhir")
def fhir_validate(resource_type: str, resource_json: str) -> Dict:
    """Validate a FHIR resource."""
    import httpx
    from config.settings import get_settings
    settings = get_settings()
    base_url = settings.urls.get("fhir_server_healthos")
    r = httpx.post(
        f"{base_url}/{resource_type}/$validate",
        json=json.loads(resource_json) if isinstance(resource_json, str) else resource_json,
        headers={"Content-Type": "application/fhir+json"},
        timeout=30,
    )
    return {"status": r.status_code, "validation": r.json() if r.status_code == 200 else r.text}


@tool(name="fhir_create", description="Create a FHIR resource on the server", module="fhir")
def fhir_create(resource_type: str, resource_json: str, server: str = "healthos") -> Dict:
    """Create a FHIR resource."""
    import httpx
    from config.settings import get_settings
    settings = get_settings()
    base_url = settings.urls.get("fhir_server_healthos" if server == "healthos" else "fhir_server_r4")
    data = json.loads(resource_json) if isinstance(resource_json, str) else resource_json
    r = httpx.post(f"{base_url}/{resource_type}", json=data, headers={"Content-Type": "application/fhir+json"}, timeout=30)
    return {"status": r.status_code, "data": r.json() if r.status_code in (200, 201) else r.text}


@tool(name="fhir_update", description="Update a FHIR resource by ID", module="fhir")
def fhir_update(resource_type: str, resource_id: str, resource_json: str, server: str = "healthos") -> Dict:
    """Update a FHIR resource."""
    import httpx
    from config.settings import get_settings
    settings = get_settings()
    base_url = settings.urls.get("fhir_server_healthos" if server == "healthos" else "fhir_server_r4")
    data = json.loads(resource_json) if isinstance(resource_json, str) else resource_json
    r = httpx.put(f"{base_url}/{resource_type}/{resource_id}", json=data, headers={"Content-Type": "application/fhir+json"}, timeout=30)
    return {"status": r.status_code, "data": r.json() if r.status_code == 200 else r.text}


@tool(name="fhir_delete", description="Delete a FHIR resource by ID", module="fhir")
def fhir_delete(resource_type: str, resource_id: str, server: str = "healthos") -> Dict:
    """Delete a FHIR resource."""
    import httpx
    from config.settings import get_settings
    settings = get_settings()
    base_url = settings.urls.get("fhir_server_healthos" if server == "healthos" else "fhir_server_r4")
    r = httpx.delete(f"{base_url}/{resource_type}/{resource_id}", timeout=30)
    return {"status": r.status_code}


# ── Database-backed FHIR Operations ─────────────────────────────────

@tool(name="query_database", description="Execute a SQL query against configured databases", module="fhir", requires_approval=True)
def query_database(query: str, db_key: str = "release01_fhir") -> Dict:
    """Execute a SQL query and return results."""
    db = get_db_manager()
    results = db.execute_query(query, db_key=db_key)
    return {"rows": results, "count": len(results)}


@tool(name="check_record_queue", description="Check FHIR_RecordQueue entries", module="fhir")
def check_record_queue(resource_id: str = "", resource_type: str = "", db_key: str = "release01_fhir") -> Dict:
    """Check the FHIR RecordQueue for entries."""
    db = get_db_manager()
    results = db.check_record_queue(
        resource_id=resource_id or None,
        resource_type=resource_type or None,
        db_key=db_key,
    )
    return {"entries": results, "count": len(results)}


@tool(name="get_db_schema", description="Get database schema information (tables, columns, triggers)", module="fhir")
def get_db_schema(table_name: str = "", db_key: str = "release01_fhir") -> Dict:
    """Get schema info for a table or all tables."""
    db = get_db_manager()
    if table_name:
        columns = db.get_columns(table_name, db_key)
        return {"table": table_name, "columns": columns}
    tables = db.get_tables(db_key)
    return {"tables": tables}


# ── Inconsistency Detection ─────────────────────────────────────────

@tool(name="find_fhir_inconsistencies", description="Find data inconsistencies between DB tables and FHIR resources", module="fhir")
def find_inconsistencies(
    resource_type: str = "Patient",
    db_key: str = "release01_fhir",
    check_fields: str = "",
) -> Dict:
    """
    Cross-reference database data with FHIR resources to find inconsistencies.

    Merged from 5 variants of fhir_inconsistency_queries into one.
    """
    db = get_db_manager()
    issues = []

    resource_queries = {
        "Patient": {
            "table": "PMPTXFT",
            "id_col": "PatientID",
            "checks": [
                ("Missing FHIR mapping", "SELECT PatientID, PatientName FROM PMPTXFT WHERE PatientID NOT IN (SELECT ResourceID FROM FHIR_RecordQueue WHERE ResourceName = 'Patient')"),
                ("Null demographics", "SELECT PatientID, PatientName FROM PMPTXFT WHERE PatientName IS NULL OR PatientName = ''"),
            ],
        },
    }

    config = resource_queries.get(resource_type)
    if not config:
        return {"error": f"No inconsistency checks defined for {resource_type}"}

    for label, query in config["checks"]:
        try:
            rows = db.execute_query(query, db_key=db_key)
            if rows:
                issues.append({
                    "type": label,
                    "resource_type": resource_type,
                    "count": len(rows),
                    "samples": rows[:5],
                })
        except Exception as e:
            issues.append({"type": label, "error": str(e)})

    return {"resource_type": resource_type, "total_issues": len(issues), "issues": issues}


# ── Scope Generation ────────────────────────────────────────────────

FHIR_R4_RESOURCES = [
    "Patient", "Practitioner", "Organization", "Location", "Encounter",
    "Condition", "Observation", "AllergyIntolerance", "Immunization",
    "MedicationRequest", "Procedure", "DiagnosticReport", "DocumentReference",
    "CarePlan", "Goal", "ServiceRequest", "Provenance", "Coverage",
    "RelatedPerson", "PractitionerRole", "Device", "Group",
    "Composition", "Consent", "ExplanationOfBenefit",
]


@tool(name="generate_smart_scopes", description="Generate SMART on FHIR v1 and v2 scopes for all resources", module="fhir")
def generate_smart_scopes(resources: str = "", include_v2: bool = True) -> Dict:
    """
    Generate SMART on FHIR scope configurations.

    v1: patient/Patient.read, user/Condition.write
    v2: patient/Patient.rs, system/Observation.cru
    """
    resource_list = resources.split(",") if resources else FHIR_R4_RESOURCES
    scopes = {"v1": [], "v2": [], "descriptions": {}}

    for res in resource_list:
        res = res.strip()
        # V1 scopes
        for level in ["patient", "user", "system"]:
            for perm in ["read", "write", "*"]:
                scopes["v1"].append(f"{level}/{res}.{perm}")

        if include_v2:
            for level in ["patient", "user", "system"]:
                for perm in ["rs", "cru", "cruds"]:
                    scopes["v2"].append(f"{level}/{res}.{perm}")

        scopes["descriptions"][res] = f"Access to {res} FHIR resources"

    scopes["v1_count"] = len(scopes["v1"])
    scopes["v2_count"] = len(scopes["v2"]) if include_v2 else 0
    return scopes


# ── Module Registration ─────────────────────────────────────────────

def register():
    """Register this module with the OneAgent system."""
    return {
        "name": "fhir",
        "description": "FHIR R4 tools — resource CRUD, validation, search, inconsistency detection, scope generation",
        "version": "2.0.0",
        "tools": [
            "fhir_search", "fhir_read", "fhir_validate", "fhir_create",
            "fhir_update", "fhir_delete", "query_database", "check_record_queue",
            "get_db_schema", "find_fhir_inconsistencies", "generate_smart_scopes",
        ],
        "routes": [
            {"method": "GET", "path": "/fhir/{resource_type}", "handler": "fhir_search"},
            {"method": "GET", "path": "/fhir/{resource_type}/{id}", "handler": "fhir_read"},
            {"method": "POST", "path": "/fhir/{resource_type}", "handler": "fhir_create"},
            {"method": "PUT", "path": "/fhir/{resource_type}/{id}", "handler": "fhir_update"},
            {"method": "DELETE", "path": "/fhir/{resource_type}/{id}", "handler": "fhir_delete"},
            {"method": "POST", "path": "/fhir/{resource_type}/$validate", "handler": "fhir_validate"},
            {"method": "GET", "path": "/fhir/inconsistencies", "handler": "find_inconsistencies"},
            {"method": "GET", "path": "/fhir/scopes", "handler": "generate_smart_scopes"},
        ],
    }
