from __future__ import annotations
from pathlib import Path
from ..tools import BaseTool, ToolResult, ToolKind, GLOBAL_TOOL_REGISTRY

class StrReplaceEditor(BaseTool):
    name = "str_replace_editor"
    description = "Edit files with create, str_replace, insert, view, undo_edit commands (Anthropic style)."
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "enum": ["create", "str_replace", "insert", "view", "undo_edit"]},
            "path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
            "insert_line": {"type": "integer"},
        },
        "required": ["command", "path"],
    }
    kind = ToolKind.EDIT
    _history: dict = {}

    async def execute(self, *, command: str, path: str, old_string: str = "", new_string: str = "", insert_line: int = 0, **kwargs) -> ToolResult:
        p = Path(path)
        try:
            if command == "create":
                p.write_text(new_string, encoding="utf-8")
                return ToolResult(output=f"Created {path}")
            if command == "view":
                if not p.exists():
                    return ToolResult(error=f"{path} does not exist")
                return ToolResult(output=p.read_text(encoding="utf-8"))
            if command not in ("str_replace", "insert", "undo_edit"):
                return ToolResult(error=f"Unknown command {command}")
            self._history.setdefault(path, []).append(p.read_text(encoding="utf-8"))
            text = p.read_text(encoding="utf-8")
            if command == "str_replace":
                if old_string not in text:
                    return ToolResult(error="old_string not found")
                p.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
                return ToolResult(output=f"Replaced in {path}")
            if command == "insert":
                lines = text.splitlines()
                lines.insert(insert_line, new_string)
                p.write_text("\n".join(lines), encoding="utf-8")
                return ToolResult(output=f"Inserted into {path}")
            if command == "undo_edit":
                hist = self._history.get(path, [])
                if not hist:
                    return ToolResult(error="No undo history")
                p.write_text(hist.pop(), encoding="utf-8")
                return ToolResult(output=f"Undid edit in {path}")
        except Exception as e:
            return ToolResult(error=str(e))

GLOBAL_TOOL_REGISTRY.register(StrReplaceEditor())
