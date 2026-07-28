from __future__ import annotations
from abc import abstractmethod
from typing import AsyncIterator
from .base import BaseAgent
from .events import AgentEvent

class ReActAgent(BaseAgent):
    """Splits step into think() + act()."""

    async def step(self) -> AsyncIterator[AgentEvent]:
        async for ev in self.think():
            yield ev
        async for ev in self.act():
            yield ev

    @abstractmethod
    async def think(self) -> AsyncIterator[AgentEvent]:
        ...

    @abstractmethod
    async def act(self) -> AsyncIterator[AgentEvent]:
        ...
