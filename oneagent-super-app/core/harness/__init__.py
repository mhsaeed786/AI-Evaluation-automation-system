"""
OneAgent Core — Pluggable Agent Harness
Inspired by OpenClaw's harness abstraction pattern.

The harness separates the model loop executor from the surrounding orchestration.
Each model family (Gemini, OpenAI, Anthropic, Ollama) can have its own native loop
while sharing context assembly, tool policy, and delivery.

Selection priority:
  1. Session-pinned harness ID
  2. ONEAGENT_HARNESS env var
  3. Auto-selection (ask registered harnesses)
  4. Default fallback
"""

import os
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class HarnessType(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class HarnessContext:
    """Context passed to a harness for execution."""
    prompt: str
    system_instruction: str = ""
    tools: List[dict] = field(default_factory=list)
    history: List[dict] = field(default_factory=list)
    model: str = ""
    task_class: str = "reason"  # classify, extract, reason, code, long_context, vision
    max_tokens: int = 4096
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HarnessResult:
    """Result from a harness execution."""
    text: str = ""
    tool_calls: List[dict] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=dict)
    model_used: str = ""
    finish_reason: str = "stop"
    latency_ms: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentHarness(ABC):
    """Abstract base class for agent harnesses.

    A harness implements the actual model loop (call model, parse response,
    execute tools, repeat). The surrounding orchestrator handles:
    - Session management
    - Context assembly
    - Tool policy
    - Delivery to user
    """

    @property
    @abstractmethod
    def harness_id(self) -> str:
        """Unique identifier for this harness."""
        pass

    @property
    @abstractmethod
    def harness_type(self) -> HarnessType:
        """Type of this harness."""
        pass

    @abstractmethod
    async def can_handle(self, context: HarnessContext) -> bool:
        """Check if this harness can handle the given context."""
        pass

    @abstractmethod
    async def execute(self, context: HarnessContext,
                     tool_executor: Callable = None) -> HarnessResult:
        """Execute the agent loop with the given context.

        Args:
            context: The execution context
            tool_executor: Optional callback to execute tool calls.
                Signature: async def tool_executor(tool_name: str, args: dict) -> dict
        """
        pass

    @abstractmethod
    async def stream(self, context: HarnessContext,
                     tool_executor: Callable = None) -> Any:
        """Stream the agent loop execution.

        Yields events: {"type": "text", "content": "..."},
                        {"type": "tool_call", "name": "...", "args": {...}},
                        {"type": "tool_result", "result": {...}},
                        {"type": "done", "result": HarnessResult}
        """
        pass


class GeminiHarness(AgentHarness):
    """Gemini API harness using @google/genai."""

    def __init__(self, api_key: str = None):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None

    @property
    def harness_id(self) -> str:
        return "gemini"

    @property
    def harness_type(self) -> HarnessType:
        return HarnessType.GEMINI

    async def can_handle(self, context: HarnessContext) -> bool:
        return bool(self._api_key and self._api_key != "MY_GEMINI_API_KEY")

    def _get_client(self):
        if self._client is None:
            # Lazy import — only load when actually used
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def execute(self, context: HarnessContext,
                     tool_executor: Callable = None) -> HarnessResult:
        import time
        start = time.time()

        try:
            client = self._get_client()
            model = context.model or "gemini-2.0-flash"

            config = {}
            if context.system_instruction:
                config["system_instruction"] = context.system_instruction
            if context.max_tokens:
                config["max_output_tokens"] = context.max_tokens
            if context.temperature is not None:
                config["temperature"] = context.temperature

            # Build conversation history
            contents = context.history + [{"role": "user", "parts": [context.prompt]}]

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=contents,
                config=config if config else None,
            )

            text = response.text or ""
            usage = {}
            if hasattr(response, "usage_metadata"):
                usage = {
                    "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                }

            return HarnessResult(
                text=text,
                usage=usage,
                model_used=model,
                latency_ms=int((time.time() - start) * 1000),
            )
        except Exception as e:
            return HarnessResult(error=str(e), latency_ms=int((time.time() - start) * 1000))

    async def stream(self, context: HarnessContext,
                     tool_executor: Callable = None) -> Any:
        result = await self.execute(context, tool_executor)
        yield {"type": "text", "content": result.text}
        yield {"type": "done", "result": result}


class OllamaHarness(AgentHarness):
    """Local Ollama harness for on-device models."""

    def __init__(self, host: str = "http://localhost:11434"):
        self._host = host

    @property
    def harness_id(self) -> str:
        return "ollama"

    @property
    def harness_type(self) -> HarnessType:
        return HarnessType.OLLAMA

    async def can_handle(self, context: HarnessContext) -> bool:
        # Check if Ollama is running
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._host}/api/tags", timeout=2) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def execute(self, context: HarnessContext,
                     tool_executor: Callable = None) -> HarnessResult:
        import time
        start = time.time()
        model = context.model or "llama3.2"

        try:
            import aiohttp
            payload = {
                "model": model,
                "prompt": context.prompt,
                "stream": False,
                "options": {
                    "temperature": context.temperature,
                    "num_predict": context.max_tokens,
                },
            }
            if context.system_instruction:
                payload["system"] = context.system_instruction

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self._host}/api/generate", json=payload) as resp:
                    data = await resp.json()
                    return HarnessResult(
                        text=data.get("response", ""),
                        usage={
                            "input_tokens": data.get("prompt_eval_count", 0),
                            "output_tokens": data.get("eval_count", 0),
                        },
                        model_used=model,
                        latency_ms=int((time.time() - start) * 1000),
                    )
        except Exception as e:
            return HarnessResult(error=str(e), latency_ms=int((time.time() - start) * 1000))

    async def stream(self, context: HarnessContext,
                     tool_executor: Callable = None) -> Any:
        # TODO: Implement streaming for Ollama
        result = await self.execute(context, tool_executor)
        yield {"type": "text", "content": result.text}
        yield {"type": "done", "result": result}


class HarnessRegistry:
    """Registry for agent harnesses with selection logic."""

    def __init__(self):
        self._harnesses: Dict[str, AgentHarness] = {}
        self._default_harness_id: Optional[str] = None

    def register(self, harness: AgentHarness) -> None:
        """Register a harness."""
        self._harnesses[harness.harness_id] = harness
        if self._default_harness_id is None:
            self._default_harness_id = harness.harness_id

    def get(self, harness_id: str) -> Optional[AgentHarness]:
        """Get a harness by ID."""
        return self._harnesses.get(harness_id)

    def list_harnesses(self) -> List[dict]:
        """List all registered harnesses."""
        return [
            {"id": h.harness_id, "type": h.harness_type.value}
            for h in self._harnesses.values()
        ]

    async def select(self, context: HarnessContext,
                     preferred_id: str = None) -> AgentHarness:
        """Select the best harness for the given context.

        Priority:
        1. preferred_id (session-pinned or explicit)
        2. ONEAGENT_HARNESS env var
        3. Auto-selection (ask each harness if it can handle)
        4. Default fallback
        """
        # 1. Explicit preference
        if preferred_id and preferred_id in self._harnesses:
            return self._harnesses[preferred_id]

        # 2. Environment variable
        env_harness = os.environ.get("ONEAGENT_HARNESS")
        if env_harness and env_harness in self._harnesses:
            return self._harnesses[env_harness]

        # 3. Auto-selection — ask each harness
        for harness in self._harnesses.values():
            if await harness.can_handle(context):
                return harness

        # 4. Default fallback
        if self._default_harness_id:
            return self._harnesses[self._default_harness_id]

        raise RuntimeError("No harness available")


def create_default_registry() -> HarnessRegistry:
    """Create a harness registry with default harnesses."""
    registry = HarnessRegistry()

    # Register Gemini if API key is available
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and gemini_key != "MY_GEMINI_API_KEY":
        registry.register(GeminiHarness(api_key=gemini_key))

    # Register Ollama (will check availability at runtime)
    registry.register(OllamaHarness())

    return registry