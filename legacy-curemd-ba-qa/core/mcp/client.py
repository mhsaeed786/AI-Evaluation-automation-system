"""
MCP Client — connect to external MCP servers and expose their tools.

Loads MCP server configs from the goose-extensions/connectors/ directory
and from user-configured servers. Wraps each as a tool in the agent registry.
"""

import json
import logging
import subprocess
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONNECTORS_DIR = Path(__file__).resolve().parent.parent.parent / "goose-extensions" / "connectors"


@dataclass
class MCPServerConfig:
    name: str
    server_type: str  # "mcp-server", "stdio", "sse"
    description: str = ""
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class MCPClient:
    """Connect to and communicate with MCP servers."""

    def __init__(self, server_config: MCPServerConfig):
        self.config = server_config
        self._process: Optional[subprocess.Popen] = None
        self._tools: List[Dict] = []

    async def connect(self) -> bool:
        """Establish connection to the MCP server."""
        if self.config.server_type == "stdio" and self.config.command:
            try:
                self._process = subprocess.Popen(
                    [self.config.command] + self.config.args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                return True
            except Exception as e:
                logger.error(f"Failed to start MCP server {self.config.name}: {e}")
                return False
        # For HTTP/SSE servers, just mark as ready
        return True

    async def list_tools(self) -> List[Dict]:
        """Discover available tools from the MCP server."""
        # Return tools from config if pre-defined
        if "operations" in self.config.config:
            return [
                {"name": op, "description": f"{op} operation on {self.config.name}"}
                for op in self.config.config["operations"]
            ]
        return self._tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        logger.info(f"MCP call: {self.config.name}/{tool_name} args={list(arguments.keys())}")
        # Subclasses or protocol-specific adapters handle actual calls
        return {"status": "not_implemented", "server": self.config.name, "tool": tool_name}

    async def disconnect(self):
        if self._process:
            self._process.terminate()
            self._process = None


class MCPHost:
    """Manages all MCP server connections."""

    def __init__(self, connectors_dir: Optional[Path] = None):
        self._dir = connectors_dir or CONNECTORS_DIR
        self._servers: Dict[str, MCPServerConfig] = {}
        self._clients: Dict[str, MCPClient] = {}
        self._load_configs()

    def _load_configs(self):
        if not self._dir.exists():
            return
        for config_file in self._dir.glob("*.json"):
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
                server = MCPServerConfig(
                    name=data["name"],
                    server_type=data.get("type", "mcp-server"),
                    description=data.get("description", ""),
                    config=data.get("config", {}),
                )
                self._servers[server.name] = server
                logger.debug(f"Loaded MCP config: {server.name}")
            except Exception as e:
                logger.error(f"Failed to load MCP config {config_file}: {e}")

    def add_server(self, config: MCPServerConfig):
        self._servers[config.name] = config

    def remove_server(self, name: str):
        self._servers.pop(name, None)
        if name in self._clients:
            asyncio.get_event_loop().run_until_complete(self._clients[name].disconnect())
            del self._clients[name]

    async def connect_server(self, name: str) -> Optional[MCPClient]:
        config = self._servers.get(name)
        if not config:
            return None
        client = MCPClient(config)
        if await client.connect():
            self._clients[name] = client
            return client
        return None

    async def connect_all(self):
        for name in self._servers:
            if self._servers[name].enabled:
                await self.connect_server(name)

    def list_servers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.name,
                "type": s.server_type,
                "description": s.description,
                "enabled": s.enabled,
                "connected": s.name in self._clients,
            }
            for s in self._servers.values()
        ]

    def get_client(self, name: str) -> Optional[MCPClient]:
        return self._clients.get(name)


_host: Optional[MCPHost] = None


def get_mcp_host() -> MCPHost:
    global _host
    if _host is None:
        _host = MCPHost()
    return _host
