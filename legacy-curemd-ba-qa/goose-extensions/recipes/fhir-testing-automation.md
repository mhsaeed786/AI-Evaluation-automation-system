---
name: fhir-testing-automation
description: Automated FHIR resource testing, validation, and trigger verification workflow
---

# FHIR Testing Automation Recipe

## Prerequisites
- FHIR server accessible (10g or 11x)
- Database connection configured
- Trigger definitions available

## Steps

1. **Setup Phase**
   - Load config from config/settings.py
   - Verify database connectivity (APP_SERVER_10G/FHIR_DB or APP_SERVER_11X/MUII_DB)
   - Check FHIR server health endpoint

2. **Trigger Discovery**
   - Read trigger definitions from Pending Trigger Updates folders
   - Map triggers to Resource IDs and table/column relationships
   - Categorize as CREATE, UPDATE, or DELETE triggers

3. **Test Execution**
   - For each trigger:
     a. Execute INSERT test with minimal required columns
     b. Check FHIR_RecordQueue for new entry
     c. Execute UPDATE test on specific tracked columns
     d. Check FHIR_RecordQueue for update entry
     e. Execute DELETE test
     f. Check FHIR_RecordQueue for delete entry
   - Record pass/fail for each step
   - Capture actual vs expected results

4. **Report Generation**
   - Generate HTML report with pass/fail matrix
   - Generate text report with detailed query logs
   - Save to output/ directory

5. **Summary**
   - Total triggers tested
   - Pass rate percentage
   - Failed triggers with reasons
   - Recommendations for fixes
