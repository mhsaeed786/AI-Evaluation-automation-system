# OneAgent Architecture Research: Cloned AI Agent Feature Analysis

> Research compiled from studying OpenClaw, Eigent, Super-App orchestrator, and Hermes codebases.
> Goal: Extract the best features from each and apply them as native features to OneAgent.

---

## 1. OPENCLAW — Key Features to Adopt

### 1.1 Harness Abstraction (Pluggable Agent Loop)
- **How it works:** An `AgentHarness` interface lets plugins replace the low-level executor. Core owns provider/model resolution, workspace, tool policy, channel delivery — the harness only runs the prepared attempt.
- **Selection:** Session-pinned harness id → `OPENCLAW_AGENT_RUNTIME` env → `auto` (ask registered harnesses) → PI fallback.
- **Pattern:** `api.registerCapability(...)` — each plugin registers capabilities (TextInference, WebSearch, Channel, BrowserControl).
- **Adopt:** OneAgent should have a pluggable harness interface where different model families each have their own native loop while sharing context assembly, tool policy, and delivery.

### 1.2 Session-Lane Serialization + Write Lock
- **How it works:** Runs serialized per session via queue. File-based, process-aware write lock for transcript integrity.
- **Pattern:** Non-reentrant lock with 60s acquire timeout. Prevents tool/session races.
- **Adopt:** Per-session queue + file-based lock for transcript integrity.

### 1.3 Pluggable Context Engine (4-Point Lifecycle)
- **How it works:** Four lifecycle points: Ingest → Assemble → Compact → AfterTurn. The legacy engine is pass-through; plugin engines can implement DAG summaries, vector retrieval, etc.
- **Adopt:** Let plugins own context assembly while core owns the session store.

### 1.4 Structured Workspace Files
- **Files:** `SOUL.md` (persona/tone), `AGENTS.md` (operating instructions), `USER.md` (user profile), `IDENTITY.md` (name/emoji), `TOOLS.md` (tool notes), `BOOTSTRAP.md` (one-time first-run ritual), `HEARTBEAT.md` (heartbeat checklist), `memory/YYYY-MM-DD.md` (daily logs).
- **Pattern:** Injected into system prompt on session start. Large files truncated with markers. Blank files skipped. `BOOTSTRAP.md` deleted after first-run ritual.
- **Adopt:** Separate persona, instructions, user profile, identity, and onboarding. Date-organized memory logs.

### 1.5 WebSocket Gateway with Challenge-Response
- **How it works:** Single long-lived Gateway daemon owns all messaging surfaces. Wire protocol: WebSocket, text frames, JSON. First frame must be `connect`. Pre-connect challenge with nonce + signature.
- **Features:** Protocol versioning (min/max), feature discovery in `hello-ok`, idempotency keys for side-effecting methods, event gaps not replayed (clients refresh).
- **Adopt:** Single control plane, device pairing, feature discovery, idempotency keys.

### 1.6 Sub-Agents with Push-Based Completion
- **How it works:** Sub-agents get own session, run on dedicated queue lane (max 8 concurrent). Context modes: `isolated` (fresh transcript) or `fork` (branch parent). Nesting up to depth 5.
- **Completion:** Push-based announce event (don't poll). Cascade stop (stopping parent stops children).
- **Tool policy:** Depth-1 orchestrators get session tools; depth-2 leaf workers don't.
- **Adopt:** Non-blocking spawn, isolated/fork context, nesting depth with tool policy.

### 1.7 Dual Hook System
- **Internal hooks:** Event-driven `HOOK.md` scripts for commands and lifecycle (`/new`, `/reset`, `/stop`, `agent:bootstrap`, `gateway:startup`).
- **Plugin hooks:** In-process extension points via `api.on(name, handler, opts)`. Key hooks: `before_model_resolve`, `before_prompt_build`, `before_tool_call` (block/rewrite/require approval), `tool_result_persist`.
- **Semantics:** Priority-ordered. `{ block: true }` is terminal. `{ block: false }` is no-op. Same for `before_install` and `message_sending`.
- **Adopt:** Operator scripts separate from plugin hooks. Pre-model-resolution hook, tool-result persist transform, approval-gating.

### 1.8 Diagnostic Flags + Timeline JSONL
- **How it works:** Subsystem-specific diagnostic flags (case-insensitive, wildcards). `timeline` flag writes structured startup/runtime timing events as JSONL.
- **Session liveness:** `long_running` (active, slow), `stalled` (no progress), `stuck` (stale bookkeeping).
- **Adopt:** Targeted per-subsystem logging. Structured timing artifacts. Session liveness classification.

### 1.9 Isolated Browser Profile + SSRF Policy
- **How it works:** Dedicated Chrome/Chromium profile (`openclaw`) isolated from user's personal browser. SSRF policy with `dangerouslyAllowPrivateNetwork`, `hostnameAllowlist`.
- **Pattern:** Snapshot → act → resnapshot → recover stale refs loop. Tab cleanup with idle minutes + max tabs per session. Optional Docker sandbox.
- **Adopt:** Never touch user's browser. Block private networks. Teach the recovery loop.

### 1.10 Queue / Steering Modes
- **`steer`:** Inbound messages injected into current run *after* tool calls, before next LLM call.
- **`followup`/`collect`:** Messages held until current turn ends, then new turn with queued payloads.
- **Adopt:** Let users inject messages mid-run. Different strategies per channel.

---

## 2. EIGENT — Key Features to Adopt

### 2.1 Domain-Driven FastAPI Architecture
- **How it works:** `app/domains/{chat,mcp,config,model_provider,oauth,trigger,user}` — each domain has `api/` (controllers), `schema/` (Pydantic models), `service/` (business logic).
- **Pattern:** `auto_include_routers()` auto-discovers and mounts domain routers. Static methods on service classes, self-managed sessions.
- **Adopt:** Domain-driven module organization with auto-discovery.

### 2.2 SSE Step Playback
- **How it works:** `GET /chat/steps/playback/{task_id}` returns `StreamingResponse` with `text/event-stream`. Each step emitted as `data: {json}\n\n`. Configurable `delay_time` for replay speed.
- **Adopt:** SSE streaming for agent step replay. Let users replay task execution with adjustable speed.

### 2.3 MCP User Service (Install/Uninstall/Import)
- **How it works:** MCP store with `install` (dedup check, parse install_command), `import` (local: validate mcpServers JSON; remote: validate URL), `update`, `uninstall`.
- **Pattern:** `McpUser` model tracks per-user installed MCPs with command/args/env/server_url. `McpType.Local` vs `McpType.Remote`.
- **Adopt:** MCP marketplace with per-user installation tracking.

### 2.4 Chat Steps as First-Class Objects
- **How it works:** `ChatStep` model stores each agent step (step type, data blob, timestamp). CRUD endpoints for steps. Steps ordered by timestamp + id.
- **Adopt:** Persist every agent step as a queryable, replayable record.

### 2.5 Project Grouping with Trigger Counts
- **How it works:** Chat histories grouped by `project_id`. Each project has `total_tokens`, `task_count`, `latest_task_date`, `total_completed_tasks`, `total_ongoing_tasks`, `total_triggers`.
- **Adopt:** Group tasks into projects with aggregate metrics.

### 2.6 File Validation + Upload
- **How it works:** `ALLOWED_EXTENSIONS` set + `MAX_FILE_SIZE` (10MB). Validates before S3 upload. `ChatFile` model tracks per-task attachments.
- **Adopt:** Strict file validation before any upload/processing.

### 2.7 Zustand Store Architecture
- **How it works:** Multiple independent stores: `chatStore`, `authStore`, `projectStore`, `skillsStore`, `triggerStore`, `globalStore`, etc. Each store created with `createStore` from zustand.
- **Pattern:** `fetchEventSource` from `@microsoft/fetch-event-source` for SSE streaming. AbortController per task for connection management.
- **Adopt:** Separate stores per concern. AbortController-based SSE lifecycle.

### 2.8 Trigger System (Webhooks + Scheduling)
- **How it works:** `trigger` domain with webhook controllers. Triggers create tasks automatically. `Trigger` model links to `project_id`.
- **Adopt:** Webhook triggers that auto-create agent tasks linked to projects.

### 2.9 Electron Desktop Integration
- **How it works:** Electron + Vite + React. `vite-plugin-electron` for dev. `electron-builder` for distribution. Monaco editor, xterm terminal, xyflow graph visualizer built in.
- **Adopt:** Monaco code editor, xterm terminal, xyflow workflow visualizer.

---

## 3. SUPER-APP ORCHESTRATOR — Key Features to Adopt

### 3.1 Adapter-as-Data (JSON)
- **How it works:** Each agent defined as `adapter.json` with `id`, `name`, `capabilities[]`, `commands{}` (named shell templates with `{placeholder}` substitution).
- **Adopt:** Define external tool integrations as JSON. Adding a new tool is config-only.

### 3.2 Per-Skill Multi-Agent Command Map
- **How it works:** `commands: {claude: {run: "..."}, goose: {run: "..."}, default: {run: "..."}}` — same skill executes on whatever agent is available.
- **Adopt:** Define capability once, map to multiple executors.

### 3.3 Allowlist Command Validation
- **How it works:** `_validate_command()` rejects dangerous metacharacters (`;|&\`$(${}><&&|()`) + checks binary against `ALLOWED_COMMAND_PREFIXES`.
- **Adopt:** Allowlist of permitted binaries + metacharacter rejection before any subprocess.

### 3.4 Cross-Platform Atomic JSON I/O
- **How it works:** `os.open` + `msvcrt.locking` (Windows) / `fcntl.flock` (Linux). Atomic truncate-and-write under exclusive lock.
- **Adopt:** Cross-platform file locking for JSON state stores shared across processes.

### 3.5 Recipe = Ordered Skill Chain
- **How it works:** Recipe JSON has `steps[]` — each step specifies `skill`, `agent`, `params`. Sequential execution with `continue_on_error` per step. Param merge: `{**recipe_params, **step_params}`.
- **Adopt:** Declarative multi-step recipes as JSON. Per-step error control. Param merge with step-overrides-recipe.

### 3.6 Facade Composition
- **How it works:** `SuperApp.__init__()` wires `AgentRegistry`, `SkillsEngine`, `CronScheduler`, `RecipeRunner`. Single entry point for all operations.
- **Adopt:** Single orchestrator facade composing all subsystems.

### 3.7 Thin REST API + Dual CLI
- **How it works:** Every endpoint is a one-liner delegating to `super_app.<method>()`. CLI mirrors API exactly. No business logic in transport layer. Pydantic for validation.
- **Adopt:** CLI and API both delegate to single facade. Zero duplication.

### 3.8 Action Groups
- **How it works:** `scheduler/actions/actions.json` defines composite actions (`morning-standup`, `end-of-day-report`) each with `trigger` + `steps[]` (job IDs).
- **Adopt:** Named composite schedules referencing job IDs.

---

## 4. HERMES — Key Features

### 4.1 SOUL.md Persona System
- Large persona file (~66KB) with detailed agent behavior rules, tool usage guidelines, boundaries.
- **Adopt:** Rich persona configuration with explicit boundaries.

### 4.2 Cron Ticker with Heartbeat
- `cron/ticker_heartbeat` and `cron/ticker_last_success` files for health monitoring.
- Lock files: `.jobs.lock`, `.tick.lock` for concurrent access protection.
- **Adopt:** Heartbeat-based scheduler health monitoring.

### 4.3 Self-Update with Stash Strategy
- `non_interactive_local_changes: "stash"` — auto-stash before pull, auto-restore after.
- **Adopt:** Self-update with conflict resolution strategy.

---

## 5. ONEAGENT WEB DISCOVERY MODULE — Existing Pattern

### 5.1 BrowserDiscoveryAgent
- Playwright-based Chromium with retry logic (3 attempts), custom user agent, configurable viewport.
- Deep DOM extraction via injected JavaScript: all interactive + content elements with full metadata (xpath, css_selector, bounding_box, visibility, interactivity).
- Page link discovery with same-domain filtering + dedup (max 20).
- Screenshot capture, selector waiting.
- **Keep:** This is a solid base for browser automation. Enhance with OpenClaw's snapshot-act-resnapshot loop.

---

## SYNTHESIS: Features to Implement in OneAgent

| Priority | Feature | Source | Implementation Area |
|----------|---------|--------|---------------------|
| P0 | **Structured workspace files** (SOUL/AGENTS/USER/IDENTITY/BOOTSTRAP) | OpenClaw | `workspace/` directory |
| P0 | **Session-lane serialization + transcript persistence** | OpenClaw | `core/session/` |
| P0 | **SSE streaming for agent steps** | Eigent | `server.ts` endpoints |
| P0 | **Allowlist command validation** | Super-App | `core/security/` |
| P0 | **Recipe = ordered skill chain** with `continue_on_error` | Super-App | `core/recipe/` |
| P1 | **Harness abstraction** (pluggable agent loop) | OpenClaw | `core/harness/` |
| P1 | **Capability registration** (explicit types) | OpenClaw | `core/capabilities/` |
| P1 | **Sub-agents with push-based completion** | OpenClaw | `core/subagent/` |
| P1 | **MCP marketplace** (install/uninstall/import) | Eigent | `core/mcp/` |
| P1 | **Dual hook system** (operator + plugin hooks) | OpenClaw | `core/hooks/` |
| P1 | **Domain-driven module organization** | Eigent | `domains/` |
| P2 | **Adapter-as-data** (JSON adapters) | Super-App | `agents/` |
| P2 | **Per-skill multi-agent command map** | Super-App | `skills/` |
| P2 | **Cross-platform atomic JSON I/O** | Super-App | `core/storage/` |
| P2 | **Diagnostic flags + timeline JSONL** | OpenClaw | `core/diagnostics/` |
| P2 | **Isolated browser profile + SSRF policy** | OpenClaw | `core/browser/` |
| P2 | **Action groups** (composite schedules) | Super-App | `core/scheduler/` |
| P2 | **Steering modes** (inject mid-run) | OpenClaw | `core/queue/` |
| P2 | **Project grouping with aggregate metrics** | Eigent | `core/project/` |
| P3 | **Electron desktop** (Monaco, xterm, xyflow) | Eigent | `electron/` |
| P3 | **Heartbeat-based scheduler health** | Hermes | `core/scheduler/` |
| P3 | **WebSocket gateway** | OpenClaw | `core/gateway/` |
| P3 | **Self-update with stash strategy** | Hermes | `core/updater/` |