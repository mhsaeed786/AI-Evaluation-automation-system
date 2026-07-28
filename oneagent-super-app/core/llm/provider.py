from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from enum import Enum
import json

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class LLMMessage:
    role: MessageRole
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    image_url: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"role": self.role.value, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d

@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    cost_usd: float = 0.0

CostCallback = Callable[[float], None]

class LLMProvider(ABC):
    name: str = "abstract"
    supports_tools: bool = True
    supports_vision: bool = False

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.extra = kwargs

    @abstractmethod
    async def complete(self, messages: List[LLMMessage], system: Optional[str] = None, tools: Optional[List[dict]] = None, temperature: float = 0.7, max_tokens: int = 4096, cost_callback: Optional[CostCallback] = None) -> LLMResponse:
        ...

    @abstractmethod
    async def stream(self, messages: List[LLMMessage], system: Optional[str] = None, tools: Optional[List[dict]] = None, temperature: float = 0.7, max_tokens: int = 4096) -> AsyncIterator[LLMResponse]:
        ...

    async def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError()

class ProviderRegistry:
    """Registry of LLM providers, singleton-like, mirroring Goose/Cline patterns."""
    def __init__(self):
        self._providers: Dict[str, type] = {}

    def register(self, name: str, cls: type):
        self._providers[name] = cls

    def get(self, name: str) -> type:
        if name not in self._providers:
            raise ValueError(f"Unknown provider '{name}'. Registered: {list(self._providers)}")
        return self._providers[name]

    def list(self) -> List[str]:
        return list(self._providers)

    def create(self, name: str, model: str, **kwargs) -> LLMProvider:
        cls = self.get(name)
        return cls(model=model, **kwargs)

GLOBAL_REGISTRY = ProviderRegistry()
