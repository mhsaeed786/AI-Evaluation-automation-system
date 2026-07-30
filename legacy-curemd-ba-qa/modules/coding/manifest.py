"""
Coding Module — CLI controller, repo scaffolding, code generation.

Provides tools for development workflows: scaffolding projects,
generating code, managing repos.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List

from core.agents.tools import get_registry, tool

logger = logging.getLogger(__name__)


@tool(name="scaffold_project", description="Scaffold a new project from a template", module="coding")
async def scaffold_project(name: str, template: str = "python", output_dir: str = ".") -> Dict:
    """Create a new project structure from a template."""
    from core.llm.router import get_router

    base = Path(output_dir) / name
    base.mkdir(parents=True, exist_ok=True)

    templates = {
        "python": ["src/", "tests/", "docs/", "requirements.txt", "setup.py", "README.md", ".gitignore"],
        "fastapi": ["app/", "app/api/", "app/core/", "app/models/", "tests/", "requirements.txt", "Dockerfile"],
        "react": ["src/", "src/components/", "src/pages/", "public/", "package.json", "vite.config.js"],
        "streamlit": ["pages/", "components/", "app.py", "requirements.txt", "README.md"],
    }

    files = templates.get(template, templates["python"])
    created = []
    for f in files:
        p = base / f
        if f.endswith("/"):
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            if template == "python" and f == "requirements.txt":
                p.write_text("# Auto-generated\n")
            elif template == "python" and f == "setup.py":
                p.write_text(f'from setuptools import setup\nsetup(name="{name}", version="0.1.0")\n')
            elif f == "README.md":
                p.write_text(f"# {name}\n")
            elif f == ".gitignore":
                p.write_text("__pycache__/\n*.pyc\n.env\n.venv/\n")
            elif f == "app.py":
                p.write_text(f'import streamlit as st\n\nst.title("{name}")\n')
            elif f == "package.json":
                p.write_text(f'{{"name": "{name}", "version": "0.1.0"}}')
            elif f == "vite.config.js":
                p.write_text(f'import {{ defineConfig }} from "vite";\nexport default defineConfig({{}});')
            else:
                p.write_text("")
            created.append(f)

    return {"project": name, "template": template, "path": str(base), "files_created": created}


@tool(name="generate_code", description="Generate code from a description using LLM", module="coding")
async def generate_code(description: str, language: str = "python", context: str = "") -> Dict:
    """Generate code from a natural language description."""
    from core.llm.router import get_router
    router = get_router()

    prompt = f"Generate {language} code for:\n{description}\n"
    if context:
        prompt += f"\nContext:\n{context}\n"
    prompt += "\nOutput ONLY the code, no markdown fences."

    response = await router.complete(
        messages=[{"role": "user", "content": prompt}],
        task_class="code",
        module="coding",
        temperature=0.3,
        max_tokens=4096,
    )
    code = response.content.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    return {"code": code, "language": language, "model": response.model, "cost": response.cost_usd}


@tool(name="review_code", description="Review code for issues, security, and best practices", module="coding")
async def review_code(code: str, language: str = "python") -> Dict:
    """Review code and provide feedback."""
    from core.llm.router import get_router
    router = get_router()

    response = await router.complete(
        messages=[
            {"role": "system", "content": "You are a code reviewer. Identify bugs, security issues, and improvement suggestions."},
            {"role": "user", "content": f"Review this {language} code:\n```\n{code}\n```"},
        ],
        task_class="code",
        module="coding",
        temperature=0.3,
    )
    return {"review": response.content, "model": response.model, "cost": response.cost_usd}


def register():
    return {
        "name": "coding",
        "description": "Code generation, scaffolding, and review tools",
        "version": "2.0.0",
        "tools": ["scaffold_project", "generate_code", "review_code"],
        "routes": [
            {"method": "POST", "path": "/coding/scaffold", "handler": "scaffold_project"},
            {"method": "POST", "path": "/coding/generate", "handler": "generate_code"},
            {"method": "POST", "path": "/coding/review", "handler": "review_code"},
        ],
    }
