"""
OpenAI-compatible provider adapter.
Works with DeepSeek, Groq, Mistral, Cohere, and any OpenAI-compatible API.
"""

import logging
from typing import Any, Dict, List, Optional

from . import BaseProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAICompatProvider(BaseProvider):
    """Generic provider for any OpenAI-compatible API (DeepSeek, Groq, Mistral, Cohere, etc.)."""

    name = "openai_compat"
    supports_streaming = True
    supports_tools = True

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None
        self.provider_name = config.get("provider_name", self.name)
        self.base_url = config.get("base_url")

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = AsyncOpenAI(**kwargs)
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        client = self._get_client()
        model = model or self.config.get("default_model", "")

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        content = choice.message.content or ""
        usage = response.usage

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            cost_usd=self.calculate_cost(
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            ),
            raw=response.model_dump() if hasattr(response, "model_dump") else {},
        )
