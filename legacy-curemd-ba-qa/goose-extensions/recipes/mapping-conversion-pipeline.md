---
name: mapping-conversion-pipeline
description: Convert old FHIR mappings to USCDI V3 format across all pipelines
---

# Mapping Conversion Pipeline Recipe

## Steps

1. **Source Discovery**
   - Scan sharepoint_downloads folder for source files
   - Identify all mapping Excel files
   - Catalog resources covered in each file

2. **Format Analysis**
   - Read old format (dot-notation with indentation)
   - Read target format (USCDI V3 full hierarchy)
   - Identify conversion rules per column

3. **Conversion**
   - Convert each resource mapping:
     a. Expand dot-notation to full element paths
     b. Handle FHIR Resource Types and Data Types
     c. Respect cardinalities
     d. Map trigger columns to new format (Create Tables | Delete Tables | Update Columns)
   - Validate converted mappings against FHIR spec

4. **Gap Analysis**
   - Compare across pipelines: LEAP-10G, LEAP-11X, FHIR-10G, FHIR-11X, UDS+
   - Identify missing resources per pipeline
   - Flag incomplete mappings

5. **Output**
   - Generate unified workbooks per resource
   - Each workbook has sheets: LEAP10G, LEAP11X, FHIR10G, FHIR11X, UDS+, Triggers
   - Save to output/ directory
