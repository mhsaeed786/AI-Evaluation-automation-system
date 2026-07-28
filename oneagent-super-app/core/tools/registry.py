from __future__ import annotations
from typing import Dict, List, Type
from .base import BaseTool

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def register_many(self, *tools: BaseTool):
        for t in tools:
            self._tools[t.name] = t

    def get(self, name: str) -> BaseTool:
        return self._tools[name]

    def list(self) -> List[str]:
        return list(self._tools)

    def collection(self) -> "ToolCollection":
        from .base import ToolCollection
        return ToolCollection(*self._tools.values())

    def clone(self) -> "ToolRegistry":
        other = ToolRegistry()
        other._tools = dict(self._tools)
        return other

GLOBAL_TOOL_REGISTRY = ToolRegistry()
