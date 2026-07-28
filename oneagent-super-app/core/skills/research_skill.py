from __future__ import annotations
import asyncio
from .base import Skill, SkillContext, GLOBAL_SKILL_REGISTRY
from ..llm import LLMResolver
from ..scraper import ScrapeOptions, GLOBAL_SCRAPER_REGISTRY

class ResearchSkill(Skill):
    name = "research"

    async def run(self, context: SkillContext) -> dict:
        query = context.query
        llm = LLMResolver.create(context.provider_descriptor)
        # Plan sub-queries
        plan_prompt = f"Generate 3 concise web search queries for: {query}
Return as JSON list of strings."
        plan = await llm.complete(messages=[], system=plan_prompt)
        import json, re
        try:
            subqueries = json.loads(re.search(r"[.*?]", plan.content, re.S).group())
        except Exception:
            subqueries = [query]
        results = []
        for q in subqueries:
            # Simulated search: just scrape top result URL placeholder logic would go here
            results.append({"query": q, "summary": f"Stub result for {q}"})
        return {"queries": subqueries, "results": results, "report": plan.content}

GLOBAL_SKILL_REGISTRY.register(ResearchSkill())
