from __future__ import annotations
import asyncio
from pathlib import Path
from ..tools import BaseTool, ToolResult, ToolKind, GLOBAL_TOOL_REGISTRY
from ..security.validator import validate_command

class ShellTool(BaseTool):
    name = "shell"
    description = "Run a validated shell command."
    parameters = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }
    kind = ToolKind.EXECUTE

    async def execute(self, *, command: str, **kwargs) -> ToolResult:
        try:
            command = validate_command(command)
        except Exception as e:
            return ToolResult(error=str(e))
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path.cwd()),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            out = stdout.decode(errors="replace") + "\n" + stderr.decode(errors="replace")
            return ToolResult(output=out.strip()[:8000])
        except Exception as e:
            return ToolResult(error=str(e))

GLOBAL_TOOL_REGISTRY.register(ShellTool())
