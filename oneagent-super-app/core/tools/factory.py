from __future__ import annotations
from typing import Callable, Optional
from .base import BaseTool, ToolResult, ToolKind

def tool(name: str, description: str, parameters: Optional[dict] = None, kind: ToolKind = ToolKind.OTHER):
    """Decorator/factory for simple function tools (smolagents style)."""
    def decorator(fn: Callable[..., ToolResult]):
        class FnTool(BaseTool):
            pass
        t = FnTool()
        t.name = name
        t.description = description
        t.parameters = parameters or {"type": "object", "properties": {}}
        t.kind = kind
        async def execute(self, **kwargs):
            try:
                return fn(**kwargs)
            except Exception as e:
                return ToolResult(error=str(e))
        t.execute = execute
        return t
    return decorator
