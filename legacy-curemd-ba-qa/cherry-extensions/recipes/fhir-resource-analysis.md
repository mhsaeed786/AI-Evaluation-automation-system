---
name: fhir-resource-analysis
description: Analyze FHIR resources for compliance and data quality (Cherry Studio recipe)
framework: cherry
---

# FHIR Resource Analysis Recipe (Cherry)

## Steps
1. Select FHIR resource type to analyze
2. Connect to configured FHIR server (10g or 11x)
3. Fetch resource instances with search parameters
4. Validate each instance against FHIR R4 profiles
5. Check USCDI V3 data class compliance
6. Cross-reference with database tables
7. Generate compliance report with findings

## Input Parameters
- `resource_type`: FHIR resource type (Patient, Encounter, etc.)
- `server`: healthos or public
- `check_uscdi`: boolean, check USCDI V3 compliance
- `db_key`: database environment for cross-reference

## Output
- Compliance percentage
- Missing elements list
- Data quality issues
- USCDI V3 coverage matrix
