"""Ollama (local) provider adapter — free, offline inference."""

import logging
from typing import Any, Dict, List, Optional

from . import BaseProvider, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    name = "ollama"
    supports_streaming = True
    supports_tools = False

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None
        self.host = config.get("base_url", "http://localhost:11434")

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key="ollama",
                    base_url=f"{self.host}/v1",
                )
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client

    def is_available(self) -> bool:
        import httpx
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        client = self._get_client()
        model = model or self.config.get("default_model", "llama3.1:8b")

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
            provider=self.name,
            model=model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            cost_usd=0.0,
            raw=response.model_dump() if hasattr(response, "model_dump") else {},
        )
