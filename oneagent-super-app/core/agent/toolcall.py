from __future__ import annotations
import json
from typing import AsyncIterator

from .react import ReActAgent
from .events import AgentEvent, EventType
from ..llm import LLMMessage, MessageRole, LLMResolver
from ..tools import ToolCollection

class ToolCallAgent(ReActAgent):
    """LLM function-calling loop (OpenManus ToolCallAgent)."""

    def __init__(self, config=None, available_tools: ToolCollection = None, llm_descriptor: str = None):
        super().__init__(config)
        self.tools = available_tools or ToolCollection()
        self.llm = LLMResolver.create(llm_descriptor or "gemini:gemini-2.5-flash")
        self.special_tool_names = ["terminate"]

    async def think(self) -> AsyncIterator[AgentEvent]:
        system = self.config.system_prompt
        response = await self.llm.complete(
            messages=self.memory,
            system=system,
            tools=self.tools.to_params(),
            cost_callback=self.config.cost_callback,
        )
        self.memory.append(LLMMessage(role=MessageRole.ASSISTANT, content=response.content, tool_calls=response.tool_calls))
        if response.content:
            yield AgentEvent(type=EventType.MESSAGE, content=response.content, step=self.current_step)
        for tc in response.tool_calls:
            yield AgentEvent(type=EventType.TOOL_CALL, tool_name=tc.name, tool_input=tc.arguments, step=self.current_step)
        if not response.tool_calls:
            self.state = "finished"

    async def act(self) -> AsyncIterator[AgentEvent]:
        last_assistant = [m for m in self.memory if m.role == MessageRole.ASSISTANT][-1]
        if not last_assistant.tool_calls:
            self.state = "finished"
            yield AgentEvent(type=EventType.FINISHED, content="done", step=self.current_step)
            return

        for tc in last_assistant.tool_calls:
            if self.config.before_tool:
                tc.arguments = self.config.before_tool(tc.name, tc.arguments)
            result = await self.tools.execute(name=tc.name, tool_input=tc.arguments)
            result_text = result.output[:self.config.max_observe]
            if result.error:
                result_text = result_text + "\nERROR: " + result.error
            self.memory.append(LLMMessage(role=MessageRole.TOOL, content=result_text, tool_call_id=tc.id))
            if self.config.after_tool:
                self.config.after_tool(tc.name, tc.arguments, result)
            yield AgentEvent(type=EventType.TOOL_RESULT, tool_name=tc.name, content=result_text, data=result.data or {}, step=self.current_step)
            if tc.name in self.special_tool_names:
                self.state = "finished"
                yield AgentEvent(type=EventType.FINISHED, content="terminated by tool", step=self.current_step)
                return

    async def cleanup(self):
        for t in self.tools.tools:
            try:
                await t.cleanup()
            except Exception:
                pass
