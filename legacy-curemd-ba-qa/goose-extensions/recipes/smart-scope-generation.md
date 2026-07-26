---
name: smart-scope-generation
description: Generate complete SMART on FHIR v1 and v2 scopes with descriptions
---

# SMART Scope Generation Recipe

## Steps

1. **Resource Discovery**
   - Query FHIR server for all available resource types
   - Include: Patient, Condition, AllergyIntolerance, Immunization, Encounter, Provenance, Procedure, MedicationRequest, Coverage, Group, DiagnosticReport, Observation, ServiceRequest, etc.

2. **V1 Scope Generation**
   - For each resource: resource/*.read, resource/*.write, resource/*.*
   - Add patient-level scopes: patient/resource.read, patient/resource.write
   - Add user-level scopes: user/resource.read, user/resource.write

3. **V2 Scope Generation**
   - For each resource: system/Resource.read, system/Resource.write, system/Resource.cru
   - Add filter scopes: system/Resource.read?filter=value
   - Add patient-level: patient/Resource.read, patient/Resource.write
   - Add user-level: user/Resource.read, user/Resource.write

4. **Description Writing**
   - Generate user-friendly descriptions for each scope
   - Include what data the scope provides access to
   - Note sensitivity level

5. **Output**
   - Generate Excel file with all scopes
   - Generate JSON for FHIR server configuration
   - Include consent texts
