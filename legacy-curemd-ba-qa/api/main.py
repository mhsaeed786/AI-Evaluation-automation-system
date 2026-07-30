"""
OneAgent API — FastAPI application with auto-discovered module routes.

One app, mounts each module as a router. Run with:
    uvicorn api.main:app --reload
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup/shutdown lifecycle using the modern lifespan pattern."""
    # --- Startup ---
    try:
        from core.data.models import get_core_db
        from modules import load_all_modules

        db = get_core_db()
        for mod_info in load_all_modules():
            if "error" not in mod_info:
                db.register_module(mod_info["name"], mod_info.get("description", ""), mod_info)
        logger.info("OneAgent API started — all modules loaded")
    except Exception as exc:
        logger.warning(f"Module auto-load skipped: {exc}")
    yield
    # --- Shutdown ---
    logger.info("OneAgent API shutting down")


# Restrict CORS to localhost in production; allow all only in dev mode.
_allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000").split(",")

app = FastAPI(
    title="OneAgent",
    description="Unified Personal Super-App — Agentic platform for healthcare IT, research, and productivity",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Core Endpoints ──────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "OneAgent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}


# ── Module Discovery ────────────────────────────────────────────────

@app.get("/modules")
async def list_modules():
    from core.data.models import get_core_db
    db = get_core_db()
    return {"modules": db.list_modules()}


@app.get("/modules/{module_name}")
async def get_module(module_name: str):
    from core.data.models import get_core_db
    db = get_core_db()
    mod = db.get_module(module_name)
    if not mod:
        raise HTTPException(404, f"Module '{module_name}' not found")
    return mod


# ── LLM Router ──────────────────────────────────────────────────────

@app.get("/llm/providers")
async def list_providers():
    from core.llm.router import get_router
    router = get_router()
    return {"providers": router.list_available()}


@app.get("/llm/budget")
async def budget_summary():
    from core.llm.router import get_router
    router = get_router()
    return {"daily_spend": router.get_daily_spend(), "cache_stats": router.get_cache_stats()}


@app.post("/llm/complete")
async def llm_complete(request: Request):
    body = await request.json()
    from core.llm.router import get_router
    router = get_router()
    response = await router.complete(
        messages=body.get("messages", []),
        task_class=body.get("task_class"),
        module=body.get("module"),
        provider_override=body.get("provider"),
        model_override=body.get("model"),
        temperature=body.get("temperature", 0.7),
        max_tokens=body.get("max_tokens", 4096),
    )
    return {
        "content": response.content,
        "provider": response.provider,
        "model": response.model,
        "cost_usd": response.cost_usd,
        "tokens": {"prompt": response.prompt_tokens, "completion": response.completion_tokens},
    }


# ── Agent Runner ────────────────────────────────────────────────────

@app.post("/agent/run")
async def run_agent(request: Request):
    body = await request.json()
    from core.agents.loop import AgentLoop, AgentConfig

    config = AgentConfig(
        name=body.get("agent", "default"),
        task_class=body.get("task_class", "reason"),
        module=body.get("module", ""),
        system_prompt=body.get("system_prompt", ""),
        max_iterations=body.get("max_iterations", 10),
        temperature=body.get("temperature", 0.7),
    )
    agent = AgentLoop(config=config)
    result = await agent.run(
        task=body.get("task", ""),
        context=body.get("context"),
    )
    return {
        "success": result.success,
        "output": result.output,
        "iterations": result.iterations,
        "cost_usd": result.cost_usd,
        "tool_calls": result.tool_calls,
    }


# ── Skills ──────────────────────────────────────────────────────────

@app.get("/skills")
async def list_skills(category: str = None):
    from core.skills.registry import get_skill_registry
    registry = get_skill_registry()
    return {"skills": [{"name": s.name, "description": s.description, "category": s.category} for s in registry.list_skills(category)]}


# ── MCP Servers ─────────────────────────────────────────────────────

@app.get("/mcp/servers")
async def list_mcp_servers():
    from core.mcp.client import get_mcp_host
    host = get_mcp_host()
    return {"servers": host.list_servers()}


# ── Scheduler ───────────────────────────────────────────────────────

@app.get("/scheduler/jobs")
async def list_jobs():
    from core.scheduler.scheduler import get_scheduler
    scheduler = get_scheduler()
    return {"jobs": [{"id": j.id, "name": j.name, "trigger": j.trigger.value, "enabled": j.enabled} for j in scheduler.list_jobs()]}


@app.post("/scheduler/fire-event")
async def fire_event(request: Request):
    body = await request.json()
    from core.scheduler.scheduler import get_scheduler
    scheduler = get_scheduler()
    await scheduler.fire_event(body.get("event"), body.get("payload"))
    return {"status": "fired", "event": body.get("event")}


# ── Meta (Self-Extension) ───────────────────────────────────────────

@app.get("/meta/modules")
async def list_authored_modules(status: str = None):
    from core.meta.registry import get_module_registry
    registry = get_module_registry()
    return {"modules": [{"name": m.name, "status": m.status, "tests_passed": m.tests_passed} for m in registry.list_modules(status)]}


@app.post("/meta/generate")
async def generate_module(request: Request):
    body = await request.json()
    from core.meta.module_author import ModuleAuthor
    author = ModuleAuthor()
    result = await author.generate(
        requirement=body.get("requirement", ""),
        module_name=body.get("name"),
        model=body.get("model", "anthropic"),
    )
    return {
        "success": result.success,
        "module_name": result.module_name,
        "test_passed": result.test_passed,
        "path": result.module_path,
    }
