"""OpenAI provider adapter."""

import os
import logging
from typing import Any, Dict, List, Optional

from . import BaseProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    name = "openai"
    supports_streaming = True
    supports_tools = True

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
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
        model = model or self.config.get("default_model", "gpt-4o")

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **{k: v for k, v in kwargs.items() if k in ("tools", "response_format", "top_p")},
        )

        choice = response.choices[0]
        content = choice.message.content or ""
        usage = response.usage

        return LLMResponse(
            content=content,
            provider=self.name,
            model=model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            cost_usd=self.calculate_cost(
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            ),
            raw=response.model_dump() if hasattr(response, "model_dump") else {},
        )
