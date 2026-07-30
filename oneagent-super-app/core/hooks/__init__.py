"""
OneAgent Core — Dual Hook System
Inspired by OpenClaw's dual hook architecture.

Two separate hook systems:
1. Internal hooks (operator scripts) — event-driven HOOK.md scripts for commands and lifecycle
2. Plugin hooks (programmatic) — in-process extension points via on(name, handler, opts)

Hook semantics:
- Priority-ordered (higher priority runs first)
- { block: true } is terminal (stops lower-priority handlers)
- { block: false } is a no-op
- Approval gating: before_tool_call can return requireApproval
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
from datetime import datetime


class HookPriority(Enum):
    """Standard priority levels for hooks."""
    SYSTEM = 100      # Core system hooks (run first)
    SECURITY = 90     # Security validation
    PLUGIN = 50       # Third-party plugins
    USER = 30         # User-defined hooks
    OPERATOR = 10     # Operator scripts (run last)


# All hook event types
HOOK_EVENTS = [
    # Agent lifecycle
    "before_model_resolve",      # Override provider/model before session loads
    "before_prompt_build",        # Inject context into system prompt
    "before_agent_reply",         # Short-circuit with synthetic reply
    "after_agent_reply",          # Post-process agent response

    # Tool lifecycle
    "before_tool_call",           # Block/rewrite/require approval
    "after_tool_call",            # Post-process tool result
    "tool_result_persist",        # Transform result before transcript write

    # Session lifecycle
    "session_create",
    "session_start",
    "session_end",
    "session_compact",

    # Message lifecycle
    "before_message_send",        # Block/modify outbound messages
    "after_message_receive",      # Process inbound messages

    # Gateway lifecycle
    "gateway_startup",
    "gateway_shutdown",
]


@dataclass
class HookResult:
    """Result from a hook handler."""
    block: bool = False           # If True, stops lower-priority handlers
    modify: Optional[dict] = None # Modified data to pass forward
    require_approval: Optional[dict] = None  # Human-in-the-loop gate
    error: Optional[str] = None


@dataclass
class HookHandler:
    """A registered hook handler."""
    name: str
    event: str
    handler: Callable
    priority: int = HookPriority.PLUGIN
    description: str = ""
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PluginHookSystem:
    """Programmatic in-process hook system for plugins."""

    def __init__(self):
        self._handlers: Dict[str, List[HookHandler]] = {event: [] for event in HOOK_EVENTS}

    def on(self, event: str, handler: Callable,
           priority: int = HookPriority.PLUGIN,
           name: str = None,
           description: str = "") -> str:
        """Register a plugin hook.

        Args:
            event: The event to hook into
            handler: Async or sync function(data: dict) -> HookResult | dict | None
            priority: Higher runs first
            name: Handler name for identification
            description: Human-readable description

        Returns: handler ID for removal
        """
        if event not in self._handlers:
            self._handlers[event] = []

        handler_id = name or f"hook_{len(self._handlers[event])}_{event}"
        h = HookHandler(
            name=handler_id,
            event=event,
            handler=handler,
            priority=priority,
            description=description,
        )
        self._handlers[event].append(h)
        # Sort by priority descending (higher first)
        self._handlers[event].sort(key=lambda x: x.priority, reverse=True)
        return handler_id

    def off(self, event: str, handler_id: str) -> bool:
        """Remove a hook handler."""
        if event not in self._handlers:
            return False
        before = len(self._handlers[event])
        self._handlers[event] = [h for h in self._handlers[event] if h.name != handler_id]
        return len(self._handlers[event]) < before

    async def trigger(self, event: str, data: dict = None) -> dict:
        """Trigger all handlers for an event.

        Handlers run in priority order (highest first).
        If a handler returns {block: true}, lower-priority handlers are skipped.

        Returns the (possibly modified) data after all handlers have run.
        """
        data = data or {}
        handlers = self._handlers.get(event, [])

        for handler in handlers:
            try:
                result = handler.handler(data)
                if asyncio.iscoroutine(result):
                    result = await result

                if result is None:
                    continue

                if isinstance(result, dict):
                    result = HookResult(**result)

                # Apply modifications
                if result.modify:
                    data.update(result.modify)

                # Block stops lower-priority handlers
                if result.block:
                    break

                # Approval gate
                if result.require_approval:
                    approved = await self._request_approval(result.require_approval)
                    if not approved.get("approved"):
                        data["blocked"] = True
                        data["block_reason"] = approved.get("reason", "Approval denied")
                        break

            except Exception as e:
                # Hook errors don't stop execution, but are logged
                data.setdefault("_hook_errors", []).append({
                    "handler": handler.name,
                    "event": event,
                    "error": str(e),
                })

        return data

    async def _request_approval(self, approval_req: dict) -> dict:
        """Request human approval for an action.

        In production, this would show a UI prompt.
        For now, auto-approve in non-interactive mode.
        """
        # TODO: Connect to frontend approval UI
        return {"approved": True, "reason": "Auto-approved (no UI connected)"}

    def list_handlers(self, event: str = None) -> List[dict]:
        """List registered handlers, optionally filtered by event."""
        if event:
            return [
                {"name": h.name, "event": h.event, "priority": h.priority, "description": h.description}
                for h in self._handlers.get(event, [])
            ]
        result = []
        for evt in self._handlers:
            for h in self._handlers[evt]:
                result.append({
                    "name": h.name, "event": h.event,
                    "priority": h.priority, "description": h.description
                })
        return result


class OperatorHookSystem:
    """Operator-installed HOOK.md scripts for simple command/lifecycle automation."""

    def __init__(self, hooks_dir: str = None):
        self.hooks_dir = Path(hooks_dir or "./hooks")
        self._scripts: Dict[str, List[Path]] = {}

    def _load_scripts(self):
        """Load HOOK.md scripts from the hooks directory."""
        if not self.hooks_dir.exists():
            return

        for hook_dir in self.hooks_dir.iterdir():
            if not hook_dir.is_dir():
                continue
            event_name = hook_dir.name
            hook_file = hook_dir / "HOOK.md"
            if hook_file.exists():
                self._scripts.setdefault(event_name, []).append(hook_file)

    def get_scripts(self, event: str = None) -> Dict[str, List[str]]:
        """Get all operator scripts, optionally filtered by event."""
        self._load_scripts()
        if event:
            return {event: [str(p) for p in self._scripts.get(event, [])]}
        return {k: [str(p) for p in v] for k, v in self._scripts.items()}


class DualHookSystem:
    """Combined hook system: plugin hooks + operator scripts."""

    def __init__(self, hooks_dir: str = None):
        self.plugin_hooks = PluginHookSystem()
        self.operator_hooks = OperatorHookSystem(hooks_dir)

    def on(self, *args, **kwargs):
        """Register a plugin hook."""
        return self.plugin_hooks.on(*args, **kwargs)

    def off(self, *args, **kwargs):
        """Remove a plugin hook."""
        return self.plugin_hooks.off(*args, **kwargs)

    async def trigger(self, event: str, data: dict = None) -> dict:
        """Trigger hooks for an event (plugin hooks first, then operator scripts)."""
        data = await self.plugin_hooks.trigger(event, data)
        # Operator scripts are informational (they can read data but not modify)
        return data

    def list_all(self) -> dict:
        """List all hooks (plugin + operator)."""
        return {
            "plugin_hooks": self.plugin_hooks.list_handlers(),
            "operator_scripts": self.operator_hooks.get_scripts(),
        }