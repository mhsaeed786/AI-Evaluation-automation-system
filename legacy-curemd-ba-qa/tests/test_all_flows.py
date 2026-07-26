"""
Comprehensive test suite for OneAgent — tests every flow.
Uses ZAI (Anthropic-compatible) API from Claude Code configs.

Run from project root: python tests/test_all_flows.py
"""

import sys
import os
import asyncio
import time
import traceback
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env BEFORE any other imports
from core.config import load_env
load_env()

# Force reload of settings to pick up env vars
import importlib
if "config.settings" in sys.modules:
    importlib.reload(sys.modules["config.settings"])

passed = 0
failed = 0
errors = []


def test(name, func, *args, **kwargs):
    """Run a test and report result."""
    global passed, failed
    try:
        if asyncio.iscoroutinefunction(func):
            result = asyncio.run(func(*args, **kwargs))
        else:
            result = func(*args, **kwargs)
        passed += 1
        print(f"  PASS  {name}")
        return result
    except Exception as e:
        failed += 1
        errors.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")
        traceback.print_exc()
        return None


def main():
    global passed, failed
    print("=" * 60)
    print("OneAgent Comprehensive Test Suite")
    print("=" * 60)

    # ── 1. Core Imports ────────────────────────────────────────────
    print("\n--- 1. Core Imports ---")

    test("Import core.config", lambda: __import__("core.config", fromlist=["load_env"]))
    test("Import config.settings", lambda: __import__("config.settings", fromlist=["Settings"]))
    test("Import config.databases", lambda: __import__("config.databases", fromlist=["DatabaseManager"]))
    test("Import core.llm", lambda: __import__("core.llm", fromlist=["get_router"]))
    test("Import core.agents", lambda: __import__("core.agents", fromlist=["AgentLoop"]))
    test("Import core.skills", lambda: __import__("core.skills", fromlist=["get_skill_registry"]))
    test("Import core.mcp", lambda: __import__("core.mcp", fromlist=["get_mcp_host"]))
    test("Import core.rag", lambda: __import__("core.rag", fromlist=["get_rag_engine"]))
    test("Import core.scheduler", lambda: __import__("core.scheduler", fromlist=["get_scheduler"]))
    test("Import core.meta", lambda: __import__("core.meta", fromlist=["ModuleAuthor"]))
    test("Import core.data", lambda: __import__("core.data", fromlist=["get_core_db"]))
    test("Import core.auth", lambda: __import__("core.auth", fromlist=["get_auth"]))
    test("Import core.profile", lambda: __import__("core.profile", fromlist=["get_profile"]))

    # ── 2. Settings & Config ───────────────────────────────────────
    print("\n--- 2. Settings & Config ---")

    def test_settings():
        from config.settings import get_settings
        s = get_settings()
        assert len(s.llm_providers) >= 8, f"Expected 8+ providers, got {len(s.llm_providers)}"
        assert "anthropic" in s.llm_providers
        assert "release01_fhir" in s.databases
        return s

    settings = test("Settings loads with 8+ providers and DBs", test_settings)

    def test_env_loaded():
        assert os.getenv("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY not loaded from .env"
        assert os.getenv("ANTHROPIC_BASE_URL"), "ANTHROPIC_BASE_URL not loaded from .env"
        return os.getenv("ANTHROPIC_API_KEY")[:10] + "..."

    test(".env loaded with ANTHROPIC_API_KEY and BASE_URL", test_env_loaded)

    # ── 3. Database Manager ────────────────────────────────────────
    print("\n--- 3. Database Manager ---")

    def test_db_manager():
        from config.databases import get_db_manager
        return get_db_manager()

    db = test("DatabaseManager creates", test_db_manager)

    def test_db_query_log():
        assert db is not None
        return db.get_query_log()

    test("DatabaseManager.get_query_log works", test_db_query_log)

    # ── 4. Core DB (SQLite) ────────────────────────────────────────
    print("\n--- 4. Core DB ---")

    def test_core_db():
        from core.data.models import get_core_db
        cdb = get_core_db()
        cdb.register_module("test_mod", "A test module", {"tools": ["test_tool"]})
        mod = cdb.get_module("test_mod")
        assert mod is not None, "Module not found after registration"
        assert mod["name"] == "test_mod"
        mods = cdb.list_modules()
        assert len(mods) >= 1
        cdb.set_preference("theme", "dark")
        assert cdb.get_preference("theme") == "dark"
        return cdb

    test("CoreDB register/get/list modules + preferences", test_core_db)

    # ── 5. Auth ─────────────────────────────────────────────────────
    print("\n--- 5. Auth ---")

    def test_auth():
        from core.auth.auth import get_auth
        auth = get_auth()
        api_key = auth.create_user("test_user", role="admin")
        assert api_key.startswith("oa_"), f"Expected oa_ prefix, got {api_key[:5]}"
        user = auth.authenticate(api_key)
        assert user is not None, "Authentication failed with valid key"
        assert user.username == "test_user"
        assert user.role == "admin"
        users = auth.list_users()
        assert len(users) >= 1
        return api_key

    test("Auth create user → authenticate → list", test_auth)

    # ── 6. Profile ──────────────────────────────────────────────────
    print("\n--- 6. Profile ---")

    def test_profile():
        from core.profile.profile import get_profile
        p = get_profile()
        p.set("name", "Hassan")
        p.set("role", "BA/QA")
        assert p.get("name") == "Hassan"
        assert p.get("role") == "BA/QA"
        p.record_task_pattern("FHIR resource validation", "fhir")
        p.record_task_pattern("FHIR resource validation", "fhir")
        p.record_task_pattern("FHIR resource validation", "fhir")
        patterns = p.get_frequent_patterns(min_count=2)
        assert len(patterns) >= 1, f"Expected patterns, got {patterns}"
        return p

    test("Profile set/get + task pattern tracking", test_profile)

    # ── 7. LLM Cache ───────────────────────────────────────────────
    print("\n--- 7. LLM Cache ---")

    def test_cache():
        from core.llm.cache import LLMCache
        cache = LLMCache()
        msgs = [{"role": "user", "content": "test"}]
        cache.put(msgs, "test-model", {"content": "cached response"}, "test-provider", 10, 5)
        hit = cache.get(msgs, "test-model")
        assert hit is not None, "Cache miss on just-stored entry"
        assert hit["content"] == "cached response"
        stats = cache.stats()
        assert stats["entries"] >= 1
        cache.close()
        return stats

    test("Cache put → get → stats", test_cache)

    # ── 8. Budget Tracker ──────────────────────────────────────────
    print("\n--- 8. Budget Tracker ---")

    def test_budget():
        from core.llm.budget import BudgetTracker, BudgetConfig
        cfg = BudgetConfig(daily_limit_usd=10.0, per_task_limits={"code": 1.0})
        bt = BudgetTracker(config=cfg)
        bt.log_call("openai", "gpt-4o", 100, 50, 0.005, task_class="code", module="test")
        bt.check_budget(task_class="code")
        summary = bt.get_daily_summary()
        assert summary["total_usd"] >= 0.005
        mod_summary = bt.get_module_summary()
        assert "test" in mod_summary
        return summary

    test("Budget log → check → summary", test_budget)

    # ── 9. LLM Router (with ZAI) ───────────────────────────────────
    print("\n--- 9. LLM Router (ZAI API) ---")

    def test_router_init():
        from core.llm.router import LLMRouter
        router = LLMRouter()
        providers = router.list_available()
        assert len(providers) >= 1, f"No providers available: {providers}"
        return router

    router = test("Router initializes with providers", test_router_init)

    async def test_llm_call():
        from core.llm.router import get_router
        r = get_router()
        response = await r.complete(
            messages=[{"role": "user", "content": "Say exactly: ONEAGENT_TEST_OK"}],
            task_class="classify",
            module="test",
            use_cache=False,
            temperature=0,
            max_tokens=20,
        )
        assert response.content, f"Empty response from LLM"
        assert response.cost_usd >= 0
        return response

    resp = test("LLM call via ZAI (Anthropic-compatible)", test_llm_call)

    async def test_llm_cache_hit():
        from core.llm.router import get_router
        r = get_router()
        msgs = [{"role": "user", "content": f"CACHE_TEST_{time.time()}"}]
        # First call — stores in cache
        r1 = await r.complete(messages=msgs, task_class="classify", module="test", use_cache=True, max_tokens=10)
        # Second call — should hit cache
        r2 = await r.complete(messages=msgs, task_class="classify", module="test", use_cache=True, max_tokens=10)
        assert r2.cost_usd == 0.0, f"Cache hit should cost $0 but cost ${r2.cost_usd}"
        return r2

    test("LLM cache hit (second call costs $0)", test_llm_cache_hit)

    # ── 10. Tool Registry ──────────────────────────────────────────
    print("\n--- 10. Tool Registry ---")

    def test_tool_registry():
        from core.agents.tools import get_registry, tool

        @tool(name="test_calc", description="Test calculator", module="test")
        def test_calc(a: int, b: int) -> int:
            return a + b

        reg = get_registry()
        t = reg.get("test_calc")
        assert t is not None, "Tool not found after registration"
        assert t.name == "test_calc"
        schema = t.to_schema()
        assert schema["type"] == "function"
        assert "test_calc" in schema["function"]["name"]
        return schema

    test("Tool register → get → schema", test_tool_registry)

    async def test_tool_call():
        from core.agents.tools import get_registry
        reg = get_registry()
        result = await reg.call("test_calc", a=3, b=4)
        assert result == 7, f"Expected 7, got {result}"
        return result

    test("Tool call test_calc(3,4) = 7", test_tool_call)

    # ── 11. Memory ─────────────────────────────────────────────────
    print("\n--- 11. Memory ---")

    def test_scratchpad():
        from core.agents.memory import Scratchpad
        sp = Scratchpad()
        sp.add_thought("Testing scratchpad")
        sp.add_observation("Saw something")
        sp.add_action("test_tool", "result")
        msgs = sp.to_messages()
        assert len(msgs) == 3
        sp.clear()
        assert len(sp.to_messages()) == 0
        return msgs

    test("Scratchpad add → to_messages → clear", test_scratchpad)

    def test_long_term_memory():
        from core.agents.memory import get_long_term_memory
        ltm = get_long_term_memory()
        mid = ltm.store("FHIR Patient resource has name field", category="fhir", importance=0.8)
        results = ltm.recall(query="Patient", category="fhir")
        assert len(results) >= 1, f"Expected recall results, got {results}"
        ltm.access(mid)
        return results

    test("Long-term memory store → recall → access", test_long_term_memory)

    # ── 12. Skills ─────────────────────────────────────────────────
    print("\n--- 12. Skills ---")

    def test_skills():
        from core.skills.registry import get_skill_registry
        reg = get_skill_registry()
        skills = reg.list_skills()
        assert len(skills) >= 7, f"Expected 7+ skills, got {len(skills)}"
        fhir_skill = reg.get("fhir-analysis")
        assert fhir_skill is not None, "fhir-analysis skill not found"
        assert "FHIR R4" in fhir_skill.prompt
        cats = reg.list_categories()
        assert len(cats) >= 1
        return [s.name for s in skills]

    test("Skills load 7+ packs + fhir-analysis has content", test_skills)

    # ── 13. MCP Host ───────────────────────────────────────────────
    print("\n--- 13. MCP Host ---")

    def test_mcp():
        from core.mcp.client import get_mcp_host
        host = get_mcp_host()
        servers = host.list_servers()
        assert len(servers) >= 5, f"Expected 5+ MCP servers from goose-extensions, got {len(servers)}"
        names = [s["name"] for s in servers]
        assert "llm-router" in names, f"llm-router not in {names}"
        assert "curemd-database" in names
        return names

    test("MCP loads 5+ servers from goose-extensions", test_mcp)

    # ── 14. Scheduler ──────────────────────────────────────────────
    print("\n--- 14. Scheduler ---")

    def test_scheduler():
        from core.scheduler.scheduler import get_scheduler, ScheduledJob, TriggerType
        sched = get_scheduler()
        job = ScheduledJob(
            id="test_job_1",
            name="Test Job",
            trigger=TriggerType.INTERVAL,
            schedule="3600",
            agent_config={"name": "test", "task_class": "reason"},
            task_prompt="Test prompt",
            module="test",
        )
        sched.add_job(job)
        jobs = sched.list_jobs()
        assert len(jobs) >= 1
        found = [j for j in jobs if j.id == "test_job_1"]
        assert len(found) == 1
        sched.remove_job("test_job_1")
        return jobs

    test("Scheduler add → list → remove job", test_scheduler)

    # ── 15. Module Registry (Meta) ─────────────────────────────────
    print("\n--- 15. Meta Module Registry ---")

    def test_meta_registry():
        from core.meta.registry import get_module_registry, AuthoredModule
        reg = get_module_registry()
        mod = AuthoredModule(
            name="test_auto_mod",
            description="Auto-generated test module",
            path="/tmp/test.py",
            status="testing",
            tests_passed=True,
            provenance={"prompt": "test", "model": "test-model"},
        )
        reg.register(mod)
        retrieved = reg.get("test_auto_mod")
        assert retrieved is not None
        assert retrieved.status == "testing"
        pending = reg.get_pending_review()
        assert len(pending) >= 1
        reg.update_status("test_auto_mod", "approved")
        assert reg.get("test_auto_mod").status == "approved"
        return retrieved

    test("Meta registry register → pending → approve", test_meta_registry)

    # ── 16. Module Loading ─────────────────────────────────────────
    print("\n--- 16. Module Loading ---")

    def test_modules():
        from modules import load_all_modules, discover_modules
        discovered = discover_modules()
        assert len(discovered) >= 7, f"Expected 7+ discovered modules, got {discovered}"
        loaded = load_all_modules()
        assert len(loaded) >= 7, f"Expected 7+ loaded modules, got {len(loaded)}"
        names = [m["name"] for m in loaded if "error" not in m]
        assert "fhir" in names, f"fhir not in {names}"
        return names

    test("Modules discover 7+ and load successfully", test_modules)

    # ── 17. FHIR Module Tools ──────────────────────────────────────
    print("\n--- 17. FHIR Module Tools ---")

    def test_fhir_scopes():
        from modules.fhir.manifest import generate_smart_scopes
        result = generate_smart_scopes(resources="Patient,Encounter", include_v2=True)
        assert result["v1_count"] > 0, "No V1 scopes generated"
        assert result["v2_count"] > 0, "No V2 scopes generated"
        return result

    test("FHIR scope generation v1+v2", test_fhir_scopes)

    def test_fhir_register():
        from modules.fhir.manifest import register
        info = register()
        assert info["name"] == "fhir"
        assert len(info["tools"]) == 11
        assert len(info["routes"]) == 8
        return info

    test("FHIR module register() returns 11 tools + 8 routes", test_fhir_register)

    # ── 18. LEAP Module ────────────────────────────────────────────
    print("\n--- 18. LEAP Module ---")

    def test_leap_register():
        from modules.leap.manifest import register
        info = register()
        assert info["name"] == "leap"
        assert len(info["tools"]) == 4
        return info

    test("LEAP module register()", test_leap_register)

    # ── 19. Research Module ────────────────────────────────────────
    print("\n--- 19. Research Module ---")

    def test_research_register():
        from modules.research.manifest import register
        info = register()
        assert info["name"] == "research"
        assert len(info["tools"]) == 5
        return info

    test("Research module register()", test_research_register)

    # ── 20. All Other Module Registrations ─────────────────────────
    print("\n--- 20. All Module Registrations ---")

    for mod_name in ["work_ops", "files", "coding", "content"]:
        def test_mod_reg(mod_name=mod_name):
            mod = __import__(f"modules.{mod_name}.manifest", fromlist=["register"])
            info = mod.register()
            assert info["name"] == mod_name, f"Expected {mod_name}, got {info.get('name')}"
            assert len(info.get("tools", [])) >= 1, f"{mod_name} has no tools"
            return info
        test(f"{mod_name} module register() OK", test_mod_reg)

    # ── 21. Agent Loop ─────────────────────────────────────────────
    print("\n--- 21. Agent Loop ---")

    async def test_agent_no_tools():
        from core.agents.loop import AgentLoop, AgentConfig, ApprovalMode
        config = AgentConfig(
            name="test_agent",
            task_class="classify",
            max_iterations=2,
            system_prompt="You are a test agent. Answer directly with just the answer.",
        )
        agent = AgentLoop(config=config)
        result = await agent.run("What is 2+2? Answer with just the number.")
        assert result.success, f"Agent failed: {result.error}"
        assert "4" in result.output, f"Expected 4 in output, got: {result.output}"
        return result

    test("Agent loop simple math question", test_agent_no_tools)

    # ── 22. API Endpoints ──────────────────────────────────────────
    print("\n--- 22. API Endpoints ---")

    def test_api_app():
        from api.main import app
        assert app.title == "OneAgent"
        routes = [r.path for r in app.routes]
        assert "/" in routes
        assert "/modules" in routes
        assert "/llm/providers" in routes
        assert "/agent/run" in routes
        return routes

    test("FastAPI app has expected routes", test_api_app)

    # ── 23. CLI ─────────────────────────────────────────────────────
    print("\n--- 23. CLI ---")

    def test_cli_imports():
        import cli
        assert hasattr(cli, "cmd_ask")
        assert hasattr(cli, "cmd_budget")
        assert hasattr(cli, "cmd_modules")
        assert hasattr(cli, "cmd_providers")
        assert hasattr(cli, "main")
        return True

    test("CLI imports and has expected commands", test_cli_imports)

    # ── 24. RAG Engine ─────────────────────────────────────────────
    print("\n--- 24. RAG Engine ---")

    def test_rag():
        from core.rag.engine import RAGEngine
        rag = RAGEngine()
        chunks = rag.ingest_text(
            "FHIR Patient resource requires a name element. "
            "The name element is a HumanName datatype with family and given fields. "
            "USCDI V3 requires Patient.name for compliance.",
            collection="test",
            doc_id="fhir_patient",
            metadata={"source": "test"},
        )
        assert chunks >= 1, f"Expected chunks, got {chunks}"
        results = rag.query("Patient name", collection="test", n_results=3)
        assert len(results) >= 1, f"Expected results, got {results}"
        cols = rag.list_collections()
        assert len(cols) >= 1
        return chunks

    test("RAG ingest → query → list collections", test_rag)

    # ── Results ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
