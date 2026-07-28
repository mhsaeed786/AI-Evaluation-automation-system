from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from ..llm import LLMMessage

@dataclass
class ContextMessage:
    message: LLMMessage
    tokens: int = 0
    priority: int = 0

class ContextManager:
    """Tracks token budget, compresses oldest messages."""
    def __init__(self, max_tokens: int = 120_000):
        self.max_tokens = max_tokens
        self.messages: List[ContextMessage] = []

    def add(self, message: LLMMessage, tokens: int = 0, priority: int = 0):
        self.messages.append(ContextMessage(message, tokens, priority))

    def fit(self, reserve: int = 8000) -> List[LLMMessage]:
        # Drop oldest low-priority messages over budget
        budget = self.max_tokens - reserve
        total = sum(m.tokens for m in self.messages)
        keep = list(self.messages)
        idx = 0
        while total > budget and idx < len(keep):
            if keep[idx].priority == 0:
                total -= keep[idx].tokens
                keep[idx] = None
            idx += 1
        keep = [m for m in keep if m is not None]
        return [m.message for m in keep]
