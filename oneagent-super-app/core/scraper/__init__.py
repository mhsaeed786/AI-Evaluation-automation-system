# Scraper engine abstraction inspired by Firecrawl
from .base import ScraperEngine, ScrapeResult, ScrapeOptions
from .registry import ScraperRegistry
from .engines import FetchEngine, PlaywrightEngine

__all__ = ["ScraperEngine", "ScrapeResult", "ScrapeOptions", "ScraperRegistry", "FetchEngine", "PlaywrightEngine"]
