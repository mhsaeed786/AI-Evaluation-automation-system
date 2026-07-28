# 🧠 OneAgent — AI Evaluation & Automation System

> An open-source **generalist AI agent** that learns automatically from your data — emails, Teams, Slack, local files, Jira, Azure DevOps — and then **creates specialist extensions to itself called "Limbs."** Built as an alternative to Manus, Goose, Hermes, and OpenClaw — but with a twist: it **evolves** into a set of personal specialists by studying your work.

<div align="center">

**Base generalist** → ingests your data → **specialist limbs** → automates your life

</div>

---

## 📦 Repository Structure

```
AI-Evaluation-automation-system/
│
├── oneagent-super-app/          ← 🚀 NEW: Google AI Studio React app (TypeScript)
│   ├── src/                     # React 19 frontend — dashboard, limbs, specialist evolution
│   ├── core/meta/               # Python meta self-authoring engine
│   ├── server.ts                # Express + Gemini API backend
│   ├── package.json
│   └── README.md
│
└── legacy-curemd-ba-qa/         ← 📂 OLD: Python CureMD BA/QA Automation Suite
    ├── api/                     # FastAPI server
    ├── core/                    # Agent loop, LLM router, meta, RAG, skills
    ├── modules/                 # FHIR tools
    ├── goose-extensions/        # Goose recipes/agents/connectors
    ├── cherry-extensions/       # Cherry Studio extensions
    ├── openclaw-extensions/     # OpenClaw agents/skills
    ├── hermes-extensions/       # Hermes workflow tasks
    ├── tests/
    └── README.md
```

---

## 🎯 What is OneAgent?

OneAgent ships as an **open-source generalist agent app** with strong base capabilities:

| Base Capability | Status |
|---|---|
| 🌐 Web Fetch | ✅ Firecrawl-style scraping API |
| 🖥️ Browser Use | ✅ Playwright headless agent |
| 🔎 Web Search | ✅ Research + SaaS opportunity finder |
| 💻 Code Execution | ✅ Sandboxed meta module runner |
| 🛠️ Coding | ✅ CLI controller, repo scaffolder |
| 📁 File Ops | ✅ Local file organizer & storage guardian |

### The "Limbs" Concept

The key innovation: OneAgent reads your data (Outlook emails, Teams messages, Slack messages, local files, Jira tickets, Azure DevOps pipelines, imported AI session logs) and automatically **creates extensions to itself called "Limbs."** Each limb is a specialist agent adapted to your specific work:

| Limb | Domain | Tools |
|---|---|---|
| 🏥 **FHIR BA/QA Suite** | Healthcare specs & compliance | 14 tools — inconsistency queries, HAPI explorer, cost analysis |
| 📊 **LEAP Analytics** | Telemetry & real-world testing | 9 tools — RWT, UDS compliance, scaling diagnostics |
| 🔬 **Deep Research** | Market intelligence | 8 tools — web search, scraping, SaaS gap finder |
| 📨 **WorkOps & DataSync** | Workflow automation | 11 tools — Outlook triage, Teams, SharePoint |
| ✍️ **Content & SEO** | Publishing | 6 tools — blog, SEO, social posts |
| 📂 **Files & Storage** | Data management | 7 tools — organizer, dedup, metadata |
| 🧑‍💻 **CLI & Code** | Developer tools | 10 tools — scaffolder, diff, test harness |

### How Limbs Are Born (Specialist Evolution Engine)

1. **Ingest** — OneAgent imports past data from all your sources (emails, Slack, Teams, DevOps, local files, and even sessions from other AI tools like Gemini CLI, Goose, Cursor, Claude Desktop)
2. **Index** — Everything goes into a local SQLite knowledge base with FTS5 + vector embeddings
3. **Synthesize** — Neurosymbolic rules are derived from patterns in your data (neural LLM pattern recognition + symbolic logic constraints)
4. **Self-Author** — The meta engine generates new Python modules from natural language descriptions, runs them in an isolated sandbox, tests them, and (after approval) promotes them to first-class limbs

---

## 🏗️ Project History

### Phase 1: CureMD BA/QA Automation Suite (Legacy)

The original project — a Python-based automation platform for CureMD's Business Analysis and QA workflows. It had:

- **Multi-LLM Router** — Routes to cheapest available model per task class (classify, reason, code, etc.)
- **Agentic Loop** — Plan → Execute Tool → Observe → Repeat
- **FHIR Analysis** — HAPI FHIR server, CureMD FHIR server, terminology servers
- **Database Automation** — 4 SQL Server databases for BA/QA validation
- **Self-Extension (Meta)** — Could generate new Python modules from natural language
- **Skill Packs** — Pre-built for FHIR analysis, gap analysis, content creation
- **MCP Integration** — Model Context Protocol server host

**Why it was rebuilt:** The legacy suite was functional but fragmented — separate extension folders for Goose, Cherry Studio, OpenClaw, and Hermes. The architecture was solid but the UX was a CLI/Python web UI that didn't clearly show the "generalist → specialist" vision. It was "shit" in the words of its creator — too many disconnected parts, no unified frontend, no clear story for how the agent learns and evolves.

### Phase 2: OneAgent Super-App (New — built with Google AI Studio)

Rebuilt from scratch using **Google AI Studio** for the first time. The new version:

- **Unified React/TypeScript frontend** — Dark dashboard with sidebar navigation, 18+ views
- **Express + Gemini API backend** — `server.ts` with live `@google/genai` integration
- **Specialist Evolution Engine** — Three sub-tabs: Local SQLite Knowledge Base (RAG), Cross-Agent Session Importer, and Neurosymbolic Rules
- **Meta Self-Authoring** — Visual UI for generating, testing, approving/rejecting new modules
- **LLM Gateway** — Multi-model router with task rankings, budget tracking, cache entries
- **Agent Runner** — Step-by-step agent loop visualization (plan → tool_call → observe → result)
- **Integrations Hub** — Connectors for Goose, Cherry, OpenClaw, Hermes via MCP
- **Scheduler** — Cron jobs for recurring specialist tasks
- **All 7 Limbs** — FHIR, LEAP, Research, WorkOps, Content, Files, Coding — each with rich UIs

---

## 🚀 Run Locally

### OneAgent Super-App (New)

```bash
cd oneagent-super-app

# Install dependencies
npm install

# Set your Gemini API key
# Create .env.local with:
#   GEMINI_API_KEY=your_key_here

# Run the dev server
npm run dev
# → http://localhost:3000
```

**Prerequisites:** Node.js 18+, Python 3.10+ (for the meta self-authoring engine)

### Legacy CureMD Suite (Old)

```bash
cd legacy-curemd-ba-qa

# Python setup
pip install -r requirements.txt

# Run CLI
python cli.py ask "Validate Patient FHIR resource"

# Run API server
python -m api.main

# Run standalone local UI
cd standalone-local && python app.py
```

**Prerequisites:** Python 3.10+, SQL Server ODBC Driver 17, Playwright (`playwright install chromium`)

---

## 🔑 Environment Variables

### OneAgent Super-App

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | `MY_GEMINI_API_KEY` |
| `APP_URL` | Hosted app URL (for OAuth callbacks) | `MY_APP_URL` |

### Legacy CureMD Suite

| Variable | Description |
|---|---|
| `DB_PASS_RELEASE01` | SQL Server password (Release01) |
| `DB_PASS_BASELINE11X` | SQL Server password (Baseline11x) |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GEMINI_API_KEY` | Gemini API key |

---

## 🧩 Tech Stack

### New Super-App
- **Frontend:** React 19, TypeScript, Tailwind CSS v4, Lucide icons, Motion
- **Backend:** Express, Vite middleware, `@google/genai` (Gemini API)
- **Meta Engine:** Python 3.10+ (sandboxed module generation)
- **Build:** Vite + esbuild

### Legacy Suite
- **Language:** Python 3.10+
- **Framework:** FastAPI
- **LLM:** Multi-provider router (OpenAI, Anthropic, Gemini, DeepSeek, Ollama, Groq, Mistral, Cohere)
- **Database:** SQL Server (ODBC 17), SQLite
- **Browser:** Playwright

---

## 📄 License

This project is open-source. See individual project folders for details.

---

## 👤 Author

**mhsaeed786** — Built with Google AI Studio (first time) after the legacy CureMD BA/QA suite proved too fragmented. The goal: one agent that learns your work and evolves into your personal specialist team.

---

<div align="center">

**OneAgent** — *Generalist at birth. Specialist by learning.*

</div>