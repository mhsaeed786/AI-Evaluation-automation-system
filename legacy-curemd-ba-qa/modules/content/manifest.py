"""
Content Module — blog, SEO, social media pipeline.

NEW module — first non-trivial self-authored module candidate.
Handles multi-platform content generation, SEO optimization,
and social media scheduling.
"""

import logging
from typing import Any, Dict, List

from core.agents.tools import get_registry, tool

logger = logging.getLogger(__name__)


@tool(name="generate_blog_post", description="Generate a full blog post with SEO optimization", module="content")
async def generate_blog_post(topic: str, tone: str = "professional", length: int = 2000, keywords: str = "") -> Dict:
    """Generate a complete blog post with SEO metadata."""
    from core.llm.router import get_router
    router = get_router()

    kw_instruction = f"\nTarget keywords: {keywords}" if keywords else ""
    response = await router.complete(
        messages=[
            {"role": "system", "content": f"You are a professional blog writer. Write in {tone} tone. Include: title, meta description, headers, body, tags.{kw_instruction}"},
            {"role": "user", "content": f"Write a {length}-word blog post about: {topic}"},
        ],
        task_class="long_context",
        module="content",
        max_tokens=6000,
    )
    return {"content": response.content, "topic": topic, "model": response.model, "cost": response.cost_usd}


@tool(name="generate_social_posts", description="Generate social media posts for multiple platforms", module="content")
async def generate_social_posts(topic: str, platforms: str = "linkedin,twitter") -> Dict:
    """Generate platform-specific social media posts."""
    from core.llm.router import get_router
    router = get_router()

    platform_list = [p.strip() for p in platforms.split(",")]
    response = await router.complete(
        messages=[
            {"role": "system", "content": f"Generate social media posts for: {', '.join(platform_list)}. Format each with a clear platform header."},
            {"role": "user", "content": f"Create posts about: {topic}"},
        ],
        task_class="reason",
        module="content",
    )
    return {"posts": response.content, "platforms": platform_list, "cost": response.cost_usd}


@tool(name="seo_analyze", description="Analyze text for SEO optimization suggestions", module="content")
async def seo_analyze(text: str, target_keywords: str = "") -> Dict:
    """Analyze content for SEO and provide improvement suggestions."""
    from core.llm.router import get_router
    router = get_router()

    response = await router.complete(
        messages=[
            {"role": "system", "content": "You are an SEO analyst. Analyze the content and provide: keyword density, readability score, meta description suggestion, heading structure, internal linking opportunities, and improvement suggestions."},
            {"role": "user", "content": f"Analyze this content for SEO (target keywords: {target_keywords or 'auto-detect'}):\n\n{text[:6000]}"},
        ],
        task_class="reason",
        module="content",
    )
    return {"analysis": response.content, "cost": response.cost_usd}


@tool(name="generate_docs", description="Generate technical documentation from code or specs", module="content")
async def generate_docs(source: str, doc_type: str = "api") -> Dict:
    """Generate technical documentation."""
    from core.llm.router import get_router
    router = get_router()

    response = await router.complete(
        messages=[
            {"role": "system", "content": f"Generate {doc_type} documentation. Use clear structure, code examples, and tables where appropriate."},
            {"role": "user", "content": f"Generate documentation for:\n{source[:8000]}"},
        ],
        task_class="code",
        module="content",
        max_tokens=4096,
    )
    return {"docs": response.content, "type": doc_type, "cost": response.cost_usd}


def register():
    return {
        "name": "content",
        "description": "Content generation — blog posts, social media, SEO analysis, documentation",
        "version": "1.0.0",
        "tools": ["generate_blog_post", "generate_social_posts", "seo_analyze", "generate_docs"],
        "routes": [
            {"method": "POST", "path": "/content/blog", "handler": "generate_blog_post"},
            {"method": "POST", "path": "/content/social", "handler": "generate_social_posts"},
            {"method": "POST", "path": "/content/seo", "handler": "seo_analyze"},
            {"method": "POST", "path": "/content/docs", "handler": "generate_docs"},
        ],
    }
