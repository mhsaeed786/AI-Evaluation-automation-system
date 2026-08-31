---
name: provenance-mapping-workflow
description: Complete provenance resource mapping for 10g and 11x EHRs
---

# Provenance Mapping Workflow Recipe

## Steps

1. **Database Connection Setup**
   - 10g: APP_SERVER_10G/FHIR_DB or MUII_DB
   - 11x: APP_SERVER_11X/MUII_DB

2. **Audit Trail Analysis**
   - Query tblauditrail for module names
   - Filter actions matching FHIR resource types
   - Map audit entries to Provenance resources

3. **Stored Procedure Discovery**
   - Search database for all SPs related to main tables
   - Read SP definitions
   - Extract insert/update logic
   - Document in separate columns

4. **Provenance File Generation**
   - Fill provenance remapping file for 10g columns
   - Fill provenance remapping file for 11x columns
   - Add SP/function names column
   - Add insert/update logic column

5. **Validation**
   - Cross-reference with existing FHIR resources
   - Verify Provenance resource completeness
   - Flag missing entries
