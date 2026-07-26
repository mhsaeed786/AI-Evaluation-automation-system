"""
Tool Registry — decorator-based tool registration.

Modules register functions as tools with @tool. The agent loop
discovers and calls them by name.
"""

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, get_type_hints

logger = logging.getLogger(__name__)


@dataclass
class ToolDef:
    """Definition of a registered tool."""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    module: str = ""
    requires_approval: bool = False

    def to_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function-calling schema."""
        sig = inspect.signature(self.func)
        params = {}
        required = []
        for pname, param in sig.parameters.items():
            if pname in ("self", "cls"):
                continue
            ptype = "string"
            desc = ""
            if pname in self.parameters:
                pmeta = self.parameters[pname]
                ptype = pmeta.get("type", "string")
                desc = pmeta.get("description", "")
            if param.default is inspect.Parameter.empty:
                required.append(pname)
            params[pname] = {"type": ptype, "description": desc}

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": required,
                },
            },
        }


class ToolRegistry:
    """Global registry of available tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: str = "",
        parameters: Optional[Dict] = None,
        module: str = "",
        requires_approval: bool = False,
    ):
        """Decorator to register a function as a tool."""
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool = ToolDef(
                name=tool_name,
                description=description or func.__doc__ or "",
                func=func,
                parameters=parameters or {},
                module=module,
                requires_approval=requires_approval,
            )
            self._tools[tool_name] = tool
            func._tool = tool
            return func
        return decorator

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def list_tools(self, module: Optional[str] = None) -> List[ToolDef]:
        tools = list(self._tools.values())
        if module:
            tools = [t for t in tools if t.module == module]
        return tools

    def list_schemas(self, module: Optional[str] = None) -> List[Dict]:
        return [t.to_schema() for t in self.list_tools(module)]

    async def call(self, name: str, **kwargs) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        result = tool.func(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    def register_module_tools(self, module_name: str, tools_module):
        """Auto-register all @tool-decorated functions from a module."""
        for attr_name in dir(tools_module):
            obj = getattr(tools_module, attr_name)
            if callable(obj) and hasattr(obj, "_tool"):
                tool: ToolDef = obj._tool
                tool.module = module_name
                self._tools[tool.name] = tool


_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


# Convenience decorator
def tool(
    name: Optional[str] = None,
    description: str = "",
    parameters: Optional[Dict] = None,
    module: str = "",
    requires_approval: bool = False,
):
    """Register a function as an agent tool."""
    return get_registry().register(
        name=name, description=description, parameters=parameters,
        module=module, requires_approval=requires_approval,
    )
