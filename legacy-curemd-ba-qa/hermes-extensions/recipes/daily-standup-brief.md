---
name: daily-standup-brief
description: Generate daily standup brief from work items and emails (Hermes)
framework: hermes
schedule: "30 7 * * 1-5"  # Weekdays 7:30 AM
---

# Daily Standup Brief (Hermes)

## Schedule
Weekdays at 7:30 AM

## Steps
1. Fetch recent emails from Outlook (last 24h)
2. Fetch recent Teams messages
3. Query Azure DevOps for updated work items
4. Summarize FHIR RecordQueue activity
5. Generate standup brief
6. Send to configured channel

## Output
- Structured standup brief:
  - What was done yesterday
  - What's planned today
  - Blockers and issues
  - Key metrics (FHIR resources processed, tests run)
