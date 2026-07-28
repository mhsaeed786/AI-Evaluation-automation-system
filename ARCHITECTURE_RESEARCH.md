# OneAgent Architecture Research

## Sources Reviewed

| Repo | Language | Core Contribution | Adopted Pattern |
|------|----------|-------------------|---------------|
| OpenClaw | TypeScript | Harness, session lanes, workspace files, hooks, diagnostics | workspace, session, hooks, diagnostics, queue |
| Eigent | Python/TS | Domain-driven FastAPI, SSE playback, MCP service, Zustand | SSE stream, project grouping, file validation |
| Super-App | Python | Adapter-as-data, skill command maps, recipe runner, facade | security, recipe runner |
| Hermes | Python | SOUL persona, cron heartbeat, update stash | heartbeat/cron patterns |
| **GPT Researcher** | Python | Skill composition, 21 retrievers, GenericLLMProvider, cost callbacks, prompt family | **llm/provider.py**, **skills/**, budget cost callbacks |
| **OpenManus** | Python | Agent harness ladder (Base→ReAct→ToolCall→Manus), ToolCollection, stuck detection, tool policies | **agent/base.py**, **agent/react.py**, **agent/toolcall.py** |
| **Goose** | Rust | Provider registry trait, MCP extensions, tool inspection chain, event streaming | provider registry, tool inspection, hooks |
| **Gemini CLI** | TypeScript | Scheduler, policy engine, context masking, loop detection, SDK tools | **scheduler/**, **policy/**, **context/** |
| **Cline** | TypeScript | createTool factory, prepareTurn seam, tool policy/approval, event stream | createTool factory, event-driven UI |
| **Firecrawl** | TypeScript | Scrape engine abstraction, fallback list, Zod config, queue | **scraper/** engine registry |
| **Aider** | Python | Repo map, str_replace_editor, linting, git integration | **coding/edit_tool.py**, read/shell tools |
| **smolagents** | Python | Code agent, local Python executor, tool decorator, memory | **tools/factory.py**, code agent concept |
| **OpenHands** | Python | Sandbox sidecar, event stream, dependency injection, agent controller | event architecture, tool isolation |
| **AutoGPT** | Python/TS | Block-graph agents, Forge framework, platform marketplace | composition/planning idea |
| **CrewAI** | Python | Crew composition, role/goal/backstory, task delegation | role system |
| **MetaGPT** | Python | Role/Action/SOP, message passing, environment, memory | role/action SOP |
| **SWE-agent** | Python | Agent-Computer Interface (ACI), command parsing, history processors | ACI command interface |

## Native OneAgent Modules

```
oneagent-super-app/core/
├── llm/            # Provider registry + GenericLLM (GPT Researcher/Goose/Cline style)
├── tools/          # BaseTool, ToolCollection, factory, registry (OpenManus/smolagents/Cline)
├── agent/          # Harness ladder: BaseAgent → ReActAgent → ToolCallAgent
├── scraper/        # Engine abstraction + fallback (Firecrawl style)
├── coding/         # ReadFileTool, ShellTool, StrReplaceEditor (Aider/Anthropic style)
├── skills/         # Skill composition (GPT Researcher style)
├── context/        # Context manager + compression (Gemini CLI/Cline)
├── policy/         # Declarative per-tool policy (Gemini CLI/Goose)
├── scheduler/      # Async task scheduler (Gemini CLI/Super-App)
├── workspace/      # Structured workspace files (OpenClaw)
├── session/        # JSONL session persistence (OpenClaw)
├── security/       # Command/URL/file validation (Super-App/Goose)
├── recipe/         # Multi-step recipe runner (Super-App)
├── harness/        # Pluggable model harnesses (OpenClaw)
├── subagent/       # Background sub-agents (OpenManus/Goose)
├── hooks/          # Lifecycle hooks (OpenClaw/Gemini CLI)
├── diagnostics/    # Flags + timeline + liveness (OpenClaw)
├── capabilities/   # Capability registry (OpenClaw)
└── queue/          # Steering/followup queues (OpenClaw)
```

## Key Adopted Patterns

1. **Agent Harness Ladder**: thin orchestrator layers (BaseAgent, ReActAgent, ToolCallAgent) lets specialists like CodeAgent inherit safely.
2. **ToolCollection + BaseTool**: declarative tools with `to_param()`, runtime add, error isolation.
3. **Provider Registry**: `provider:model` string resolution + lazy client creation.
4. **Skill Composition**: research/coding/browser skills are pluggable and receive a SkillContext.
5. **Scraper Engine Registry**: fetch + playwright engines with feature flags and fallback.
6. **Policy Engine**: per-tool ALLOW/DENY/ASK_USER decisions, wildcard defaults.
7. **Event Stream**: AgentEvent union drives UI and can be serialized.
8. **Cost Callbacks**: threaded through LLM calls for observability.
9. **Stuck Detection**: duplicate assistant messages trigger recovery prompt.
10. **Context Compression**: drop oldest low-priority messages under token budget.

## Frontend Views

- Agent Architecture (existing)
- Skill Runner
- Web Scraper
- Coding Agent Harness

All wired into Sidebar and App.tsx.
