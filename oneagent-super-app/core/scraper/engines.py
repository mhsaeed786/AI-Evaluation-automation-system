from __future__ import annotations
import re
from typing import Optional
import aiohttp

from .base import ScraperEngine, ScrapeResult, ScrapeOptions, ScrapeFormat

class FetchEngine(ScraperEngine):
    name = "fetch"
    quality = 5
    supports_javascript = False
    supports_screenshot = False

    async def scrape(self, url: str, options: ScrapeOptions) -> ScrapeResult:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=options.timeout)) as session:
                async with session.get(url) as resp:
                    html = await resp.text()
                    md = _html_to_md(html)
                    content = md if options.format == ScrapeFormat.MARKDOWN else _strip_tags(html)
                    title = _extract_title(html)
                    return ScrapeResult(url=url, title=title, content=content, html=html, markdown=md, status=resp.status)
        except Exception as e:
            return ScrapeResult(url=url, success=False, error=str(e), status=0)

class PlaywrightEngine(ScraperEngine):
    name = "playwright"
    quality = 20
    supports_javascript = True
    supports_screenshot = True

    async def scrape(self, url: str, options: ScrapeOptions) -> ScrapeResult:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return ScrapeResult(url=url, success=False, error="playwright not installed", status=0)
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=options.timeout * 1000)
                if options.wait_for:
                    await page.wait_for_selector(options.wait_for, timeout=options.timeout * 1000)
                html = await page.content()
                title = await page.title()
                screenshot = None
                if options.screenshot:
                    screenshot_bytes = await page.screenshot(type="png")
                    import base64
                    screenshot = base64.b64encode(screenshot_bytes).decode()
                await browser.close()
                md = _html_to_md(html)
                content = md if options.format == ScrapeFormat.MARKDOWN else _strip_tags(html)
                return ScrapeResult(url=url, title=title, content=content, html=html, markdown=md, screenshot=screenshot, status=200)
        except Exception as e:
            return ScrapeResult(url=url, success=False, error=str(e), status=0)

def _html_to_md(html: str) -> str:
    # Minimal fallback
    text = _strip_tags(html)
    return text

def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html).strip()

def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return m.group(1).strip() if m else ""
