"""
OneAgent Core — Structured Workspace Files System
Inspired by OpenClaw's workspace attestation pattern.

Workspace files are injected into the system prompt on session start.
Large files are truncated with markers. Blank files are skipped.
BOOTSTRAP.md is only present for brand-new workspaces and deleted after first-run ritual.

Files:
  SOUL.md       — Agent persona, tone, boundaries
  AGENTS.md     — Operating instructions, tool usage rules
  USER.md       — User profile, preferences, context
  IDENTITY.md   — Agent name, emoji, display identity
  TOOLS.md      — Tool notes, known limitations, tips
  BOOTSTRAP.md  — One-time first-run ritual (deleted after completion)
  HEARTBEAT.md  — Periodic health checklist
  memory/YYYY-MM-DD.md — Date-organized memory logs
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Maximum characters per workspace file when injecting into system prompt
MAX_FILE_CHARS = 4000
# Truncation marker appended when a file exceeds the limit
TRUNCATION_MARKER = "\n\n[... file truncated at {limit} chars ...]"

# Which files to inject, in order
WORKSPACE_FILES = [
    "IDENTITY.md",
    "SOUL.md",
    "AGENTS.md",
    "USER.md",
    "TOOLS.md",
    "HEARTBEAT.md",
]

# Memory files: today + yesterday
MEMORY_DIR = "memory"


class WorkspaceManager:
    """Manages OneAgent structured workspace files."""

    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = Path(workspace_dir or os.environ.get(
            "ONEAGENT_WORKSPACE",
            str(Path.home() / ".oneagent" / "workspace")
        ))
        self.memory_dir = self.workspace_dir / MEMORY_DIR

    def ensure_workspace(self) -> None:
        """Create workspace directory structure if missing."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def is_new_workspace(self) -> bool:
        """Check if this is a brand-new workspace that needs bootstrap."""
        return not (self.workspace_dir / "AGENTS.md").exists()

    def create_bootstrap(self, task: str = None) -> None:
        """Create BOOTSTRAP.md for first-run onboarding ritual."""
        bootstrap_path = self.workspace_dir / "BOOTSTRAP.md"
        if bootstrap_path.exists():
            return

        content = f"""# OneAgent First-Run Bootstrap

This is your first time running OneAgent. Please complete this initialization ritual:

1. Read the user's profile in USER.md (if provided)
2. Introduce yourself using your IDENTITY.md
3. Scan the workspace and confirm readiness
4. Ask the user what they'd like to automate first
5. Delete this file once the ritual is complete

**Created at:** {datetime.now().isoformat()}
**Initial task:** {task or "None — awaiting user input"}
"""
        bootstrap_path.write_text(content, encoding="utf-8")

    def delete_bootstrap(self) -> None:
        """Remove BOOTSTRAP.md after first-run ritual is complete."""
        bootstrap_path = self.workspace_dir / "BOOTSTRAP.md"
        if bootstrap_path.exists():
            bootstrap_path.unlink()

    def read_file(self, filename: str) -> Optional[str]:
        """Read a workspace file, returning None if missing or blank."""
        path = self.workspace_dir / filename
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return None
        return content

    def write_file(self, filename: str, content: str) -> None:
        """Write content to a workspace file."""
        path = self.workspace_dir / filename
        self.ensure_workspace()
        path.write_text(content, encoding="utf-8")

    def truncate_for_prompt(self, content: str, limit: int = MAX_FILE_CHARS) -> str:
        """Truncate content with a marker if it exceeds the limit."""
        if len(content) > limit:
            return content[:limit] + TRUNCATION_MARKER.format(limit=limit)
        return content

    def get_memory_files(self, dates: list = None) -> Dict[str, str]:
        """Get memory files for specified dates (default: today + yesterday)."""
        if dates is None:
            today = datetime.now().strftime("%Y-%m-%d")
            from datetime import timedelta
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            dates = [today, yesterday]

        memories = {}
        for date_str in dates:
            mem_path = self.memory_dir / f"{date_str}.md"
            if mem_path.exists():
                content = mem_path.read_text(encoding="utf-8").strip()
                if content:
                    memories[date_str] = self.truncate_for_prompt(content, 2000)
        return memories

    def write_memory(self, content: str, date_str: str = None) -> None:
        """Append to today's memory log."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        mem_path = self.memory_dir / f"{date_str}.md"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"\n## [{timestamp}]\n{content}\n"
        with open(mem_path, "a", encoding="utf-8") as f:
            f.write(entry)

    def build_system_prompt_context(self) -> str:
        """Build the workspace context string for injection into system prompt.

        Returns a formatted string with all workspace file contents,
        or empty string if no files exist.
        """
        self.ensure_workspace()

        # Handle bootstrap for new workspaces
        if self.is_new_workspace():
            self.create_bootstrap()

        sections = []

        for filename in WORKSPACE_FILES:
            content = self.read_file(filename)
            if content is None:
                continue
            truncated = self.truncate_for_prompt(content)
            sections.append(f"### {filename}\n{truncated}")

        # Bootstrap (if present)
        bootstrap = self.read_file("BOOTSTRAP.md")
        if bootstrap:
            sections.append(f"### BOOTSTRAP.md (FIRST-RUN RITUAL — delete after completion)\n{self.truncate_for_prompt(bootstrap)}")

        # Memory files
        memories = self.get_memory_files()
        if memories:
            mem_lines = []
            for date_str, content in memories.items():
                mem_lines.append(f"#### Memory: {date_str}\n{content}")
            sections.append(f"### Recent Memory\n" + "\n\n".join(mem_lines))

        if not sections:
            return ""

        return "# OneAgent Workspace Context\n\n" + "\n\n---\n\n".join(sections)

    def list_workspace_files(self) -> list:
        """List all files in the workspace directory."""
        if not self.workspace_dir.exists():
            return []
        return [f.name for f in self.workspace_dir.iterdir() if f.is_file()]

    def initialize_default_workspace(self, user_name: str = None, user_role: str = None) -> None:
        """Create default workspace files for a new user."""
        self.ensure_workspace()

        defaults = {
            "IDENTITY.md": f"""# OneAgent Identity

**Name:** OneAgent
**Emoji:** 🧠
**Version:** 1.0.0
**Description:** A generalist AI agent that learns from your data and evolves into specialist limbs.

I am OneAgent — generalist at birth, specialist by learning.
""",
            "SOUL.md": """# OneAgent Persona

You are OneAgent, an intelligent AI assistant. You are helpful, knowledgeable, and direct.

## Core Traits
- **Adaptive:** You learn from the user's data and evolve specialist capabilities
- **Efficient:** Be targeted in exploration. Don't waste tokens on unnecessary steps
- **Honest:** Admit uncertainty when appropriate. Never fabricate information
- **Proactive:** Suggest automations when you notice repetitive patterns

## Boundaries
- Never share API keys or secrets
- Always ask before deleting files
- Respect robots.txt and rate limits when browsing
- Use sandboxed execution for untrusted code
""",
            "AGENTS.md": """# OneAgent Operating Instructions

## Tool Usage
1. Always validate tool inputs before calling
2. Parse tool outputs carefully — check for errors before proceeding
3. Use the cheapest available model for the task class
4. Cache results when possible to reduce API costs
5. Track spending against the daily budget cap

## Agent Loop
1. **Plan:** Break down the task into steps
2. **Execute:** Call one tool at a time
3. **Observe:** Parse and verify the result
4. **Repeat:** Continue until task is complete
5. **Report:** Summarize what was done and what was found

## Specialist Evolution
When you detect patterns in the user's work:
1. Note the pattern in memory
2. Suggest creating a specialist limb
3. If approved, use the meta-authoring engine to generate the module
4. Test in sandbox before promoting to production
""",
            "USER.md": f"""# User Profile

**Name:** {user_name or "Unknown"}
**Role:** {user_role or "General"}
**Timezone:** {datetime.now().astimezone().tzinfo}
**Preferences:**
- Communication style: Direct and concise
- Code style: Clean, well-documented
- Language: English

*(Update this file to help OneAgent adapt to your work)*
""",
            "TOOLS.md": """# Tool Notes

## Available Base Tools
- `web_fetch` — Fetch and parse web pages
- `web_search` — Search the web
- `browser_use` — Playwright browser automation
- `code_exec` — Execute code in sandbox
- `file_ops` — Read, write, organize files
- `shell_exec` — Run shell commands (validated)

## Known Limitations
- Browser automation requires Playwright to be installed
- Code execution runs in an isolated sandbox
- Shell commands are validated against an allowlist

## Tips
- Use `web_search` before `web_fetch` to find relevant URLs
- Batch file operations to reduce round trips
- Cache expensive LLM calls when the same prompt recurs
""",
            "HEARTBEAT.md": """# OneAgent Health Checklist

## Periodic Checks (run every 5 minutes)
- [ ] Is the LLM router responding?
- [ ] Are all enabled MCP connectors reachable?
- [ ] Is the SQLite knowledge base accessible?
- [ ] Are any cron jobs overdue?
- [ ] Is the budget spend within the daily cap?
- [ ] Are there any stalled agent sessions?
""",
        }

        for filename, content in defaults.items():
            path = self.workspace_dir / filename
            if not path.exists():
                path.write_text(content, encoding="utf-8")

        self.create_bootstrap()