from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class ScrapeFormat(Enum):
    HTML = "html"
    MARKDOWN = "markdown"
    TEXT = "text"

@dataclass
class ScrapeOptions:
    format: ScrapeFormat = ScrapeFormat.MARKDOWN
    screenshot: bool = False
    wait_for: Optional[str] = None
    timeout: int = 30
    javascript: bool = False

@dataclass
class ScrapeResult:
    url: str
    title: str = ""
    content: str = ""
    html: str = ""
    markdown: str = ""
    screenshot: Optional[str] = None
    status: int = 200
    success: bool = True
    error: Optional[str] = None

class ScraperEngine(ABC):
    name: str = "abstract"
    quality: int = 0
    supports_javascript: bool = False
    supports_screenshot: bool = False

    @abstractmethod
    async def scrape(self, url: str, options: ScrapeOptions) -> ScrapeResult:
        ...
