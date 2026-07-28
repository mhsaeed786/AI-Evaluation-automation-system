# Scraper engine abstraction inspired by Firecrawl
from .base import ScraperEngine, ScrapeResult, ScrapeOptions, ScrapeFormat
from .registry import ScraperRegistry, GLOBAL_SCRAPER_REGISTRY
from .engines import FetchEngine, PlaywrightEngine

__all__ = [
    "ScraperEngine",
    "ScrapeResult",
    "ScrapeOptions",
    "ScrapeFormat",
    "ScraperRegistry",
    "GLOBAL_SCRAPER_REGISTRY",
    "FetchEngine",
    "PlaywrightEngine",
]
