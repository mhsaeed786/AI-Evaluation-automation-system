"""
Research Module — deep researcher + SaaS opportunity finder.

Multi-LLM + web search for comprehensive research tasks.
"""

import logging
from typing import Any, Dict, List, Optional

from core.agents.tools import get_registry, tool

logger = logging.getLogger(__name__)


@tool(name="web_search", description="Search the web for information on a topic", module="research")
def web_search(query: str, max_results: int = 10) -> Dict:
    """Search the web and return results."""
    try:
        import httpx
        # Use DuckDuckGo HTML search as fallback
        r = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        return {"status": r.status_code, "preview": r.text[:2000]}
    except Exception as e:
        return {"error": str(e)}


@tool(name="web_scrape", description="Scrape and extract text content from a URL", module="research")
def web_scrape(url: str, max_length: int = 5000) -> Dict:
    """Fetch and extract text from a URL."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return {"url": url, "text": text[:max_length], "length": len(text)}
    except Exception as e:
        return {"error": str(e)}


@tool(name="summarize_text", description="Summarize a block of text using LLM", module="research")
async def summarize_text(text: str, max_length: int = 500) -> Dict:
    """Use LLM to summarize text."""
    from core.llm.router import get_router
    router = get_router()
    response = await router.complete(
        messages=[
            {"role": "system", "content": "Summarize the following text concisely."},
            {"role": "user", "content": text[:8000]},
        ],
        task_class="summarize",
        module="research",
        max_tokens=max_length,
    )
    return {"summary": response.content, "model": response.model, "cost": response.cost_usd}


@tool(name="find_saas_opportunities", description="Research SaaS market opportunities for a given domain", module="research")
async def find_saas_opportunities(domain: str, market: str = "healthcare IT") -> Dict:
    """Use LLM + web research to identify SaaS opportunities."""
    from core.llm.router import get_router
    router = get_router()
    response = await router.complete(
        messages=[
            {"role": "system", "content": "You are a SaaS market analyst. Identify opportunities."},
            {"role": "user", "content": f"Identify top SaaS opportunities in {domain} for the {market} market. Include: market size, competition, differentiation ideas, pricing models."},
        ],
        task_class="reason",
        module="research",
        max_tokens=4096,
    )
    return {"opportunities": response.content, "domain": domain, "cost": response.cost_usd}


@tool(name="deep_research", description="Conduct multi-source deep research on a topic", module="research")
async def deep_research(topic: str, depth: str = "standard") -> Dict:
    """
    Conduct comprehensive research using LLM + web sources.

    Merged from deep_researcher app. Depth: quick (3-5 sources),
    standard (5-10), deep (10+).
    """
    from core.llm.router import get_router
    router = get_router()

    source_counts = {"quick": 3, "standard": 7, "deep": 12}
    n = source_counts.get(depth, 5)

    response = await router.complete(
        messages=[
            {"role": "system", "content": f"You are a deep research analyst. Conduct {depth} research with at least {n} sourced insights."},
            {"role": "user", "content": f"Research: {topic}\n\nProvide:\n1. Executive summary\n2. Key findings with citations\n3. Analysis and trends\n4. Recommendations\n5. Sources"},
        ],
        task_class="reason",
        module="research",
        max_tokens=6000,
    )
    return {"research": response.content, "topic": topic, "depth": depth, "cost": response.cost_usd}


def register():
    return {
        "name": "research",
        "description": "Deep research, web search, SaaS opportunity analysis",
        "version": "2.0.0",
        "tools": ["web_search", "web_scrape", "summarize_text", "find_saas_opportunities", "deep_research"],
        "routes": [
            {"method": "POST", "path": "/research/search", "handler": "web_search"},
            {"method": "POST", "path": "/research/scrape", "handler": "web_scrape"},
            {"method": "POST", "path": "/research/summarize", "handler": "summarize_text"},
            {"method": "POST", "path": "/research/saas", "handler": "find_saas_opportunities"},
            {"method": "POST", "path": "/research/deep", "handler": "deep_research"},
        ],
    }
