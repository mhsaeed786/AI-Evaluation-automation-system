from __future__ import annotations
from typing import List
from ..llm import LLMMessage, MessageRole

def compress_messages(messages: List[LLMMessage], keep_last: int = 10) -> List[LLMMessage]:
    """Drop middle messages, keep system + recent."""
    system = [m for m in messages if m.role == MessageRole.SYSTEM]
    tail = messages[-keep_last:] if len(messages) > keep_last else messages
    summary = LLMMessage(role=MessageRole.USER, content="[Earlier conversation summarized for brevity.]")
    return system + [summary] + tail
