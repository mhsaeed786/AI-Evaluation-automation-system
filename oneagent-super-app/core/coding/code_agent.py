from __future__ import annotations
from typing import List
from ..agent import ToolCallAgent, AgentConfig
from ..tools import ToolCollection
from .edit_tool import StrReplaceEditor
from .shell_tool import ShellTool
from .read_tool import ReadFileTool

class CodeAgent(ToolCallAgent):
    """Specialist coding agent with read/edit/shell tools."""

    def __init__(self, llm_descriptor: str = None, workspace: str = None):
        cfg = AgentConfig(
            system_prompt="""You are a coding specialist. You have read_file, str_replace_editor, and shell tools.
Always propose minimal, correct edits. Run tests or validation when possible.""",
            max_steps=50,
        )
        tools = ToolCollection(ReadFileTool(), StrReplaceEditor(), ShellTool())
        super().__init__(config=cfg, available_tools=tools, llm_descriptor=llm_descriptor)
        self.workspace = workspace
