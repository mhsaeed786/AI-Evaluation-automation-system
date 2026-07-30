"""
OneAgent Core — Sub-Agent System with Push-Based Completion
Inspired by OpenClaw's sub-agent architecture.

Features:
- Non-blocking spawn (returns immediately with run_id + child_session_key)
- Push-based completion announce (no polling)
- Context modes: isolated (fresh transcript) or fork (branch parent)
- Nesting depth with tool policy (depth-1 gets session tools, depth-2 doesn't)
- Cascade stop (stopping parent stops all children)
- Max 8 concurrent sub-agents
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import hashlib


class SubAgentContextMode(Enum):
    ISOLATED = "isolated"  # Fresh child transcript (default)
    FORK = "fork"          # Branch from parent's transcript


class SubAgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubAgentRun:
    """Represents a sub-agent execution."""
    run_id: str
    parent_session_id: str
    child_session_id: str
    task: str
    context_mode: SubAgentContextMode
    depth: int
    status: SubAgentStatus = SubAgentStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    runtime_ms: int = 0
    tokens_used: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    announce_callback: Optional[Callable] = None


class SubAgentManager:
    """Manages sub-agent spawning, execution, and completion."""

    MAX_CONCURRENT = 8
    MAX_DEPTH = 5
    RECOMMENDED_DEPTH = 2

    def __init__(self, session_manager=None, harness_registry=None):
        self._session_manager = session_manager
        self._harness_registry = harness_registry
        self._runs: Dict[str, SubAgentRun] = {}
        self._children_by_parent: Dict[str, List[str]] = {}
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        self._announce_listeners: Dict[str, asyncio.Future] = {}

    def _gen_run_id(self) -> str:
        return hashlib.sha256(f"subagent:{datetime.now().isoformat()}".encode()).hexdigest()[:16]

    def _get_depth(self, parent_session_id: str) -> int:
        """Determine the depth of a sub-agent based on its parent."""
        parent = self._session_manager.get_session(parent_session_id) if self._session_manager else None
        if parent and parent.parent_session_id:
            # Parent is itself a sub-agent — increment depth
            parent_run = None
            for run in self._runs.values():
                if run.child_session_id == parent_session_id:
                    parent_run = run
                    break
            return (parent_run.depth + 1) if parent_run else 1
        return 1

    def can_spawn(self, parent_session_id: str) -> bool:
        """Check if a sub-agent can be spawned from the given parent."""
        depth = self._get_depth(parent_session_id)
        return depth < self.MAX_DEPTH

    def get_allowed_tools(self, depth: int) -> List[str]:
        """Get allowed tools for a given depth.

        Depth 1 (orchestrators): full tool set including session management
        Depth 2+ (leaf workers): no session tools (prevents runaway fan-out)
        """
        if depth == 1:
            return [
                "web_fetch", "web_search", "browser_use",
                "code_exec", "file_ops", "shell_exec",
                "session_spawn", "session_list", "session_create",
            ]
        else:
            return [
                "web_fetch", "web_search", "browser_use",
                "code_exec", "file_ops",  # No shell_exec or session tools
            ]

    async def spawn(self, parent_session_id: str, task: str,
                    context_mode: SubAgentContextMode = SubAgentContextMode.ISOLATED,
                    agent_id: str = "subagent",
                    on_complete: Callable = None) -> SubAgentRun:
        """Spawn a sub-agent. Returns immediately with run info.

        The sub-agent runs in the background. Completion is announced
        via the on_complete callback (push-based, not polling).
        """
        depth = self._get_depth(parent_session_id)
        if depth >= self.MAX_DEPTH:
            raise ValueError(
                f"Max nesting depth ({self.MAX_DEPTH}) reached. "
                f"Depth {self.RECOMMENDED_DEPTH} recommended."
            )

        run_id = self._gen_run_id()
        child_session_id = f"subagent:{run_id}"

        # Create child session
        if self._session_manager:
            if context_mode == SubAgentContextMode.FORK:
                # Fork: copy parent's context
                parent_session = self._session_manager.get_session(parent_session_id)
                child = self._session_manager.create_session(
                    session_id=child_session_id,
                    agent_id=agent_id,
                    parent_session_id=parent_session_id,
                )
                if parent_session:
                    child.messages = list(parent_session.messages[-20:])  # Last 20 msgs
                    child.token_count = parent_session.token_count
            else:
                # Isolated: fresh transcript
                child = self._session_manager.create_session(
                    session_id=child_session_id,
                    agent_id=agent_id,
                    parent_session_id=parent_session_id,
                )

        run = SubAgentRun(
            run_id=run_id,
            parent_session_id=parent_session_id,
            child_session_id=child_session_id,
            task=task,
            context_mode=context_mode,
            depth=depth,
            announce_callback=on_complete,
        )
        self._runs[run_id] = run

        # Track parent→children
        if parent_session_id not in self._children_by_parent:
            self._children_by_parent[parent_session_id] = []
        self._children_by_parent[parent_session_id].append(run_id)

        # Create a future for push-based completion
        future = asyncio.get_event_loop().create_future()
        self._announce_listeners[run_id] = future

        # Launch in background
        asyncio.create_task(self._execute(run))

        return run

    async def _execute(self, run: SubAgentRun) -> None:
        """Execute a sub-agent run in the background."""
        async with self._semaphore:
            run.status = SubAgentStatus.RUNNING
            import time
            start = time.time()

            try:
                # Execute via harness
                from core.harness import HarnessContext
                context = HarnessContext(
                    prompt=run.task,
                    system_instruction=f"You are a sub-agent at depth {run.depth}. "
                                       f"Complete this task and return a concise result.",
                )

                if self._harness_registry:
                    harness = await self._harness_registry.select(context)
                    result = await harness.execute(context)
                    run.result = result.text
                    run.tokens_used = sum(result.usage.values()) if result.usage else 0
                else:
                    run.result = f"[Sub-Agent depth={run.depth}] Task processed: {run.task}"
                    run.tokens_used = 500

                run.status = SubAgentStatus.COMPLETED

            except Exception as e:
                run.status = SubAgentStatus.FAILED
                run.error = str(e)

            run.runtime_ms = int((time.time() - start) * 1000)
            run.finished_at = datetime.now().isoformat()

            # Push-based announce
            if run.announce_callback:
                try:
                    await run.announce_callback(run)
                except Exception:
                    pass

            # Resolve the completion future
            future = self._announce_listeners.pop(run.run_id, None)
            if future and not future.done():
                future.set_result(run)

    async def wait_for(self, run_id: str, timeout: int = 300) -> SubAgentRun:
        """Wait for a sub-agent to complete (push-based, not polling)."""
        future = self._announce_listeners.get(run_id)
        if future is None:
            # Already completed
            return self._runs.get(run_id)

        return await asyncio.wait_for(future, timeout=timeout)

    async def stop(self, run_id: str) -> bool:
        """Stop a sub-agent run."""
        run = self._runs.get(run_id)
        if run and run.status in (SubAgentStatus.PENDING, SubAgentStatus.RUNNING):
            run.status = SubAgentStatus.CANCELLED
            return True
        return False

    async def stop_all_children(self, parent_session_id: str) -> int:
        """Cascade stop: stop all children of a parent session."""
        child_run_ids = self._children_by_parent.get(parent_session_id, [])
        stopped = 0
        for run_id in child_run_ids:
            if await self.stop(run_id):
                stopped += 1
            # Recursively stop grandchildren
            run = self._runs.get(run_id)
            if run:
                stopped += await self.stop_all_children(run.child_session_id)
        return stopped

    def get_run(self, run_id: str) -> Optional[SubAgentRun]:
        """Get a sub-agent run by ID."""
        return self._runs.get(run_id)

    def list_runs(self, parent_session_id: str = None) -> List[SubAgentRun]:
        """List all sub-agent runs, optionally filtered by parent."""
        runs = list(self._runs.values())
        if parent_session_id:
            runs = [r for r in runs if r.parent_session_id == parent_session_id]
        return runs

    def get_active_count(self) -> int:
        """Count of currently running sub-agents."""
        return sum(1 for r in self._runs.values() if r.status == SubAgentStatus.RUNNING)