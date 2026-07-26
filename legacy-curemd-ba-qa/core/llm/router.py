"""
LLM Router — the single gateway for all LLM calls in OneAgent.

Routes to the cheapest model that works based on ranking.yaml.
Supports per-task-class, per-module, and per-call overrides.
Cache + budget are enforced automatically.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cache import LLMCache, get_cache
from .budget import BudgetTracker, BudgetExceeded, get_budget_tracker
from .providers import BaseProvider, LLMResponse
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.gemini_provider import GeminiProvider
from .providers.openai_compat_provider import OpenAICompatProvider
from .providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

RANKING_PATH = Path(__file__).parent / "ranking.yaml"

# Map provider keys to (adapter_class, config_from_settings)
PROVIDER_MAP = {
    "openai": (OpenAIProvider, "openai"),
    "anthropic": (AnthropicProvider, "anthropic"),
    "gemini": (GeminiProvider, "gemini"),
    "deepseek": (OpenAICompatProvider, "deepseek"),
    "groq": (OpenAICompatProvider, "groq"),
    "mistral": (OpenAICompatProvider, "mistral"),
    "cohere": (OpenAICompatProvider, "cohere"),
    "ollama": (OllamaProvider, "ollama"),
}


class LLMRouter:
    """Unified LLM gateway with ranking, caching, and budget enforcement."""

    def __init__(
        self,
        ranking_path: Optional[str] = None,
        cache: Optional[LLMCache] = None,
        budget: Optional[BudgetTracker] = None,
    ):
        self._ranking_path = Path(ranking_path) if ranking_path else RANKING_PATH
        self._rankings = self._load_rankings()
        self._cache = cache or get_cache()
        self._budget = budget or get_budget_tracker()
        self._providers: Dict[str, BaseProvider] = {}
        self._init_providers()

    def _load_rankings(self) -> dict:
        if self._ranking_path.exists():
            with open(self._ranking_path) as f:
                return yaml.safe_load(f)
        return {"defaults": [], "task_classes": {}}

    def _init_providers(self):
        from config.settings import get_settings
        settings = get_settings()

        for key, (cls, cfg_key) in PROVIDER_MAP.items():
            cfg = settings.llm_providers.get(cfg_key)
            if not cfg:
                continue
            provider_config = {
                "api_key": os.getenv(cfg.api_key_env, ""),
                "default_model": cfg.default_model,
                "cost_per_1k_input": cfg.cost_per_1k_input,
                "cost_per_1k_output": cfg.cost_per_1k_output,
                "base_url": cfg.base_url,
                "provider_name": key,
            }
            provider = cls(provider_config)
            self._providers[key] = provider

    def get_ranked_models(self, task_class: Optional[str] = None) -> List[Dict]:
        """Return model list in preference order for a task class."""
        if task_class and task_class in self._rankings.get("task_classes", {}):
            return self._rankings["task_classes"][task_class]
        return self._rankings.get("defaults", [])

    async def complete(
        self,
        messages: List[Dict[str, str]],
        task_class: Optional[str] = None,
        module: Optional[str] = None,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_cache: bool = True,
        **kwargs,
    ) -> LLMResponse:
        """
        Route an LLM call through the best available provider.

        Args:
            messages: Chat messages list
            task_class: Type of task (classify, reason, code, etc.) for ranking
            module: Calling module name for budget tracking
            provider_override: Force a specific provider
            model_override: Force a specific model
            temperature: Sampling temperature
            max_tokens: Max output tokens
            use_cache: Whether to check/store in cache
        """
        self._budget.check_budget(task_class=task_class, module=module)

        # If caller overrides both provider and model, go direct
        if provider_override and model_override:
            return await self._call_provider(
                provider_override, model_override, messages,
                task_class, module, temperature, max_tokens, use_cache, **kwargs,
            )

        # Try ranked models in order
        ranked = self.get_ranked_models(task_class)
        last_error = None

        if provider_override:
            ranked = [r for r in ranked if r["provider"] == provider_override]
            if not ranked:
                ranked = [{"provider": provider_override, "model": model_override or ""}]

        for entry in ranked:
            prov_key = entry["provider"]
            model = model_override or entry.get("model")

            provider = self._providers.get(prov_key)
            if not provider or not provider.is_available():
                continue

            try:
                return await self._call_provider(
                    prov_key, model, messages,
                    task_class, module, temperature, max_tokens, use_cache, **kwargs,
                )
            except Exception as e:
                logger.warning(f"Provider {prov_key}/{model} failed: {e}")
                last_error = e
                continue

        raise RuntimeError(f"All providers failed for task '{task_class}'. Last error: {last_error}")

    async def _call_provider(
        self, provider_key: str, model: str, messages: list,
        task_class: Optional[str], module: Optional[str],
        temperature: float, max_tokens: int, use_cache: bool,
        **kwargs,
    ) -> LLMResponse:
        provider = self._providers[provider_key]
        if not provider or not provider.is_available():
            raise RuntimeError(f"Provider '{provider_key}' not available")

        # Check cache
        if use_cache:
            cached = self._cache.get(messages, model, temperature=temperature, max_tokens=max_tokens)
            if cached:
                self._budget.log_call(
                    provider=provider_key, model=model,
                    prompt_tokens=0, completion_tokens=0, cost_usd=0.0,
                    task_class=task_class, module=module, cached=True,
                )
                return LLMResponse(
                    content=cached["content"],
                    provider=provider_key,
                    model=model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    cost_usd=0.0,
                )

        response = await provider.complete(
            messages=messages, model=model,
            temperature=temperature, max_tokens=max_tokens, **kwargs,
        )

        # Log and cache
        self._budget.log_call(
            provider=provider_key, model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost_usd=response.cost_usd,
            task_class=task_class, module=module,
        )

        if use_cache:
            self._cache.put(
                messages=messages, model=response.model,
                response={"content": response.content},
                provider=provider_key,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                temperature=temperature, max_tokens=max_tokens,
            )

        return response

    def list_available(self) -> List[Dict[str, Any]]:
        """List all providers and their availability status."""
        result = []
        for key, provider in self._providers.items():
            result.append({
                "provider": key,
                "model": provider.config.get("default_model", ""),
                "available": provider.is_available(),
                "cost_per_1k_input": provider.config.get("cost_per_1k_input", 0),
                "cost_per_1k_output": provider.config.get("cost_per_1k_output", 0),
            })
        return result

    def get_daily_spend(self) -> Dict:
        return self._budget.get_daily_summary()

    def get_cache_stats(self) -> Dict:
        return self._cache.stats()


_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
