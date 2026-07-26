---
name: mapping-conversion-pipeline
description: Automated mapping conversion from old format to USCDI V3 (OpenClaw)
framework: openclaw
---

# Mapping Conversion Pipeline (OpenClaw)

## Trigger
- Event: on new mapping file uploaded
- Manual: on-demand

## Steps
1. Watch for new mapping files in SharePoint
2. Download and parse old format
3. Convert dot-notation to USCDI V3 hierarchy
4. Generate trigger mapping sheets
5. Cross-pipeline gap analysis
6. Generate unified workbooks
7. Upload results to SharePoint

## Pipelines
LEAP-10G, LEAP-11X, FHIR-10G, FHIR-11X, UDS+
