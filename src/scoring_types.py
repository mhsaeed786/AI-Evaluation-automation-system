"""Dependency-free shared types for the scoring layer.

Kept separate from :mod:`src.ollama_client` so the offline scoring self-test
(``tests/test_scoring.py``) and :mod:`src.scorers` can import
:class:`LetterScores` without pulling in the ``openai`` / ``tenacity`` SDKs.
A multiple-choice score is just a mapping of answer letters to
log-probabilities; it carries no network dependency.

The production client re-exports this class, so
``from src.ollama_client import LetterScores`` continues to work for callers
that already depend on the SDK.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class LetterScores:
    """Log-probability mass for each candidate answer letter.

    ``scores`` maps each letter (``"A"``, ``"B"``, ...) to its natural-log
    probability (nats) as the *next token* after the prompt. ``present`` is
    False when the endpoint returned no ``top_logprobs`` at all, or none of the
    candidate letters appeared — in which case the caller should fall back to
    generate-and-parse.
    """

    scores: dict  # {"A": float, "B": float, ...} in natural-log nats
    present: bool  # whether any answer letters were seen in top_logprobs

    def argmax_letter(self) -> str | None:
        """Return the highest-logprob letter, or None if no letters scored."""
        if not self.scores:
            return None
        return max(self.scores, key=self.scores.get)

    def softmax_probs(self) -> dict:
        """Renormalise the candidate-letter logprobs to probabilities."""
        if not self.scores:
            return {}
        vals = list(self.scores.values())
        m = max(vals)
        exps = {k: math.exp(v - m) for k, v in self.scores.items()}
        tot = sum(exps.values()) or 1.0
        return {k: v / tot for k, v in exps.items()}
