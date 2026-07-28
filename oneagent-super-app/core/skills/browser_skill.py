from __future__ import annotations
from .base import Skill, SkillContext
from .registry import GLOBAL_SKILL_REGISTRY
from ..scraper import ScrapeOptions, GLOBAL_SCRAPER_REGISTRY, FetchEngine, PlaywrightEngine

class BrowserSkill(Skill):
    name = "browser"

    async def run(self, context: SkillContext) -> dict:
        url = context.extra.get("url", context.query)
        opts = ScrapeOptions(
            format="markdown",
            javascript=context.extra.get("javascript", True),
            screenshot=context.extra.get("screenshot", False),
            wait_for=context.extra.get("wait_for"),
        )
        GLOBAL_SCRAPER_REGISTRY.register(FetchEngine())
        GLOBAL_SCRAPER_REGISTRY.register(PlaywrightEngine())
        result = await GLOBAL_SCRAPER_REGISTRY.scrape(url, opts)
        return {
            "url": result.url,
            "title": result.title,
            "content": result.content,
            "screenshot": result.screenshot,
            "error": result.error,
        }

GLOBAL_SKILL_REGISTRY.register(BrowserSkill())
