# OneAgent Local — Standalone Offline Version

Lightweight version that works offline with Ollama local models.
No cloud API keys required. All features work with local inference.

## Quick Start

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama3.1`
3. Run: `streamlit run app.py --server.port 8502`

## Differences from Full OneAgent
- Uses only Ollama (no cloud providers)
- No budget limits (free inference)
- No caching (local is fast enough)
- Simplified UI with core modules only
- No Celery/Redis (in-process scheduler)

## Modules Available
- FHIR Tools (search, validate, CRUD)
- Database Operations (queries, schema, triggers)
- LEAP Analytics
- File Operations
- Coding Tools
