# Unified tool system inspired by OpenManus, Cline, smolagents
from .base import BaseTool, ToolResult, ToolFailure, ToolCollection, ToolKind, MUTATOR_KINDS, READ_ONLY_KINDS
from .registry import ToolRegistry, GLOBAL_TOOL_REGISTRY
from .factory import tool

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolFailure",
    "ToolCollection",
    "ToolKind",
    "MUTATOR_KINDS",
    "READ_ONLY_KINDS",
    "ToolRegistry",
    "GLOBAL_TOOL_REGISTRY",
    "tool",
]
