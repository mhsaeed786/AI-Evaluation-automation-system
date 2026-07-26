---
name: healthcare-qa-dashboard
description: Generate comprehensive QA dashboard for healthcare IT testing status
---

# Healthcare QA Dashboard Recipe

## Steps

1. **Data Collection**
   - Scan all test results from output/ directory
   - Read trigger test reports
   - Read FHIR validation results
   - Read mapping conversion status

2. **Status Aggregation**
   - Trigger test pass rates
   - FHIR resource coverage
   - USCDI V3 compliance percentage
   - Outstanding issues count

3. **Dashboard Generation**
   - Create HTML dashboard with charts
   - Show trends over time
   - Highlight blockers
   - List next priorities

4. **Export**
   - Save dashboard HTML
   - Generate summary email content
   - Update status files
