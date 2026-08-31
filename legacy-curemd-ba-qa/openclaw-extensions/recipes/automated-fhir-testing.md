---
name: automated-fhir-testing
description: End-to-end automated FHIR testing workflow for OpenClaw
framework: openclaw
---

# Automated FHIR Testing Recipe (OpenClaw)

## Trigger
- Cron: every 6 hours
- Event: on code deployment to FHIR server

## Steps
1. Discover all FHIR resource types from server capabilities
2. For each resource type:
   a. Search for existing instances
   b. Validate each against R4 profiles
   c. Check USCDI V3 compliance
   d. Test CRUD operations
3. Run trigger tests against database
4. Cross-reference FHIR data with database tables
5. Generate test report
6. Fire event: test-complete with results

## Configuration
- `fhir_server`: healthos | public
- `db_environment`: release01_fhir | baseline11x_fhir
- `resource_types`: list or "all"
- `report_format`: html | json | both

## Output
- HTML dashboard with pass/fail per resource
- JSON results for programmatic access
- Coverage metrics
