"""Multi-API provider chat clients.

Uniform client interface over three API dialects so the builtin engine and
scorers stay agnostic to the provider's wire format:

  * openai    -> OpenAICompatClient = the existing OllamaCloudClient (any
                 OpenAI-compatible endpoint: OpenAI, Ollama, Groq, OpenRouter,
                 Cerebras, HF, Together, Mistral, ... plus Google Gemini via
                 its OpenAI-compat URL).
  * anthropic -> AnthropicClient (Anthropic Messages API; `anthropic` SDK).
  * gemini    -> GeminiClient (Google Gemini API; `google-genai` SDK).

``make_client(provider, cfg)`` picks the right adapter from
``config.PROVIDERS``. The Anthropic/Gemini SDKs are OPTIONAL: if missing, the
adapter import fails softly and the runner skips that provider with a clear
note (or, for Gemini, transparently falls back to Google's OpenAI-compat URL,
which needs no extra SDK).

Where an adapter cannot expose next-token logprobs (Anthropic, Gemini), MCQ
scoring transparently falls back to generate-and-parse, because
``answer_letter_logprob`` returns ``present=False``.
"""
from __future__ import annotations

import logging
from typing import Sequence

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .scoring_types import LetterScores

log = logging.getLogger("ollama_eval.clients")


def _retry(max_attempts: int = 6, multiplier: float = 2.0, max_wait: float = 60.0):
    return retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=multiplier, max=max_wait),
        stop=stop_after_attempt(max_attempts),
        reraise=True,
    )


# ======================================================================
# Anthropic (Claude) — Messages API
# ======================================================================
class AnthropicClient:
    api_type = "anthropic"

    def __init__(self, base_url, api_key, *, timeout=180.0, seed=1234, temperature=0.0, org_id=""):
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "The `anthropic` SDK is required for this provider: pip install anthropic"
            ) from e
        self.base_url = base_url or "https://api.anthropic.com"
        self.api_key = api_key
        self.seed = seed
        self.temperature = temperature
        kwargs = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = anthropic.Anthropic(**kwargs)

    @_retry()
    def list_models(self) -> list[str]:
        try:
            data = self.client.models.list()
            ids = [getattr(m, "id", "") for m in (getattr(data, "data", None) or [])]
            return [i for i in ids if i]
        except Exception:
            return ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest",
                    "claude-3-7-sonnet-latest", "claude-sonnet-4-20250514",
                    "claude-opus-4-20250514", "claude-3-opus-latest"]

    @staticmethod
    def _split_system(messages: Sequence[dict]):
        sys_msgs = [str(m["content"]) for m in messages if m.get("role") == "system"]
        rest = [m for m in messages if m.get("role") != "system"]
        system = "\n\n".join(sys_msgs) if sys_msgs else None
        norm = []
        for m in rest:
            c = m.get("content", "")
            norm.append({"role": m.get("role", "user"),
                         "content": c if isinstance(c, str) else str(c)})
        return system, norm

    @_retry()
    def _create(self, *, model, messages, temperature, max_tokens, stop=None):
        system, msgs = self._split_system(messages)
        kw = {"model": model, "messages": msgs, "max_tokens": max_tokens,
              "temperature": self.temperature if temperature is None else temperature}
        if system:
            kw["system"] = system
        if stop:
            kw["stop_sequences"] = list(stop)
        return self.client.messages.create(**kw)

    def chat_text(self, *, model, messages, temperature=None, max_tokens=1024,
                  stop=None, **kw) -> str:
        resp = self._create(model=model, messages=messages, temperature=temperature,
                            max_tokens=max_tokens, stop=stop)
        parts = getattr(resp, "content", []) or []
        texts = [getattr(b, "text", "") for b in parts if getattr(b, "text", None)]
        return "\n".join(texts).strip()

    def answer_letter_logprob(self, *, model, prompt_messages,
                              letters=("A", "B", "C", "D"), top_logprobs=5) -> LetterScores:
        # Anthropic Messages API does not expose top-k token logprobs.
        return LetterScores(scores={}, present=False)

    def answer_letter_generate(self, *, model, prompt_messages,
                               letters=("A", "B", "C", "D"), max_tokens=4) -> str | None:
        text = (self.chat_text(model=model, messages=prompt_messages,
                               max_tokens=max_tokens, temperature=0.0) or "").upper()
        for ch in text:
            if ch in letters:
                return ch
        return None


# ======================================================================
# Google Gemini — native API (google-genai SDK)
# ======================================================================
class GeminiClient:
    api_type = "gemini"

    def __init__(self, base_url, api_key, *, timeout=180.0, seed=1234, temperature=0.0, org_id=""):
        try:
            from google import genai  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "The `google-genai` SDK is required for native Gemini: pip install google-genai"
            ) from e
        self.base_url = base_url or "https://generativelanguage.googleapis.com/v1beta"
        self.api_key = api_key
        self.seed = seed
        self.temperature = temperature
        self.timeout = timeout
        http_options = ({"base_url": base_url} if base_url else None)
        self.client = genai.Client(api_key=api_key, http_options=http_options)

    @staticmethod
    def _model(model: str) -> str:
        return model.split("/", 1)[-1] if model.startswith("models/") else model

    @_retry()
    def list_models(self) -> list[str]:
        try:
            out = []
            for m in self.client.models.list():
                name = getattr(m, "name", "") or ""
                if name:
                    out.append(self._model(name))
            return out or ["gemini-2.0-flash", "gemini-2.5-flash",
                           "gemini-2.5-pro", "gemini-1.5-pro"]
        except Exception:
            return ["gemini-2.0-flash", "gemini-2.5-flash",
                    "gemini-2.5-pro", "gemini-1.5-pro"]

    def _contents(self, messages: Sequence[dict]):
        system, msgs = AnthropicClient._split_system(messages)
        contents = []
        for m in msgs:
            role = "user" if m.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": str(m.get("content", ""))}]})
        return contents, system

    @_retry()
    def _generate(self, *, model, messages, temperature, max_tokens, stop=None):
        from google.genai import types  # type: ignore
        contents, system = self._contents(messages)
        gen_cfg = {"temperature": self.temperature if temperature is None else temperature,
                   "max_output_tokens": max_tokens}
        if stop:
            gen_cfg["stop_sequences"] = list(stop)
        if system:
            gen_cfg["system_instruction"] = system
        return self.client.models.generate_content(
            model=self._model(model), contents=contents,
            config=types.GenerateContentConfig(**gen_cfg))

    def chat_text(self, *, model, messages, temperature=None, max_tokens=1024,
                  stop=None, **kw) -> str:
        try:
            resp = self._generate(model=model, messages=messages, temperature=temperature,
                                  max_tokens=max_tokens, stop=stop)
            return (getattr(resp, "text", "") or "").strip()
        except Exception as e:  # noqa: BLE001
            log.warning("gemini chat_text error: %s", e)
            return ""

    def answer_letter_logprob(self, *, model, prompt_messages,
                              letters=("A", "B", "C", "D"), top_logprobs=5) -> LetterScores:
        # Gemini top-token logprob parsing is fragile across SDK versions; rely
        # on the generate-and-parse fallback for MCQ.
        return LetterScores(scores={}, present=False)

    def answer_letter_generate(self, *, model, prompt_messages,
                               letters=("A", "B", "C", "D"), max_tokens=4) -> str | None:
        text = (self.chat_text(model=model, messages=prompt_messages,
                               max_tokens=max_tokens, temperature=0.0) or "").upper()
        for ch in text:
            if ch in letters:
                return ch
        return None


# ======================================================================
# Factory
# ======================================================================
def make_client(provider: str, cfg):
    """Return a chat client for ``provider`` based on its configured api_type.

    Falls back to the OpenAI-compatible client when a dialect-specific SDK is
    unavailable, so a provider still runs if it exposes an OpenAI-compat surface
    (notably Gemini, via Google's /v1beta/openai endpoint).
    """
    from .config import provider_api_type, get_provider_credentials
    from .ollama_client import OllamaCloudClient

    api_type = provider_api_type(provider)
    url, key = get_provider_credentials(provider)
    common = dict(timeout=cfg.sampling.timeout, seed=cfg.sampling.seed,
                  temperature=cfg.sampling.temperature, org_id=cfg.org_id)

    if api_type == "anthropic":
        try:
            return AnthropicClient(url, key, **common)
        except ImportError:
            log.warning("anthropic SDK missing for '%s'; skipping native path", provider)
            raise
    if api_type == "gemini":
        try:
            return GeminiClient(url, key, **common)
        except ImportError:
            log.warning("google-genai missing for '%s'; using Gemini OpenAI-compat URL", provider)
            compat = (url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/") + "/openai"
            return OllamaCloudClient(compat, key, **common)

    # default: openai-compatible
    return OllamaCloudClient(url, key, **common)
