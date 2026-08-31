# HealthOS BA/QA Automation Suite

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

**Enterprise Healthcare IT Automation Platform**

*FHIR Testing • DB Trigger Analysis • USCDI V3 Mapping • Gap Analysis • Smart Scope Generation*

[Quick Start](#quick-start) • [Features](#features) • [Architecture](#architecture) • [Configuration](#configuration) • [Modules](#modules)

</div>

---

## Quick Start

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Internet connection for initial dependency installation

### Installation

1. **Clone or download** this repository to your local machine
2. **Double-click `run.bat`** for one-click launch, OR run manually:

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the application
streamlit run ui/app.py --server.port 8501
```

3. Open your browser at **http://localhost:8501**

### Environment Variables (Optional)

Create a `.env` file or set these environment variables for LLM features:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AI...
DEEPSEEK_API_KEY=dsk-...
GROQ_API_KEY=gsk_...
OLLAMA_HOST=http://localhost:11434
MISTRAL_API_KEY=...
COHERE_API_KEY=...
```

---

## Features

### Core Capabilities
- **Multi-Provider LLM Router** — Route AI queries across OpenAI, Anthropic, Gemini, DeepSeek, Ollama, Groq, Mistral, and Cohere with automatic fallback chains and cost optimization
- **Autonomous Agent Loop** — Plan → Execute → Observe → Reflect cycle with configurable approval modes
- **Persistent Memory** — SQLite-backed semantic memory with importance scoring and decay
- **Cron-like Scheduler** — Schedule recurring automation tasks

### Healthcare IT Modules

| Module | Description |
|--------|-------------|
| **FHIR Tools** | Resource CRUD, validation, search, bundle processing against FHIR servers |
| **Trigger Tester** | Database trigger testing with FHIR_RecordQueue verification |
| **Mapping Converter** | Old FHIR format to USCDI V3 conversion with trigger mapping sheets |
| **Provenance Remapper** | Provenance resource mapping for 10g/11x environments |
| **DB Analyzer** | Full database schema mapping and cross-reference analysis |
| **Scope Generator** | SMART on FHIR v1/v2 scope generation for all resources |
| **SNOMED Validator** | SNOMED CT and HL7 code validation with terminology lookups |
| **Gap Analyzer** | Azure DevOps work item gap analysis with coverage reports |
| **Web Discovery** | Browser-based DOM discovery with automated script generation |
| **Email/Teams Extractor** | Outlook email and Teams message extraction via Playwright |
| **SharePoint Downloader** | SharePoint document and attachment batch download |
| **DevOps Automation** | Azure DevOps UI automation for bulk operations |
| **Content Generator** | Multi-platform content automation for documentation |
| **Music Creator** | AI music prompt generation (Minimax integration) |
| **Learning Engine** | Microlearning paths and knowledge assessment |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit UI Layer                 │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │Dash  │ │FHIR  │ │Trigr │ │Map   │ │Scope │ ...  │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘      │
├─────────────────────────────────────────────────────┤
│                    Core Engine                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │LLM Router│ │Agent Loop│ │  Memory  │            │
│  └──────────┘ └──────────┘ └──────────┘            │
│  ┌──────────┐ ┌──────────┐                         │
│  │  Tools   │ │Scheduler │                         │
│  └──────────┘ └──────────┘                         │
├─────────────────────────────────────────────────────┤
│                  Module Layer                        │
│  FHIR | Triggers | Mapping | Provenance | DB | ... │
├─────────────────────────────────────────────────────┤
│              Database & External Services            │
│  SQL Server | FHIR Server | Azure DevOps | SP | ... │
└─────────────────────────────────────────────────────┘
```

---

## Configuration

### Database Connections

Configured in `config/settings.py` with the following environments:

| Environment | Server | Database | Credentials |
|-------------|--------|----------|-------------|
| APP_SERVER_10G | APP_SERVER_10G | FHIR_DB | healthos / ENV_DB_PASSWORD |
| APP_SERVER_10G | APP_SERVER_10G | MUII_DB | healthos / ENV_DB_PASSWORD |
| Baseline 11x | APP_SERVER_11X | MUII_DB | Configurable |

### Key URLs

- **SharePoint**: `https://example.sharepoint.com/sites/ApplicationImprovementsTeam/`
- **Azure DevOps**: `https://devops.example.com/HealthOS10g/11g`

### File Paths

The suite uses the following directory structure for data files:

```
data/                    — Reference data (FHIR resources, scopes, SNOMED codes, USCDI mappings)
output/                  — Generated reports, converted files, analysis results
logs/                    — Application and module execution logs
```

---

## Module Details

### FHIR Tools (`modules/fhir_tools.py`)
- Build and validate FHIR R4 resources (Patient, Encounter, Observation, etc.)
- Execute CRUD operations against configurable FHIR servers
- Search with parameter validation and result filtering
- Bundle processing for batch operations
- Profile-based validation

### Trigger Tester (`modules/trigger_tester.py`)
- Read SQL trigger definitions from configurable folders
- Map triggers to FHIR Resource IDs and Names
- Execute INSERT, UPDATE, DELETE test operations against target databases
- Verify FHIR_RecordQueue entries after trigger execution
- Generate HTML and plain-text test reports with pass/fail status
- Real-time progress dashboard with execution metrics

### Mapping Converter (`modules/mapping_converter.py`)
- Read old-format FHIR mapping Excel/JSON files
- Convert dot-notation paths to full FHIR hierarchy
- Handle USCDI V3 format requirements
- Generate trigger mapping sheets (Create Tables | Delete Tables | Update Columns)
- Cross-pipeline gap analysis
- Output unified workbooks per resource

### Provenance Remapper (`modules/provenance_remapper.py`)
- Query `tblauditrail` for module names and actions
- Search for stored procedures and functions related to database tables
- Read SP definitions for insert/update logic analysis
- Fill provenance resource mappings for 10g and 11x environments
- Support bulk provenance resource creation

### Scope Generator (`modules/scope_generator.py`)
- Generate SMART on FHIR v1 (e.g., `patient/Patient.read`) and v2 (e.g., `patient/Patient.rs`) format scopes
- User-friendly scope descriptions for each permission
- Sub-resource level filter scopes
- Complete scope sets for ALL FHIR R4 resources

### Gap Analyzer (`modules/gap_analyzer.py`)
- Connect to Azure DevOps projects
- Analyze work items for coverage gaps
- Cross-reference requirements with test cases
- Generate coverage matrices and gap reports

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_fhir_tools.py -v
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `pyodbc` install fails | Install Microsoft ODBC Driver for SQL Server |
| `playwright` install fails | Run `playwright install` after pip install |
| Port 8501 in use | Change port in `run.bat` or use `--server.port` |
| Database connection fails | Verify VPN/network access to database servers |
| LLM features not working | Set API key environment variables |

---

## License

Internal use only — HealthOS Inc. All rights reserved.
