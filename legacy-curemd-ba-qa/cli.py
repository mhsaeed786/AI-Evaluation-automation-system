"""
OneAgent CLI — terminal access to all OneAgent features.

Usage:
    python cli.py ask "your question"
    python cli.py run-agent <module> "task"
    python cli.py budget
    python cli.py modules
    python cli.py providers
"""

import argparse
import asyncio
import json
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def cmd_ask(args):
    """Ask a question — routes through LLM router."""
    async def _run():
        from core.llm.router import get_router
        router = get_router()
        response = await router.complete(
            messages=[{"role": "user", "content": args.prompt}],
            task_class=args.task,
            module=args.module,
        )
        print(f"\n{response.content}")
        print(f"\n--- {response.provider}/{response.model} | ${response.cost_usd:.4f} ---")

    asyncio.run(_run())


def cmd_run_agent(args):
    """Run an agent for a task."""
    async def _run():
        from core.agents.loop import AgentLoop, AgentConfig
        config = AgentConfig(
            name=args.module or "cli",
            task_class=args.task,
            module=args.module or "",
            max_iterations=args.iterations,
            system_prompt=args.system or "",
        )
        agent = AgentLoop(config=config)
        result = await agent.run(args.task)
        print(f"\n{'SUCCESS' if result.success else 'FAILED'}")
        print(result.output)
        print(f"\n--- {result.iterations} iterations | ${result.cost_usd:.4f} | {len(result.tool_calls)} tool calls ---")

    asyncio.run(_run())


def cmd_budget(args):
    """Show today's budget usage."""
    from core.llm.router import get_router
    router = get_router()
    summary = router.get_daily_spend()
    print(f"\nDaily spend for {summary['date']}: ${summary['total_usd']:.4f}")
    print(f"Cached calls: {summary['cached_calls']}")
    for provider, models in summary.get("by_provider", {}).items():
        for m in models:
            print(f"  {provider}/{m['model']}: ${m['cost_usd']:.4f} ({m['calls']} calls)")


def cmd_modules(args):
    """List available modules."""
    from modules import load_all_modules
    for mod in load_all_modules():
        tools = mod.get("tools", [])
        print(f"  {mod['name']}: {mod.get('description', '')}")
        if tools:
            print(f"    tools: {', '.join(tools)}")


def cmd_providers(args):
    """List LLM providers and availability."""
    from core.llm.router import get_router
    router = get_router()
    for p in router.list_available():
        status = "AVAILABLE" if p["available"] else "UNAVAILABLE"
        print(f"  {p['provider']:12} | {p['model']:30} | ${p['cost_per_1k_input']:.4f}/1k in | {status}")


def cmd_generate(args):
    """Generate a new module from a description."""
    async def _run():
        from core.meta.module_author import ModuleAuthor
        author = ModuleAuthor()
        result = await author.generate(requirement=args.description, module_name=args.name)
        print(f"\nModule: {result.module_name}")
        print(f"Path: {result.module_path}")
        print(f"Tests passed: {result.test_passed}")
        if result.error:
            print(f"Error: {result.error}")

    asyncio.run(_run())


def main():
    parser = argparse.ArgumentParser(prog="oneagent", description="OneAgent — Unified Personal Super-App")
    sub = parser.add_subparsers(dest="command")

    # ask
    p = sub.add_parser("ask", help="Ask a question through the LLM router")
    p.add_argument("prompt", help="Your question")
    p.add_argument("--task", default="reason", help="Task class (classify, reason, code, etc.)")
    p.add_argument("--module", default="", help="Module context for budget tracking")

    # run-agent
    p = sub.add_parser("run-agent", help="Run an agent for a task")
    p.add_argument("task", help="Task description")
    p.add_argument("--module", default="", help="Module to use")
    p.add_argument("--task-class", dest="task", default="reason", help="Task class")
    p.add_argument("--iterations", type=int, default=10)
    p.add_argument("--system", default="")

    # budget
    sub.add_parser("budget", help="Show today's LLM spend")

    # modules
    sub.add_parser("modules", help="List available modules")

    # providers
    sub.add_parser("providers", help="List LLM providers")

    # generate
    p = sub.add_parser("generate", help="Generate a new module")
    p.add_argument("description", help="What the module should do")
    p.add_argument("--name", help="Module name")

    args = parser.parse_args()

    commands = {
        "ask": cmd_ask,
        "run-agent": cmd_run_agent,
        "budget": cmd_budget,
        "modules": cmd_modules,
        "providers": cmd_providers,
        "generate": cmd_generate,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
