"""
OneAgent Core — Command Validation & Security
Inspired by Super-App's allowlist command validation + metacharacter rejection.

Features:
- Allowlist of permitted binaries
- Shell metacharacter rejection (injection prevention)
- Structured arg list mode (shell=False, no injection possible)
- SSRF protection for URL-based tools
- File path sandboxing (no traversal outside workspace)
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

# Allowed command prefixes — extend as needed
ALLOWED_COMMAND_PREFIXES = {
    "python", "python3", "pip", "pip3",
    "node", "npm", "npx", "yarn", "pnpm", "bun", "tsx",
    "git", "gh",
    "curl", "wget",
    "ls", "cat", "echo", "mkdir", "cp", "mv", "rm", "touch", "find", "grep", "head", "tail",
    "docker", "docker-compose",
    "playwright",
    "pytest", "uvicorn",
}

# Dangerous shell metacharacters that indicate injection attempts
_SHELL_DANGEROUS_PATTERNS = re.compile(
    r"(?:;|\|\||&&|`|\$\(|\$\{|\n|\r|>\s|<\s|\(\s*\))"
)

# Private network ranges for SSRF protection
PRIVATE_IP_PATTERNS = [
    re.compile(r"^127\."),       # Loopback
    re.compile(r"^10\."),        # Class A private
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[01])\."),  # Class B private
    re.compile(r"^192\.168\."),  # Class C private
    re.compile(r"^0\."),          # Reserved
    re.compile(r"^169\.254\."),   # Link-local
    re.compile(r"::1$"),          # IPv6 loopback
    re.compile(r"^fe80:"),        # IPv6 link-local
    re.compile(r"^fc00:"),       # IPv6 unique local
    re.compile(r"^fd"),           # IPv6 unique local
]


class SecurityError(Exception):
    """Raised when a command or request is rejected by the security layer."""
    pass


def validate_command(cmd: str) -> str:
    """Validate and sanitize a shell command before execution.

    Rejects commands containing dangerous shell metacharacters and ensures
    the command starts with a known-safe binary.
    Returns the cleaned command on success; raises SecurityError on rejection.
    """
    if not cmd or not cmd.strip():
        raise SecurityError("Empty command")

    stripped = cmd.strip()

    if _SHELL_DANGEROUS_PATTERNS.search(stripped):
        raise SecurityError(
            f"Command rejected — contains disallowed shell metacharacters: {stripped[:120]}"
        )

    # Extract the first token (the binary name)
    first_token = stripped.split()[0]
    base = Path(first_token).name.lower()

    if base not in ALLOWED_COMMAND_PREFIXES:
        raise SecurityError(
            f"Command rejected — unknown binary '{base}'. "
            f"Allowed: {sorted(ALLOWED_COMMAND_PREFIXES)}"
        )

    return stripped


def validate_args(binary: str, args: List[str]) -> List[str]:
    """Validate a structured arg list for shell=False execution.

    Checks the binary against the allowlist but allows pipes/redirects
    in individual args (since shell=False prevents injection).
    """
    base = Path(binary).name.lower()
    if base not in ALLOWED_COMMAND_PREFIXES:
        raise SecurityError(
            f"Binary '{base}' is not in the allowlist. "
            f"Allowed: {sorted(ALLOWED_COMMAND_PREFIXES)}"
        )

    # Check each arg for dangerous patterns (still block obvious injection in args)
    for arg in args:
        if _SHELL_DANGEROUS_PATTERNS.search(arg):
            raise SecurityError(
                f"Argument contains dangerous metacharacters: {arg[:80]}"
            )

    return args


def validate_url(url: str, allow_private: bool = False,
                 allowlist: set = None) -> str:
    """Validate a URL for SSRF protection.

    Blocks private network ranges by default.
    Allows specific hostnames via the allowlist parameter.
    """
    if not url or not url.strip():
        raise SecurityError("Empty URL")

    parsed = urlparse(url.strip())

    if parsed.scheme not in ("http", "https"):
        raise SecurityError(f"URL scheme '{parsed.scheme}' not allowed. Use http or https.")

    hostname = parsed.hostname or ""
    if not hostname:
        raise SecurityError("URL has no hostname")

    # Check allowlist first
    if allowlist and hostname in allowlist:
        return url.strip()

    # Check private network ranges
    if not allow_private:
        for pattern in PRIVATE_IP_PATTERNS:
            if pattern.search(hostname):
                raise SecurityError(
                    f"URL rejected — hostname '{hostname}' is in a private network range. "
                    f"Set allow_private=True or add to allowlist to permit."
                )

        # Block localhost variants
        if hostname in ("localhost", "0.0.0.0", "::1"):
            raise SecurityError(
                f"URL rejected — hostname '{hostname}' is localhost. "
                f"Set allow_private=True to permit."
            )

    return url.strip()


def validate_file_path(path: str, workspace: str = None,
                       allow_outside: bool = False) -> str:
    """Validate a file path to prevent directory traversal.

    By default, paths must resolve inside the workspace directory.
    """
    if not path or not path.strip():
        raise SecurityError("Empty file path")

    target = Path(path).resolve()

    if not allow_outside and workspace:
        ws = Path(workspace).resolve()
        try:
            target.relative_to(ws)
        except ValueError:
            raise SecurityError(
                f"Path '{path}' is outside the workspace directory. "
                f"Workspace: {ws}"
            )

    return str(target)


def add_allowed_binary(name: str) -> None:
    """Add a binary to the allowlist at runtime."""
    ALLOWED_COMMAND_PREFIXES.add(Path(name).name.lower())


def get_allowed_binaries() -> List[str]:
    """Return sorted list of allowed binaries."""
    return sorted(ALLOWED_COMMAND_PREFIXES)