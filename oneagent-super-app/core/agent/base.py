from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, List, Optional
import asyncio
import uuid

from .events import AgentEvent, EventType
from ..llm import LLMMessage, MessageRole

class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"
    STALLED = "stalled"

@dataclass
class AgentConfig:
    max_steps: int = 30
    duplicate_threshold: int = 2
    max_observe: int = 10000
    system_prompt: str = "You are OneAgent, a helpful generalist agent."
    cost_callback: Optional[Callable[[float], None]] = None
    before_tool: Optional[Callable[[str, dict], dict]] = None
    after_tool: Optional[Callable[[str, dict, Any], Any]] = None

class BaseAgent(ABC):
    """Base state machine + run loop (OpenManus pattern)."""

    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.state = AgentState.IDLE
        self.current_step = 0
        self.memory: List[LLMMessage] = []
        self.results: List[str] = []
        self.session_id = str(uuid.uuid4())

    async def run(self, request: str) -> AsyncIterator[AgentEvent]:
        if self.state != AgentState.IDLE:
            raise RuntimeError("Agent is not idle")
        self.memory.append(LLMMessage(role=MessageRole.USER, content=request))
        async with self._state_context(AgentState.RUNNING):
            try:
                async for ev in self._run_loop():
                    yield ev
            except Exception as e:
                self.state = AgentState.ERROR
                yield AgentEvent(type=EventType.ERROR, content=str(e), error=str(e))
            finally:
                await self.cleanup()

    async def _run_loop(self) -> AsyncIterator[AgentEvent]:
        while self.current_step < self.config.max_steps and self.state != AgentState.FINISHED:
            self.current_step += 1
            async for ev in self.step():
                yield ev
            if self._is_stuck():
                yield AgentEvent(type=EventType.STATE_CHANGE, content="stuck", data={"state": "stalled"})
                self.memory.append(LLMMessage(role=MessageRole.USER, content="You appear stuck. Try a different strategy."))
        if self.state != AgentState.FINISHED:
            yield AgentEvent(type=EventType.FINISHED, content="max_steps reached")

    @abstractmethod
    async def step(self) -> AsyncIterator[AgentEvent]:
        ...

    def _is_stuck(self) -> bool:
        """OpenManus stuck detection: duplicate assistant messages."""
        assistant_msgs = [m.content for m in self.memory if m.role == MessageRole.ASSISTANT]
        if len(assistant_msgs) < self.config.duplicate_threshold + 1:
            return False
        recent = assistant_msgs[-(self.config.duplicate_threshold + 1):]
        return all(m == recent[0] for m in recent)

    def _state_context(self, state: AgentState):
        class _Ctx:
            async def __aenter__(ctx_self):
                self._prev_state = self.state
                self.state = state
                return ctx_self
            async def __aexit__(ctx_self, exc_type, exc, tb):
                if exc:
                    self.state = AgentState.ERROR
                elif self.state == AgentState.RUNNING:
                    self.state = self._prev_state
        return _Ctx()

    async def cleanup(self):
        pass

    def get_context_messages(self) -> List[LLMMessage]:
        return self.memory
