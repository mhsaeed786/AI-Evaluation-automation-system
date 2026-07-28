from __future__ import annotations
from typing import List, Optional, AsyncIterator
import json
import os
from dataclasses import dataclass

from .provider import LLMProvider, LLMMessage, LLMResponse, ToolCall, CostCallback, MessageRole, GLOBAL_REGISTRY

class GenericLLM(LLMProvider):
    """OpenAI-compatible unified provider used by GPT Researcher / OpenManus / many tools."""
    name = "generic_openai"
    supports_tools = True
    supports_vision = False

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, api_key, base_url, **kwargs)
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                import openai
            except ImportError:
                raise RuntimeError("openai package required for generic_openai provider")
            key = self.api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
            base = self.base_url or os.environ.get("OPENAI_BASE_URL")
            args = {"api_key": key}
            if base:
                args["base_url"] = base
            self.client = openai.AsyncOpenAI(**args)
        return self.client

    def _normalize_messages(self, messages: List[LLMMessage], system: Optional[str]):
        out = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages:
            out.append(m.to_dict())
        return out

    async def complete(self, messages, system=None, tools=None, temperature=0.7, max_tokens=4096, cost_callback: Optional[CostCallback]=None):
        client = self._get_client()
        params = {
            "model": self.model,
            "messages": self._normalize_messages(messages, system),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        resp = await client.chat.completions.create(**params)
        choice = resp.choices[0]
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments)))
        usage = dict(resp.usage) if resp.usage else {}
        cost = self._estimate_cost(usage)
        if cost_callback:
            cost_callback(cost)
        return LLMResponse(content=choice.message.content or "", tool_calls=tool_calls, model=self.model, usage=usage, finish_reason=choice.finish_reason, cost_usd=cost)

    async def stream(self, messages, system=None, tools=None, temperature=0.7, max_tokens=4096):
        client = self._get_client()
        params = {
            "model": self.model,
            "messages": self._normalize_messages(messages, system),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            params["tools"] = tools
        acc = ""
        async for chunk in await client.chat.completions.create(**params):
            delta = chunk.choices[0].delta
            if delta.content:
                acc += delta.content
                yield LLMResponse(content=acc, model=self.model)

    def _estimate_cost(self, usage: dict) -> float:
        # Very rough default cost estimator
        inp = usage.get("prompt_tokens", 0)
        out = usage.get("completion_tokens", 0)
        return round((inp * 1.5e-6) + (out * 6e-6), 6)

class GeminiLLM(GenericLLM):
    """Gemini via OpenAI-compatible endpoint."""
    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash", api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        base = base_url or "https://generativelanguage.googleapis.com/v1beta/openai/"
        super().__init__(model, key, base, **kwargs)

class OllamaLLM(GenericLLM):
    name = "ollama"

    def __init__(self, model: str = "llama3.1", api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        base = base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
        super().__init__(model, "ollama", base, **kwargs)

class AnthropicLLM(GenericLLM):
    name = "anthropic"

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        base = base_url or "https://api.anthropic.com/v1/"
        super().__init__(model, key, base, **kwargs)

# Register defaults
GLOBAL_REGISTRY.register("openai", GenericLLM)
GLOBAL_REGISTRY.register("gemini", GeminiLLM)
GLOBAL_REGISTRY.register("ollama", OllamaLLM)
GLOBAL_REGISTRY.register("anthropic", AnthropicLLM)
