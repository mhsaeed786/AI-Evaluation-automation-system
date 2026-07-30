"""
FHIR R4 Resource Operations Module for HealthOS BA-QA Automation Suite.
Provides validate, search, create, read, update, delete, count, and capability statement actions.
"""

import json
import datetime
import uuid
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    """Main dispatch function for FHIR tools."""
    action = params.get("action", "")
    dispatch = {
        "validate": lambda: _dispatch_validate(params),
        "search": lambda: _dispatch_search(params),
        "create": lambda: _dispatch_create(params),
        "read": lambda: _dispatch_read(params),
        "update": lambda: _dispatch_update(params),
        "delete": lambda: _dispatch_delete(params),
        "count": lambda: _dispatch_count(params),
        "capability_statement": lambda: _dispatch_capability_statement(params),
    }
    handler = dispatch.get(action)
    if handler is None:
        return {"success": False, "error": f"Unknown action '{action}'. Available: {sorted(dispatch.keys())}"}
    try:
        return handler()
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Internal dispatch helpers
# ---------------------------------------------------------------------------

def _dispatch_validate(params):
    result = validate_resource(params.get("resource_type", ""), params.get("resource_json", {}))
    return {"success": True, "data": result}


def _dispatch_search(params):
    result = search_resources(
        params.get("base_url", ""),
        params.get("resource_type", ""),
        params.get("search_params", {}),
        token=params.get("token"),
    )
    return {"success": True, "data": result}


def _dispatch_create(params):
    result = create_resource(
        params.get("base_url", ""),
        params.get("resource_type", ""),
        params.get("resource_json", {}),
        token=params.get("token"),
    )
    return {"success": True, "data": result}


def _dispatch_read(params):
    result = read_resource(
        params.get("base_url", ""),
        params.get("resource_type", ""),
        params.get("resource_id", ""),
        token=params.get("token"),
    )
    return {"success": True, "data": result}


def _dispatch_update(params):
    result = update_resource(
        params.get("base_url", ""),
        params.get("resource_type", ""),
        params.get("resource_id", ""),
        params.get("resource_json", {}),
        token=params.get("token"),
    )
    return {"success": True, "data": result}


def _dispatch_delete(params):
    result = delete_resource(
        params.get("base_url", ""),
        params.get("resource_type", ""),
        params.get("resource_id", ""),
        token=params.get("token"),
    )
    return {"success": True, "data": result}


def _dispatch_count(params):
    result = count_resources(
        params.get("base_url", ""),
        params.get("resource_type", ""),
        patient_id=params.get("patient_id"),
        token=params.get("token"),
    )
    return {"success": True, "data": {"count": result}}


def _dispatch_capability_statement(params):
    result = get_capability_statement(
        params.get("base_url", ""),
        token=params.get("token"),
    )
    return {"success": True, "data": result}


# ---------------------------------------------------------------------------
# FHIR R4 Resource Validation
# ---------------------------------------------------------------------------

FHIR_R4_REQUIRED_FIELDS = {
    "Patient": {"name", "gender"},
    "Observation": {"status", "code", "subject"},
    "Practitioner": {"name"},
    "Encounter": {"status", "class"},
    "Condition": {"subject", "clinicalStatus"},
    "MedicationRequest": {"subject", "medication"},
    "DiagnosticReport": {"status", "code", "subject"},
    "Procedure": {"subject", "status"},
    "AllergyIntolerance": {"patient"},
    "Immunization": {"patient", "vaccineCode"},
    "Organization": {"name"},
    "Location": {"name"},
    "Device": {"type"},
    "Provenance": {"target", "recorded"},
    "Bundle": {"type"},
}

FHIR_R4_STATUSES = {
    "Observation": ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"],
    "Encounter": ["planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled", "entered-in-error", "unknown"],
    "Condition": ["active", "recurrence", "relapse", "inactive", "remission", "resolved", "unknown"],
    "DiagnosticReport": ["registered", "partial", "preliminary", "final", "amended", "corrected", "appended", "cancelled", "entered-in-error", "unknown"],
    "Procedure": ["preparation", "in-progress", "not-done", "on-hold", "stopped", "completed", "entered-in-error", "unknown"],
}


def validate_resource(resource_type: str, resource_json: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a FHIR R4 resource against structural rules."""
    issues = []

    if not resource_type:
        issues.append({"severity": "error", "code": "required", "details": "resource_type is required"})
        return {"valid": False, "issues": issues}

    if not isinstance(resource_json, dict):
        issues.append({"severity": "error", "code": "structure", "details": "resource_json must be a dictionary"})
        return {"valid": False, "issues": issues}

    # Check resourceType field matches
    rt = resource_json.get("resourceType")
    if rt and rt != resource_type:
        issues.append({
            "severity": "error",
            "code": "invariant",
            "details": f"resourceType '{rt}' does not match expected '{resource_type}'",
            "expression": ["resourceType"],
        })

    # Check required fields
    required = FHIR_R4_REQUIRED_FIELDS.get(resource_type, set())
    for field in required:
        if field not in resource_json:
            issues.append({
                "severity": "error",
                "code": "required",
                "details": f"Missing required field: {field}",
                "expression": [field],
            })

    # Validate status fields
    if resource_type in FHIR_R4_STATUSES:
        status = resource_json.get("status")
        if status and status not in FHIR_R4_STATUSES[resource_type]:
            issues.append({
                "severity": "error",
                "code": "value",
                "details": f"Invalid status '{status}'. Allowed: {FHIR_R4_STATUSES[resource_type]}",
                "expression": ["status"],
            })

    # Validate name arrays for Patient/Practitioner
    if resource_type in ("Patient", "Practitioner") and "name" in resource_json:
        names = resource_json["name"]
        if not isinstance(names, list) or len(names) == 0:
            issues.append({
                "severity": "error",
                "code": "structure",
                "details": "name must be a non-empty array",
                "expression": ["name"],
            })
        for idx, nm in enumerate(names if isinstance(names, list) else []):
            if not isinstance(nm, dict):
                continue
            if "family" not in nm and "text" not in nm:
                issues.append({
                    "severity": "warning",
                    "code": "business-rule",
                    "details": f"name[{idx}] missing 'family' or 'text'",
                    "expression": [f"name[{idx}]"],
                })

    # Validate gender for Patient
    if resource_type == "Patient" and "gender" in resource_json:
        valid_genders = ["male", "female", "other", "unknown"]
        if resource_json["gender"] not in valid_genders:
            issues.append({
                "severity": "error",
                "code": "value",
                "details": f"Invalid gender '{resource_json['gender']}'. Allowed: {valid_genders}",
                "expression": ["gender"],
            })

    # Validate Coding / CodeableConcept
    for key in ("code", "type", "vaccineCode", "class", "valueCodeableConcept"):
        val = resource_json.get(key)
        if val and isinstance(val, dict):
            codings = val.get("coding", [])
            for ci, coding in enumerate(codings if isinstance(codings, list) else []):
                if not coding.get("system"):
                    issues.append({
                        "severity": "warning",
                        "code": "business-rule",
                        "details": f"{key}.coding[{ci}] missing 'system'",
                        "expression": [f"{key}.coding[{ci}].system"],
                    })
                if not coding.get("code"):
                    issues.append({
                        "severity": "warning",
                        "code": "business-rule",
                        "details": f"{key}.coding[{ci}] missing 'code'",
                        "expression": [f"{key}.coding[{ci}].code"],
                    })

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    return {
        "valid": len(errors) == 0,
        "resource_type": resource_type,
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# FHIR HTTP Operations
# ---------------------------------------------------------------------------

def _build_headers(token: Optional[str] = None) -> Dict[str, str]:
    """Build standard FHIR R4 request headers."""
    headers = {
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json",
        "Prefer": "return=representation",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _make_opoutcome(severity: str, code: str, details: str) -> Dict[str, Any]:
    """Build a FHIR OperationOutcome dict."""
    return {
        "resourceType": "OperationOutcome",
        "issue": [{
            "severity": severity,
            "code": code,
            "details": {"text": details},
        }],
    }


def search_resources(base_url: str, resource_type: str, params: Dict[str, Any],
                     token: Optional[str] = None) -> Dict[str, Any]:
    """Search FHIR resources, returns a Bundle."""
    if requests is None:
        return _make_opoutcome("error", "exception", "requests library not installed")
    url = f"{base_url.rstrip('/')}/{resource_type}"
    try:
        resp = requests.get(url, params=params, headers=_build_headers(token), timeout=30)
        if resp.status_code >= 400:
            return _make_opoutcome("error", "exception",
                                   f"HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()
    except requests.RequestException as exc:
        return _make_opoutcome("error", "exception", str(exc))


def create_resource(base_url: str, resource_type: str, resource_json: Dict[str, Any],
                    token: Optional[str] = None) -> Dict[str, Any]:
    """Create a FHIR resource via POST."""
    if requests is None:
        return _make_opoutcome("error", "exception", "requests library not installed")
    url = f"{base_url.rstrip('/')}/{resource_type}"
    resource_json.setdefault("resourceType", resource_type)
    try:
        resp = requests.post(url, json=resource_json, headers=_build_headers(token), timeout=30)
        if resp.status_code not in (200, 201):
            return _make_opoutcome("error", "exception",
                                   f"HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()
    except requests.RequestException as exc:
        return _make_opoutcome("error", "exception", str(exc))


def read_resource(base_url: str, resource_type: str, resource_id: str,
                  token: Optional[str] = None) -> Dict[str, Any]:
    """Read a single FHIR resource by ID."""
    if requests is None:
        return _make_opoutcome("error", "exception", "requests library not installed")
    url = f"{base_url.rstrip('/')}/{resource_type}/{resource_id}"
    try:
        resp = requests.get(url, headers=_build_headers(token), timeout=30)
        if resp.status_code == 404:
            return _make_opoutcome("error", "not-found",
                                   f"{resource_type}/{resource_id} not found")
        if resp.status_code >= 400:
            return _make_opoutcome("error", "exception",
                                   f"HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()
    except requests.RequestException as exc:
        return _make_opoutcome("error", "exception", str(exc))


def update_resource(base_url: str, resource_type: str, resource_id: str,
                    resource_json: Dict[str, Any], token: Optional[str] = None) -> Dict[str, Any]:
    """Update a FHIR resource via PUT."""
    if requests is None:
        return _make_opoutcome("error", "exception", "requests library not installed")
    url = f"{base_url.rstrip('/')}/{resource_type}/{resource_id}"
    resource_json["resourceType"] = resource_type
    resource_json["id"] = resource_id
    try:
        resp = requests.put(url, json=resource_json, headers=_build_headers(token), timeout=30)
        if resp.status_code >= 400:
            return _make_opoutcome("error", "exception",
                                   f"HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()
    except requests.RequestException as exc:
        return _make_opoutcome("error", "exception", str(exc))


def delete_resource(base_url: str, resource_type: str, resource_id: str,
                    token: Optional[str] = None) -> Dict[str, Any]:
    """Delete a FHIR resource."""
    if requests is None:
        return _make_opoutcome("error", "exception", "requests library not installed")
    url = f"{base_url.rstrip('/')}/{resource_type}/{resource_id}"
    try:
        resp = requests.delete(url, headers=_build_headers(token), timeout=30)
        if resp.status_code == 204:
            return {"resourceType": "OperationOutcome",
                    "issue": [{"severity": "information", "code": "informational",
                               "details": {"text": f"{resource_type}/{resource_id} deleted"}}]}
        if resp.status_code >= 400:
            return _make_opoutcome("error", "exception",
                                   f"HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json() if resp.text else {"deleted": True}
    except requests.RequestException as exc:
        return _make_opoutcome("error", "exception", str(exc))


def count_resources(base_url: str, resource_type: str, patient_id: Optional[str] = None,
                    token: Optional[str] = None) -> int:
    """Count FHIR resources, optionally filtered by patient."""
    if requests is None:
        return -1
    params: Dict[str, str] = {"_summary": "count"}
    if patient_id:
        params["patient"] = patient_id
    url = f"{base_url.rstrip('/')}/{resource_type}"
    try:
        resp = requests.get(url, params=params, headers=_build_headers(token), timeout=30)
        if resp.status_code >= 400:
            return -1
        bundle = resp.json()
        return bundle.get("total", 0)
    except requests.RequestException:
        return -1


def get_capability_statement(base_url: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Fetch the server's CapabilityStatement."""
    if requests is None:
        return _make_opoutcome("error", "exception", "requests library not installed")
    url = f"{base_url.rstrip('/')}/metadata"
    try:
        resp = requests.get(url, headers=_build_headers(token), timeout=30)
        if resp.status_code >= 400:
            return _make_opoutcome("error", "exception",
                                   f"HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()
    except requests.RequestException as exc:
        return _make_opoutcome("error", "exception", str(exc))


# ---------------------------------------------------------------------------
# FHIR Resource Builders
# ---------------------------------------------------------------------------

def build_patient(first_name: str, last_name: str, dob: str, gender: str) -> Dict[str, Any]:
    """Build a FHIR R4 Patient resource dict."""
    return {
        "resourceType": "Patient",
        "id": str(uuid.uuid4()),
        "name": [{
            "use": "official",
            "family": last_name,
            "given": [first_name],
        }],
        "gender": gender,
        "birthDate": dob,
        "identifier": [{
            "system": "urn:ietf:rfc:3986",
            "value": str(uuid.uuid4()),
        }],
        "active": True,
    }


def build_observation(patient_id: str, code: str, value: Any) -> Dict[str, Any]:
    """Build a FHIR R4 Observation resource dict."""
    obs = {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": code,
            }],
        },
        "subject": {
            "reference": f"Patient/{patient_id}",
        },
        "effectiveDateTime": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if isinstance(value, (int, float)):
        obs["valueQuantity"] = {"value": value}
    elif isinstance(value, str):
        obs["valueString"] = value
    elif isinstance(value, dict):
        obs["valueCodeableConcept"] = value
    return obs
