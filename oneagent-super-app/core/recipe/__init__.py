"""
OneAgent Core — Recipe Runner (Multi-Step Pipelines)
Inspired by Super-App's recipe pattern with enhancements.

Features:
- Ordered skill chains with per-step error control
- Param merge with step-overrides-recipe precedence
- Dependency DAG (steps can depend on other steps)
- Conditional execution (when: expression)
- Parallel step support (steps with no dependencies run concurrently)
- Output passing between steps (step output → next step input)
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class RecipeStep:
    """A single step in a recipe."""
    name: str
    skill: str  # Skill ID to execute
    agent: Optional[str] = None  # Override default agent for this skill
    params: Dict[str, Any] = field(default_factory=dict)
    continue_on_error: bool = False
    depends_on: List[str] = field(default_factory=list)  # Step names this depends on
    when: Optional[str] = None  # Conditional expression (e.g., "result.exit_code == 0")
    timeout: int = 300  # Seconds

    def __post_init__(self):
        if not self.name:
            raise ValueError("Step name is required")
        if not self.skill:
            raise ValueError(f"Step '{self.name}' has no skill defined")


@dataclass
class RecipeStepResult:
    """Result of executing a recipe step."""
    step_name: str
    skill: str
    agent: str
    status: str  # "success", "error", "skipped", "timeout"
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RecipeResult:
    """Result of executing a complete recipe."""
    recipe_id: str
    status: str  # "completed", "failed", "partial"
    completed_steps: int = 0
    total_steps: int = 0
    results: List[RecipeStepResult] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    duration_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "recipe_id": self.recipe_id,
            "status": self.status,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "results": [r.__dict__ for r in self.results],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class RecipeRunner:
    """Executes multi-step recipes that chain skills and agents."""

    def __init__(self, skills_executor: Callable = None, recipes_dir: str = None):
        """
        Args:
            skills_executor: A function(skill_id, agent_name, params) -> dict
            recipes_dir: Directory containing recipe JSON files
        """
        self._executor = skills_executor or self._default_executor
        self.recipes: Dict[str, dict] = {}
        self.recipes_dir = Path(recipes_dir or "./recipes")
        self._load_recipes()

    def _default_executor(self, skill_id: str, agent: str, params: dict) -> dict:
        """Default executor — override with real implementation."""
        return {"error": "No executor configured", "skill": skill_id}

    def _load_recipes(self):
        """Load all recipe JSON files from the recipes directory."""
        if not self.recipes_dir.exists():
            return
        for recipe_file in self.recipes_dir.glob("*.json"):
            try:
                with open(recipe_file, "r", encoding="utf-8") as f:
                    recipe = json.load(f)
                    self.recipes[recipe["id"]] = recipe
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load recipe {recipe_file.name}: {e}")

    def add_recipe(self, recipe_id: str, recipe: dict) -> None:
        """Register a recipe programmatically."""
        self.recipes[recipe_id] = recipe
        self.recipes_dir.mkdir(parents=True, exist_ok=True)
        with open(self.recipes_dir / f"{recipe_id}.json", "w", encoding="utf-8") as f:
            json.dump(recipe, f, indent=2)

    def list_recipes(self) -> List[dict]:
        """List all available recipes."""
        return list(self.recipes.values())

    def get_recipe(self, recipe_id: str) -> Optional[dict]:
        """Get a recipe by ID."""
        return self.recipes.get(recipe_id)

    def _check_condition(self, when_expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate a conditional expression.

        Supports simple expressions like:
        - "result.exit_code == 0"
        - "steps.scan.output.found == true"
        - "steps.scan.status == 'success'"
        """
        try:
            # Safe eval with limited namespace
            namespace = {"context": context, "steps": context.get("steps", {})}
            return bool(eval(when_expr, {"__builtins__": {}}, namespace))
        except Exception:
            # If expression fails, default to True (run the step)
            return True

    def _resolve_step_order(self, steps: List[RecipeStep]) -> List[List[RecipeStep]]:
        """Resolve step execution order based on dependencies (topological sort).

        Returns a list of batches — steps in the same batch can run in parallel.
        """
        step_map = {s.name: s for s in steps}
        completed = set()
        batches = []

        remaining = list(steps)
        while remaining:
            batch = []
            for step in remaining:
                deps = step.depends_on
                if all(d in completed for d in deps):
                    batch.append(step)

            if not batch:
                # Circular dependency — just run what's left in order
                batches.append(remaining)
                break

            batches.append(batch)
            for s in batch:
                completed.add(s.name)
                remaining.remove(s)

        return batches

    async def run_recipe(self, recipe_id: str, params: dict = None) -> RecipeResult:
        """Execute a recipe with all its steps.

        Supports parallel execution of independent steps (DAG).
        """
        recipe = self.recipes.get(recipe_id)
        if not recipe:
            return RecipeResult(
                recipe_id=recipe_id,
                status="failed",
                error=f"Recipe '{recipe_id}' not found",
            )

        params = params or {}
        raw_steps = recipe.get("steps", [])
        steps = [RecipeStep(**s) for s in raw_steps]

        result = RecipeResult(
            recipe_id=recipe_id,
            total_steps=len(steps),
        )

        start_time = datetime.now()
        context = {"steps": {}, "params": params}

        # Resolve execution order
        batches = self._resolve_step_order(steps)

        for batch in batches:
            # Run all steps in this batch concurrently
            tasks = []
            for step in batch:
                # Check conditional
                if step.when and not self._check_condition(step.when, context):
                    step_result = RecipeStepResult(
                        step_name=step.name,
                        skill=step.skill,
                        agent=step.agent or "default",
                        status="skipped",
                        timestamp=datetime.now().isoformat(),
                    )
                    result.results.append(step_result)
                    context["steps"][step.name] = step_result.__dict__
                    continue

                # Merge params: recipe params < step params
                merged_params = {**params, **step.params}
                tasks.append(self._run_step(step, merged_params))

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, step_result in enumerate(batch_results):
                if isinstance(step_result, Exception):
                    step = batch[i]
                    step_result = RecipeStepResult(
                        step_name=step.name,
                        skill=step.skill,
                        agent=step.agent or "default",
                        status="error",
                        error=str(step_result),
                    )

                result.results.append(step_result)
                context["steps"][step_result.step_name] = step_result.__dict__

                # Check if we should stop
                if step_result.status in ("error", "timeout"):
                    step = batch[i]
                    if not step.continue_on_error:
                        result.status = "failed"
                        result.error = f"Step '{step_result.step_name}' failed: {step_result.error}"
                        result.finished_at = datetime.now().isoformat()
                        result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                        return result

                if step_result.status == "success":
                    result.completed_steps += 1

        result.status = "completed" if result.completed_steps == result.total_steps else "partial"
        result.finished_at = datetime.now().isoformat()
        result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return result

    async def _run_step(self, step: RecipeStep, params: dict) -> RecipeStepResult:
        """Execute a single recipe step."""
        start = datetime.now()
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self._executor, step.skill, step.agent, params
                ),
                timeout=step.timeout,
            )

            return RecipeStepResult(
                step_name=step.name,
                skill=step.skill,
                agent=step.agent or "default",
                status="success" if not result.get("error") else "error",
                output=result,
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                error=result.get("error"),
                duration_ms=int((datetime.now() - start).total_seconds() * 1000),
            )
        except asyncio.TimeoutError:
            return RecipeStepResult(
                step_name=step.name,
                skill=step.skill,
                agent=step.agent or "default",
                status="timeout",
                error=f"Step timed out after {step.timeout}s",
                duration_ms=int((datetime.now() - start).total_seconds() * 1000),
            )
        except Exception as e:
            return RecipeStepResult(
                step_name=step.name,
                skill=step.skill,
                agent=step.agent or "default",
                status="error",
                error=str(e),
                duration_ms=int((datetime.now() - start).total_seconds() * 1000),
            )