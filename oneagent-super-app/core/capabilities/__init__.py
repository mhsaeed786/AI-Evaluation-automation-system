"""
OneAgent Core — Capability Registration System
Inspired by OpenClaw's capability registration model.

Instead of ad-hoc plugin interfaces, define explicit capability types.
Each plugin/limb registers against these types, making ownership explicit.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class CapabilityType(Enum):
    """Explicit capability types that plugins can register."""
    TEXT_INFERENCE = "text_inference"       # LLM text generation
    WEB_SEARCH = "web_search"               # Web search
    WEB_FETCH = "web_fetch"                 # Fetch/parse web pages
    BROWSER_CONTROL = "browser_control"     # Full browser automation
    CODE_EXECUTION = "code_execution"       # Execute code in sandbox
    FILE_OPS = "file_ops"                   # File system operations
    SHELL_EXEC = "shell_exec"               # Shell command execution
    IMAGE_GENERATION = "image_generation"   # Generate images
    IMAGE_ANALYSIS = "image_analysis"       # Analyze/understand images
    DATA_STORAGE = "data_storage"           # Persistent storage
    MESSAGE_CHANNEL = "message_channel"     # Communication channels (Slack, Teams, etc.)
    SCHEDULER = "scheduler"                 # Task scheduling
    RAG = "rag"                              # Retrieval-augmented generation
    EMBEDDING = "embedding"                  # Vector embeddings
    MCP_SERVER = "mcp_server"                # MCP protocol server
    SKILL_PROVIDER = "skill_provider"       # Provides skill packs
    META_AUTHOR = "meta_author"             # Self-authoring engine


@dataclass
class Capability:
    """A registered capability."""
    type: CapabilityType
    provider_id: str          # ID of the plugin/limb providing this
    name: str                 # Human-readable name
    handler: Optional[Callable] = None  # Function to invoke this capability
    config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 50        # Higher = preferred over alternatives
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """Registry for capabilities with provider routing."""

    def __init__(self):
        self._capabilities: Dict[CapabilityType, List[Capability]] = {
            ct: [] for ct in CapabilityType
        }
        self._providers: Dict[str, dict] = {}  # provider_id → metadata

    def register_provider(self, provider_id: str, name: str,
                          description: str = "", version: str = "1.0.0") -> None:
        """Register a plugin/limb as a provider."""
        self._providers[provider_id] = {
            "id": provider_id,
            "name": name,
            "description": description,
            "version": version,
            "registered_at": __import__("datetime").datetime.now().isoformat(),
        }

    def register_capability(self, cap: Capability) -> None:
        """Register a capability. Multiple providers can register the same type."""
        self._capabilities[cap.type].append(cap)
        # Sort by priority descending (highest = preferred)
        self._capabilities[cap.type].sort(key=lambda c: c.priority, reverse=True)

    def get(self, cap_type: CapabilityType,
            provider_id: str = None) -> Optional[Capability]:
        """Get the best (highest-priority, enabled) capability of a type.

        If provider_id is specified, get from that specific provider.
        """
        caps = self._capabilities.get(cap_type, [])
        if not caps:
            return None

        if provider_id:
            for cap in caps:
                if cap.provider_id == provider_id and cap.enabled:
                    return cap
            return None

        # Return highest-priority enabled capability
        for cap in caps:
            if cap.enabled:
                return cap
        return None

    def get_all(self, cap_type: CapabilityType) -> List[Capability]:
        """Get all registered capabilities of a type (sorted by priority)."""
        return [c for c in self._capabilities.get(cap_type, []) if c.enabled]

    def list_capabilities(self, cap_type: CapabilityType = None) -> List[dict]:
        """List all capabilities, optionally filtered by type."""
        result = []
        types = [cap_type] if cap_type else list(CapabilityType)
        for ct in types:
            for cap in self._capabilities.get(ct, []):
                result.append({
                    "type": ct.value,
                    "provider_id": cap.provider_id,
                    "name": cap.name,
                    "priority": cap.priority,
                    "enabled": cap.enabled,
                    "config": cap.config,
                })
        return result

    def list_providers(self) -> List[dict]:
        """List all registered providers."""
        return list(self._providers.values())

    def disable_provider(self, provider_id: str) -> int:
        """Disable all capabilities from a provider. Returns count disabled."""
        count = 0
        for caps in self._capabilities.values():
            for cap in caps:
                if cap.provider_id == provider_id and cap.enabled:
                    cap.enabled = False
                    count += 1
        return count

    def enable_provider(self, provider_id: str) -> int:
        """Enable all capabilities from a provider."""
        count = 0
        for caps in self._capabilities.values():
            for cap in caps:
                if cap.provider_id == provider_id and not cap.enabled:
                    cap.enabled = True
                    count += 1
        return count

    def build_metadata_snapshot(self) -> dict:
        """Build a metadata-only snapshot for fast startup.

        This is used for config validation, capability discovery,
        and UI hints without loading any plugin code.
        """
        return {
            "providers": list(self._providers.values()),
            "capabilities": self.list_capabilities(),
            "capability_types": [ct.value for ct in CapabilityType],
        }


def create_default_registry() -> CapabilityRegistry:
    """Create a capability registry with default OneAgent capabilities."""
    registry = CapabilityRegistry()

    # Register OneAgent as a provider
    registry.register_provider(
        provider_id="oneagent-core",
        name="OneAgent Core",
        description="Base generalist agent capabilities",
        version="1.0.0",
    )

    # Register base capabilities
    registry.register_capability(Capability(
        type=CapabilityType.TEXT_INFERENCE,
        provider_id="oneagent-core",
        name="LLM Text Generation",
        priority=50,
    ))
    registry.register_capability(Capability(
        type=CapabilityType.WEB_SEARCH,
        provider_id="oneagent-core",
        name="Web Search",
        priority=50,
    ))
    registry.register_capability(Capability(
        type=CapabilityType.WEB_FETCH,
        provider_id="oneagent-core",
        name="Web Page Fetch",
        priority=50,
    ))
    registry.register_capability(Capability(
        type=CapabilityType.BROWSER_CONTROL,
        provider_id="oneagent-core",
        name="Playwright Browser Automation",
        priority=50,
    ))
    registry.register_capability(Capability(
        type=CapabilityType.CODE_EXECUTION,
        provider_id="oneagent-core",
        name="Sandboxed Code Execution",
        priority=50,
    ))
    registry.register_capability(Capability(
        type=CapabilityType.FILE_OPS,
        provider_id="oneagent-core",
        name="File Operations",
        priority=50,
    ))
    registry.register_capability(Capability(
        type=CapabilityType.SHELL_EXEC,
        provider_id="oneagent-core",
        name="Shell Command Execution",
        priority=50,
    ))
    registry.register_capability(Capability(
        type=CapabilityType.RAG,
        provider_id="oneagent-core",
        name="SQLite RAG Knowledge Base",
        priority=50,
    ))
    registry.register_capability(Capability(
        type=CapabilityType.META_AUTHOR,
        provider_id="oneagent-core",
        name="Meta Self-Authoring Engine",
        priority=50,
    ))

    return registry