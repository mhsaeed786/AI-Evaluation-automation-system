from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Callable

class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"

@dataclass
class ToolPolicy:
    auto_approve: bool = False
    auto_deny: bool = False
    require_approval: bool = False

class PolicyEngine:
    """Declarative per-tool policy with wildcard defaults."""
    def __init__(self):
        self.policies: Dict[str, ToolPolicy] = {"*": ToolPolicy()}

    def set_policy(self, name: str, policy: ToolPolicy):
        self.policies[name] = policy

    def decide(self, tool_name: str, tool_input: dict, ask_callback: Optional[Callable] = None) -> PolicyDecision:
        policy = self.policies.get(tool_name, self.policies.get("*", ToolPolicy()))
        if policy.auto_deny:
            return PolicyDecision.DENY
        if policy.auto_approve:
            return PolicyDecision.ALLOW
        if policy.require_approval:
            if ask_callback and ask_callback(tool_name, tool_input):
                return PolicyDecision.ALLOW
            return PolicyDecision.DENY
        return PolicyDecision.ALLOW
