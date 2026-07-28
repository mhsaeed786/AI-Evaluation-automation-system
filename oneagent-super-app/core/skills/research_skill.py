from __future__ import annotations
from .base import Skill, SkillContext
from .registry import GLOBAL_SKILL_REGISTRY
from ..llm import LLMResolver

class ResearchSkill(Skill):
    name = "research"

    async def run(self, context: SkillContext) -> dict:
        query = context.query
        llm = LLMResolver.create(context.provider_descriptor)
        plan_prompt = "Generate 3 concise web search queries for: " + query + "\nReturn as JSON list of strings."
        plan = await llm.complete(messages=[], system=plan_prompt)
        import json, re
        try:
            subqueries = json.loads(re.search(r"\[.*?\]", plan.content, re.S).group())
        except Exception:
            subqueries = [query]
        results = []
        for q in subqueries:
            results.append({"query": q, "summary": f"Stub result for {q}"})
        return {"queries": subqueries, "results": results, "report": plan.content}

GLOBAL_SKILL_REGISTRY.register(ResearchSkill())
