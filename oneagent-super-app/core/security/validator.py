from __future__ import annotations
from typing import List, Optional
import re

class SecurityError(Exception):
    pass

ALLOWED_COMMAND_PREFIXES = {
    "python", "python3", "node", "npm", "npx", "git", "curl", "wget", "docker",
    "playwright", "pytest", "uvicorn", "ls", "cat", "echo", "mkdir", "cd", "pwd"
}

DANGEROUS_PATTERNS = re.compile(r"(?:;|\|\||&&|`|\$\(|\$\{|\n|\r|>\s|<\s|\(\s*\))")

def validate_command(cmd: str) -> str:
    if not cmd or not cmd.strip():
        raise SecurityError("Empty command")
    if DANGEROUS_PATTERNS.search(cmd):
        raise SecurityError("Command contains dangerous shell metacharacters")
    binary = cmd.strip().split()[0].split("/")[-1].lower()
    if binary not in ALLOWED_COMMAND_PREFIXES:
        raise SecurityError(f"Binary '{binary}' not in allowlist")
    return cmd

def validate_url(url: str, allow_private: bool = False, allowlist: Optional[set] = None) -> str:
    if not re.match(r"^https?://", url):
        raise SecurityError("URL must use http or https")
    return url

def validate_file_path(path: str, workspace: str = None, allow_outside: bool = False) -> str:
    return path
