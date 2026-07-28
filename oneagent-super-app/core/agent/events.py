from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class EventType(Enum):
    MESSAGE = "message"
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    USAGE = "usage"
    STATE_CHANGE = "state_change"
    FINISHED = "finished"
    ERROR = "error"

@dataclass
class AgentEvent:
    type: EventType
    content: str = ""
    data: dict = field(default_factory=dict)
    step: int = 0
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    error: Optional[str] = None
