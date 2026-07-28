from __future__ import annotations
from pathlib import Path
from ..tools import BaseTool, ToolResult, ToolKind, GLOBAL_TOOL_REGISTRY

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read contents of one or more files."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "offset": {"type": "integer", "default": 1},
            "limit": {"type": "integer", "default": 200},
        },
        "required": ["path"],
    }
    kind = ToolKind.READ

    async def execute(self, *, path: str, offset: int = 1, limit: int = 200, **kwargs) -> ToolResult:
        try:
            p = Path(path).resolve()
            if not p.exists():
                return ToolResult(error=f"File not found: {path}")
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            start = max(0, offset - 1)
            chunk = lines[start:start + limit]
            numbered = "\n".join(f"{i + start + 1:4}: {line}" for i, line in enumerate(chunk))
            return ToolResult(output=numbered)
        except Exception as e:
            return ToolResult(error=str(e))

GLOBAL_TOOL_REGISTRY.register(ReadFileTool())
