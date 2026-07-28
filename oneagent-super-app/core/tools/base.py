from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

class ToolKind(Enum):
    READ = "read"
    EDIT = "edit"
    DELETE = "delete"
    MOVE = "move"
    SEARCH = "search"
    EXECUTE = "execute"
    THINK = "think"
    AGENT = "agent"
    FETCH = "fetch"
    COMMUNICATE = "communicate"
    PLAN = "plan"
    OTHER = "other"

MUTATOR_KINDS = {ToolKind.EDIT, ToolKind.DELETE, ToolKind.MOVE, ToolKind.EXECUTE}
READ_ONLY_KINDS = {ToolKind.READ, ToolKind.SEARCH, ToolKind.FETCH}

@dataclass
class ToolResult:
    output: str = ""
    error: Optional[str] = None
    data: Optional[dict] = None
    image_url: Optional[str] = None

    @property
    def success(self) -> bool:
        return not self.error

    def __bool__(self):
        return self.success

class ToolFailure(ToolResult):
    def __init__(self, error: str, output: str = ""):
        super().__init__(output=output, error=error)

class BaseTool(ABC):
    """Tool base mirroring OpenManus BaseTool + Cline createTool."""
    name: str = ""
    description: str = ""
    parameters: Optional[dict] = None
    kind: ToolKind = ToolKind.OTHER
    timeout_ms: int = 30_000
    retryable: bool = True
    max_retries: int = 1

    def to_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}},
            },
        }

    async def __call__(self, **kwargs) -> ToolResult:
        return await self.execute(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        ...

    async def cleanup(self):
        pass

class ToolCollection:
    """Minimal declarative registry from OpenManus."""
    def __init__(self, *tools: BaseTool):
        self.tools = tools
        self.tool_map = {t.name: t for t in tools}

    def to_params(self) -> List[dict]:
        return [t.to_param() for t in self.tools]

    async def execute(self, *, name: str, tool_input: dict) -> ToolResult:
        if name not in self.tool_map:
            return ToolFailure(f"Tool '{name}' not found")
        try:
            return await self.tool_map[name].execute(**tool_input)
        except Exception as e:
            return ToolFailure(str(e))

    def add_tool(self, tool: BaseTool):
        self.tool_map[tool.name] = tool
        self.tools = tuple(list(self.tools) + [tool])
