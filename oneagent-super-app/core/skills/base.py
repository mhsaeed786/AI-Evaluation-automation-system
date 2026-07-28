from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class SkillContext:
    query: str
    workspace: str = "."
    provider_descriptor: str = "gemini:gemini-2.5-flash"
    extra: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}

class Skill(ABC):
    name: str = ""

    @abstractmethod
    async def run(self, context: SkillContext) -> dict:
        ...
