"""
Base provider interface — all adapters implement this.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    raw: Optional[Dict[str, Any]] = None


class BaseProvider:
    """Interface every provider adapter must implement."""

    name: str = "base"
    supports_streaming: bool = False
    supports_tools: bool = False

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        raise NotImplementedError

    def count_tokens(self, text: str) -> int:
        return len(text) // 4  # rough estimate

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        ci = self.config.get("cost_per_1k_input", 0)
        co = self.config.get("cost_per_1k_output", 0)
        return (prompt_tokens / 1000 * ci) + (completion_tokens / 1000 * co)
