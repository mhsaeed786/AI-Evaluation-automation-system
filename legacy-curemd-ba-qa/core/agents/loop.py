"""
Agent Loop — Plan → Tool-call → Observe → Repeat.

The single implementation of the agentic cycle. Modules contribute
tools (via core/agents/tools.py) and prompts. This loop orchestrates.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..llm.router import LLMRouter, get_router
from .tools import ToolRegistry, get_registry
from .memory import Scratchpad, LongTermMemory, get_long_term_memory

logger = logging.getLogger(__name__)


class ApprovalMode(Enum):
    AUTO = "auto"           # No approval needed
    SUGGEST = "suggest"     # Show what will happen, proceed
    APPROVE = "approve"     # Require user approval for tool calls


@dataclass
class AgentConfig:
    name: str = "default"
    task_class: str = "reason"
    module: str = ""
    max_iterations: int = 10
    approval_mode: ApprovalMode = ApprovalMode.AUTO
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)  # empty = all available
    on_tool_call: Optional[Callable] = None  # callback for approval
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class AgentResult:
    success: bool
    output: str
    iterations: int
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    cost_usd: float = 0.0
    error: Optional[str] = None


SYSTEM_PROMPT_TEMPLATE = """You are {name}, an AI agent. You have access to tools.

## Instructions
{system_prompt}

## Available Tools
{tool_descriptions}

## Rules
1. Plan your approach before acting.
2. Use tools when you need information or need to take action.
3. Observe tool results before deciding next steps.
4. When you have the final answer, respond with it directly.
5. If you cannot complete the task, explain why.

Respond in JSON when using tools:
{{"thought": "your reasoning", "tool": "tool_name", "args": {{...}}}}

Or respond with plain text when you have the final answer.
"""


class AgentLoop:
    """The generic agent loop — plan, execute, observe, repeat."""

    def __init__(
        self,
        config: AgentConfig,
        router: Optional[LLMRouter] = None,
        registry: Optional[ToolRegistry] = None,
        memory: Optional[LongTermMemory] = None,
    ):
        self.config = config
        self.router = router or get_router()
        self.registry = registry or get_registry()
        self.memory = memory or get_long_term_memory()
        self.scratchpad = Scratchpad()

    def _build_system_prompt(self) -> str:
        tools = self.registry.list_tools()
        if self.config.tools:
            tools = [t for t in tools if t.name in self.config.tools]
        tool_descs = "\n".join(
            f"- **{t.name}**: {t.description}" for t in tools
        )
        return SYSTEM_PROMPT_TEMPLATE.format(
            name=self.config.name,
            system_prompt=self.config.system_prompt,
            tool_descriptions=tool_descs or "No tools available.",
        )

    async def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        """Execute the agent loop for a task."""
        self.scratchpad.clear()
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": task},
        ]
        if context:
            messages.insert(1, {"role": "system", "content": f"Context: {json.dumps(context)}"})

        total_cost = 0.0
        tool_calls_log = []

        for iteration in range(self.config.max_iterations):
            response = await self.router.complete(
                messages=messages,
                task_class=self.config.task_class,
                module=self.config.module,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            total_cost += response.cost_usd
            self.scratchpad.add_thought(f"[iter {iteration + 1}] LLM responded")

            # Check if response is a tool call (JSON)
            content = response.content.strip()
            tool_result = self._try_parse_tool_call(content)

            if tool_result is None:
                # Final answer
                self.scratchpad.add_observation("Agent provided final answer")
                return AgentResult(
                    success=True,
                    output=content,
                    iterations=iteration + 1,
                    tool_calls=tool_calls_log,
                    cost_usd=total_cost,
                )

            # Execute tool call
            tool_name, tool_args = tool_result
            self.scratchpad.add_action(tool_name, str(tool_args))

            # Approval check
            if self.config.approval_mode == ApprovalMode.APPROVE:
                if self.config.on_tool_call:
                    approved = self.config.on_tool_call(tool_name, tool_args)
                    if not approved:
                        messages.append({"role": "assistant", "content": content})
                        messages.append({
                            "role": "user",
                            "content": "Tool call was not approved. Try a different approach or explain why you need this tool.",
                        })
                        continue

            try:
                result = await self.registry.call(tool_name, **tool_args)
                result_str = json.dumps(result, default=str)[:2000]
                tool_calls_log.append({
                    "tool": tool_name, "args": tool_args,
                    "result_preview": result_str[:200], "success": True,
                })
                self.scratchpad.add_observation(f"Tool {tool_name} result: {result_str[:300]}")
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"Tool result: {result_str}"})
            except Exception as e:
                error_msg = f"Tool {tool_name} error: {e}"
                tool_calls_log.append({
                    "tool": tool_name, "args": tool_args,
                    "error": str(e), "success": False,
                })
                self.scratchpad.add_observation(error_msg)
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": error_msg})

        return AgentResult(
            success=False,
            output=self.scratchpad.summary,
            iterations=self.config.max_iterations,
            tool_calls=tool_calls_log,
            cost_usd=total_cost,
            error="Max iterations reached without final answer",
        )

    def _try_parse_tool_call(self, content: str) -> Optional[tuple]:
        """Try to parse a JSON tool call from the LLM response."""
        try:
            # Try to find JSON in the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                return None
            parsed = json.loads(content[json_start:json_end])
            if "tool" in parsed:
                return parsed["tool"], parsed.get("args", {})
        except (json.JSONDecodeError, KeyError):
            pass
        return None
