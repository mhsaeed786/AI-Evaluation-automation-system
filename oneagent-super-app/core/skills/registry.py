from __future__ import annotations
from typing import Dict, List, Type
from .base import Skill, SkillContext

class SkillRegistry:
    def __init__(self):
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill):
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        return self._skills[name]

    def list(self) -> List[str]:
        return list(self._skills)

    async def run(self, name: str, context: SkillContext) -> dict:
        return await self._skills[name].run(context)

GLOBAL_SKILL_REGISTRY = SkillRegistry()
