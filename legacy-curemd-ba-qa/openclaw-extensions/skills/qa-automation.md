---
name: qa-automation
description: QA automation skill for OpenClaw — test strategy and execution
framework: openclaw
---

# QA Automation Skill (OpenClaw)

## Capabilities
- Test case generation from requirements
- Automated regression test execution
- Test report generation (HTML, JSON)
- Coverage analysis and gap identification
- Database trigger testing methodology

## Test Types
1. **Unit**: Individual FHIR resource validation
2. **Integration**: End-to-end trigger → queue → server flow
3. **Regression**: Automated comparison of expected vs actual results
4. **Performance**: Response time and throughput testing

## Integration
Works with OneAgent's FHIR module tools for database queries,
FHIR server operations, and record queue verification.
