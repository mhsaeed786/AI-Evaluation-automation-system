"""Anthropic provider adapter."""

import logging
from typing import Any, Dict, List, Optional

from . import BaseProvider, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    supports_streaming = True
    supports_tools = True

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                kwargs = {"api_key": self.api_key}
                base_url = self.config.get("base_url")
                if base_url:
                    kwargs["base_url"] = base_url
                self._client = AsyncAnthropic(**kwargs)
            except ImportError:
                raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
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
        model = model or self.config.get("default_model", "claude-sonnet-4-20250514")

        system_msg = None
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                chat_messages.append(m)

        params = dict(
            model=model,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if system_msg:
            params["system"] = system_msg

        response = await client.messages.create(**params)

        content = response.content[0].text if response.content else ""
        usage = response.usage

        return LLMResponse(
            content=content,
            provider=self.name,
            model=model,
            prompt_tokens=usage.input_tokens if usage else 0,
            completion_tokens=usage.output_tokens if usage else 0,
            cost_usd=self.calculate_cost(
                usage.input_tokens if usage else 0,
                usage.output_tokens if usage else 0,
            ),
            raw={"id": response.id, "stop_reason": response.stop_reason},
        )
