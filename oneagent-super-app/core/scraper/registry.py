from __future__ import annotations
from typing import List, Type
from .base import ScraperEngine, ScrapeResult, ScrapeOptions

class ScraperRegistry:
    def __init__(self):
        self._engines: dict = {}

    def register(self, engine: ScraperEngine):
        self._engines[engine.name] = engine

    def select(self, *, javascript: bool = False, screenshot: bool = False) -> List[ScraperEngine]:
        candidates = []
        for e in self._engines.values():
            if javascript and not e.supports_javascript:
                continue
            if screenshot and not e.supports_screenshot:
                continue
            candidates.append(e)
        return sorted(candidates, key=lambda x: -x.quality)

    async def scrape(self, url: str, options: ScrapeOptions) -> ScrapeResult:
        engines = self.select(javascript=options.javascript, screenshot=options.screenshot)
        last_error = "No engines available"
        for engine in engines:
            result = await engine.scrape(url, options)
            if result.success:
                return result
            last_error = result.error
        return ScrapeResult(url=url, success=False, error=last_error or "All engines failed", status=0)

GLOBAL_SCRAPER_REGISTRY = ScraperRegistry()
