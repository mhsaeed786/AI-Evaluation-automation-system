---
name: weekly-fhir-audit
description: Weekly FHIR compliance and data quality audit (Hermes scheduled task)
framework: hermes
schedule: "0 8 * * 1"  # Every Monday 8am
---

# Weekly FHIR Audit (Hermes)

## Schedule
Every Monday at 8:00 AM

## Steps
1. Connect to FHIR server (10g and 11x)
2. Query all resource types and counts
3. Validate sample resources against R4 profiles
4. Check FHIR_RecordQueue for stuck entries
5. Run inconsistency detection queries
6. Generate compliance report
7. Send summary notification

## Output
- Compliance dashboard update
- Email summary to stakeholders
- JSON results stored in data/audits/

## Configurable Parameters
- `environments`: [release01_fhir, baseline11x_fhir]
- `sample_size`: 50
- `report_recipients`: [hassan.saeed@example.com]
- `notify_on_failure`: true
