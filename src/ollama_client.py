"""OpenAI-compatible client wrapper for Ollama Cloud.

Ollama Cloud exposes an OpenAI-compatible REST surface. We drive it through
the official ``openai`` SDK (which speaks that protocol exactly), wrapping it
with:

  * deterministic sampling defaults (seed=1234, temperature=0) so runs are
    reproducible and comparable across models,
  * exponential-backoff retries on rate-limit / transient server errors,
  * a ``answer_letter_logprob`` helper that returns the log-probability the
    model assigns to each candidate answer token â€” the canonical way to score
    multiple-choice benchmarks against a chat endpoint,
  * graceful degradation when the endpoint does not return ``top_logprobs``
    (falls back to generating + parsing an answer letter).

Note: :class:`~src.scoring_types.LetterScores` lives in its own dependency-free
module so the scorer layer and its offline self-test can import it without the
``openai`` / ``tenacity`` SDKs; it is re-exported here for convenience.
"""
from __future__ import annotations

import logging
from typing import Sequence

from .scoring_types import LetterScores
from openai import OpenAI
from openai import (
    APIError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
    APIConnectionError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger("ollama_eval.client")

# Transient errors worth retrying with backoff.
_RETRYABLE = (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)


def _retry_policy(max_attempts: int = 6, multiplier: float = 2.0, max_wait: float = 60.0):
    return retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=multiplier, max=max_wait),
        stop=stop_after_attempt(max_attempts),
        reraise=True,
    )


class OllamaCloudClient:
    """Thin, hardened wrapper over ``openai.OpenAI`` targeting Ollama Cloud."""

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0,
                 seed: int = 1234, temperature: float = 0.0, org_id: str = ""):
        self.base_url = base_url
        self.seed = seed
        self.temperature = temperature
        kwargs = {"base_url": base_url, "api_key": api_key, "timeout": timeout}
        if org_id:
            kwargs["default_headers"] = {"OpenAI-Organization": org_id}
        self.client = OpenAI(**kwargs)

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------
    @_retry_policy()
    def list_models(self) -> list[str]:
        """Return the list of model ids available to this key."""
        resp = self.client.models.list()
        data = resp.data or []
        return [m.id for m in data]

    @_retry_policy()
    def ping(self) -> bool:
        try:
            self.client.models.list()
            return True
        except APIError:
            return False

    # ------------------------------------------------------------------
    # Chat completions
    # ------------------------------------------------------------------
    @_retry_policy()
    def chat(self, *, model: str, messages: Sequence[dict], temperature: float | None = None,
             max_tokens: int = 1024, seed: int | None = None, stop: Sequence[str] | None = None,
             logprobs: bool = False, top_logprobs: int | None = None,
             response_format: dict | None = None, extra_body: dict | None = None):
        """Single chat completion. Returns the raw SDK response object."""
        params: dict = {
            "model": model,
            "messages": list(messages),
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens,
            "seed": self.seed if seed is None else seed,
        }
        if stop:
            params["stop"] = list(stop)
        if logprobs:
            params["logprobs"] = True
            params["top_logprobs"] = min(top_logprobs or 5, 5)
        if response_format:
            params["response_format"] = response_format
        if extra_body:
            params["extra_body"] = extra_body
        return self.client.chat.completions.create(**params)

    # Convenience: return just the assistant text.
    def chat_text(self, *, model: str, messages: Sequence[dict], **kw) -> str:
        resp = self.chat(model=model, messages=messages, **kw)
        return (resp.choices[0].message.content or "").strip()

    # ------------------------------------------------------------------
    # Text completions (for the /v1/completions loglikelihood path)
    # ------------------------------------------------------------------
    @_retry_policy()
    def complete(self, *, model: str, prompt: str, temperature: float | None = None,
                 max_tokens: int = 1, seed: int | None = None, echo: bool = False,
                 logprobs: int | None = None, stop: Sequence[str] | None = None):
        params: dict = {
            "model": model,
            "prompt": prompt,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens,
            "seed": self.seed if seed is None else seed,
        }
        if echo:
            params["echo"] = True
        if logprobs is not None:
            params["logprobs"] = logprobs
        if stop:
            params["stop"] = list(stop)
        return self.client.completions.create(**params)

    # ------------------------------------------------------------------
    # Multiple-choice scoring
    # ------------------------------------------------------------------
    def answer_letter_logprob(self, *, model: str, prompt_messages: Sequence[dict],
                              letters: Sequence[str] = ("A", "B", "C", "D"),
                              top_logprobs: int = 5) -> LetterScores:
        """Score a multiple-choice item by next-token logprobs.

        Sends ``prompt_messages`` (the few-shot MCQ prompt ending in
        "Answer:") and inspects the log-probability the model assigns to each
        candidate answer letter as the *first generated token*. Returns the
        per-letter log-prob masses. If the endpoint returns no logprobs (or
        none of the letters appear), ``present`` is False and the caller should
        fall back to generate-and-parse.
        """
        resp = self.chat(
            model=model,
            messages=prompt_messages,
            max_tokens=1,            # we only care about the first token
            logprobs=True,
            top_logprobs=top_logprobs,
        )
        choice = resp.choices[0]
        tlp = getattr(choice, "logprobs", None)
        content = tlp.content if tlp else None
        # Reasoning models (e.g. deepseek-v4-flash) may consume the single
        # max_tokens=1 budget on the reasoning trace, leaving content empty
        # and logprobs None. Signal absent so the engine falls back to
        # generate-and-parse with a larger token budget.
        if not content:
            return LetterScores(scores={}, present=False)

        first = content[0]
        top_tokens = first.top_logprobs or []
        scores: dict = {}
        for tok in top_tokens:
            # Normalise token text: strip leading space / punctuation.
            txt = (tok.token or "").strip().upper()
            if txt in letters:
                # Keep the best (max) logprob seen for a given letter.
                if txt not in scores or tok.logprob > scores[txt]:
                    scores[txt] = tok.logprob
        return LetterScores(scores=scores, present=bool(scores))

    def answer_letter_generate(self, *, model: str, prompt_messages: Sequence[dict],
                               letters: Sequence[str] = ("A", "B", "C", "D"),
                               max_tokens: int = 4) -> str | None:
        """Fallback: ask the model to emit a letter and parse it."""
        text = self.chat_text(model=model, messages=prompt_messages, max_tokens=max_tokens,
                              temperature=0.0)
        text = text.upper()
        for ch in text:
            if ch in letters:
                return ch
        return None
