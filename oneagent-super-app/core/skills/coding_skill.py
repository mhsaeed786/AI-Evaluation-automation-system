from __future__ import annotations
from .base import Skill, SkillContext
from .registry import GLOBAL_SKILL_REGISTRY
from ..coding import CodeAgent

class CodingSkill(Skill):
    name = "coding"

    async def run(self, context: SkillContext) -> dict:
        agent = CodeAgent(llm_descriptor=context.provider_descriptor, workspace=context.workspace)
        outputs = []
        async for ev in agent.run(context.query):
            outputs.append({"type": ev.type.value, "content": ev.content, "tool": ev.tool_name})
        return {"session_id": agent.session_id, "events": outputs}

GLOBAL_SKILL_REGISTRY.register(CodingSkill())
