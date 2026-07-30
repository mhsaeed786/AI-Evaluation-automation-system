"""
Module Author — the meta-agent that generates new modules.

When a recurring task can't be solved by composing existing skills/tools,
this agent writes a new Python module under modules/, generates tests,
runs them in the sandbox, and registers the module for review.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..llm.router import get_router
from ..agents.loop import AgentLoop, AgentConfig
from .sandbox import Sandbox, get_sandbox
from .registry import AuthoredModule, ModuleRegistry, get_module_registry

logger = logging.getLogger(__name__)

MODULES_DIR = Path(__file__).resolve().parent.parent.parent / "modules"

GENERATE_PROMPT = """You are a module code generator for OneAgent.

## Task
Generate a complete Python module for the following requirement:

{requirement}

## Rules
1. The module must be self-contained in a single file
2. It must use the core/ APIs: core.llm for AI calls, core.agents for agent loop, config.databases for DB
3. Import paths should be absolute from the project root
4. Include a `register()` function that returns a dict with:
   - "name": module name
   - "description": what it does
   - "tools": list of tool names it provides
   - "routes": list of API route dicts (method, path, handler)
5. Include docstrings on all public functions
6. Handle errors gracefully
7. Output ONLY the Python code, no markdown fences

## Module code:"""

TEST_GENERATE_PROMPT = """You are a test generator for OneAgent modules.

## Module Code
```python
{module_code}
```

## Task
Generate pytest tests for this module.

## Rules
1. Use pytest fixtures and parametrize where appropriate
2. Mock external dependencies (DB, LLM, network)
3. Test happy path AND error cases
4. Import the module as: from module_under_test import *
5. Output ONLY the Python test code, no markdown fences

## Test code:"""


@dataclass
class AuthorResult:
    success: bool
    module_name: str
    module_path: Optional[str] = None
    test_passed: bool = False
    test_output: str = ""
    error: Optional[str] = None
    module_code: str = ""
    test_code: str = ""


class ModuleAuthor:
    """Meta-agent that generates new modules."""

    def __init__(self):
        self.router = get_router()
        self.sandbox = get_sandbox()
        self.registry = get_module_registry()

    async def generate(
        self,
        requirement: str,
        module_name: Optional[str] = None,
        model: str = "anthropic",
        auto_test: bool = True,
    ) -> AuthorResult:
        """Generate a new module from a requirement description."""
        logger.info(f"Generating module for: {requirement[:100]}")

        # Step 1: Generate module code
        response = await self.router.complete(
            messages=[{"role": "user", "content": GENERATE_PROMPT.format(requirement=requirement)}],
            task_class="code",
            module="meta",
            provider_override=model,
            temperature=0.3,
            max_tokens=8192,
        )
        module_code = self._clean_code(response.content)
        if not module_name:
            module_name = self._extract_name(module_code) or f"auto_{int(time.time())}"

        # Step 2: Generate tests
        test_code = ""
        if auto_test:
            test_response = await self.router.complete(
                messages=[{"role": "user", "content": TEST_GENERATE_PROMPT.format(module_code=module_code)}],
                task_class="code",
                module="meta",
                provider_override=model,
                temperature=0.3,
                max_tokens=4096,
            )
            test_code = self._clean_code(test_response.content)

        # Step 3: Run in sandbox
        test_passed = False
        test_output = ""
        if auto_test and test_code:
            env = self.sandbox.create_env(f"meta_{module_name}")
            self.sandbox.install_deps(env, ["pytest"])
            test_passed, test_output = self.sandbox.run_tests(env, test_code, module_code)
            if test_passed:
                self.sandbox.cleanup(f"meta_{module_name}")

        # Step 4: Write module file
        module_dir = MODULES_DIR / module_name
        module_dir.mkdir(parents=True, exist_ok=True)
        module_path = module_dir / "__init__.py"
        module_path.write_text(module_code, encoding="utf-8")

        if test_code:
            test_path = module_dir / "test_generated.py"
            test_path.write_text(test_code, encoding="utf-8")

        # Step 5: Register
        status = "testing" if auto_test else "draft"
        authored = AuthoredModule(
            name=module_name,
            description=requirement[:200],
            path=str(module_path),
            status=status if not test_passed else "testing",
            provenance={
                "prompt": requirement,
                "model": response.model,
                "provider": response.provider,
                "cost_usd": response.cost_usd,
                "timestamp": time.time(),
            },
            tests_passed=test_passed,
            test_output=test_output[:1000],
            created_by="meta-agent",
        )
        self.registry.register(authored)

        return AuthorResult(
            success=True,
            module_name=module_name,
            module_path=str(module_path),
            test_passed=test_passed,
            test_output=test_output,
            module_code=module_code,
            test_code=test_code,
        )

    @staticmethod
    def _clean_code(raw: str) -> str:
        """Remove markdown code fences if present."""
        lines = raw.strip().split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines)

    @staticmethod
    def _extract_name(code: str) -> Optional[str]:
        """Try to extract a module name from generated code."""
        for line in code.split("\n"):
            if "name" in line and "=" in line and '"' in line:
                try:
                    return line.split('"')[1].replace("-", "_").replace(" ", "_").lower()
                except IndexError:
                    pass
        return None
