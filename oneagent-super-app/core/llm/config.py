from __future__ import annotations
from typing import Optional, Tuple
import os
from dataclasses import dataclass

from .provider import GLOBAL_REGISTRY

@dataclass
class LLMConfig:
    fast: str = "gemini:gemini-2.5-flash"
    smart: str = "gemini:gemini-2.5-pro"
    strategic: str = "gemini:gemini-2.5-pro"
    embedding: str = "gemini:gemini-embedding-exp-03-07"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class LLMResolver:
    """Parse 'provider:model' strings used by GPT Researcher and Cline."""
    @staticmethod
    def parse(descriptor: str) -> Tuple[str, str]:
        if ":" in descriptor:
            provider, model = descriptor.split(":", 1)
            return provider, model
        return "gemini", descriptor

    @staticmethod
    def create(descriptor: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        provider, model = LLMResolver.parse(descriptor)
        env_key = os.environ.get("GEMINI_API_KEY") if provider == "gemini" else os.environ.get("OPENAI_API_KEY")
        return GLOBAL_REGISTRY.create(provider, model, api_key=api_key or env_key, base_url=base_url)
