"""
Skill Pack System — OpenClaude-style skill packs.

A skill = a folder with manifest.yaml + prompt.md + optional code.
Skills bundle prompts and tools into reusable, composable units.
Modules load skills by name; the registry resolves and serves them.
"""

import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent / "packs"


@dataclass
class SkillPack:
    """A loaded skill pack."""
    name: str
    description: str
    version: str = "1.0"
    author: str = ""
    category: str = "general"
    prompt: str = ""
    tools: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    path: Optional[Path] = None

    def get_system_prompt(self, **kwargs) -> str:
        prompt = self.prompt
        for key, value in kwargs.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
        return prompt


class SkillRegistry:
    """Load and manage skill packs from the packs/ directory."""

    def __init__(self, skills_dir: Optional[Path] = None):
        self._dir = skills_dir or SKILLS_DIR
        self._skills: Dict[str, SkillPack] = {}
        self._load_all()

    def _load_all(self):
        if not self._dir.exists():
            return
        for skill_dir in self._dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "manifest.yaml").exists():
                self._load_skill(skill_dir)

    def _load_skill(self, skill_dir: Path):
        manifest_path = skill_dir / "manifest.yaml"
        prompt_path = skill_dir / "prompt.md"
        try:
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f) or {}
            prompt = ""
            if prompt_path.exists():
                prompt = prompt_path.read_text(encoding="utf-8")
            skill = SkillPack(
                name=manifest.get("name", skill_dir.name),
                description=manifest.get("description", ""),
                version=manifest.get("version", "1.0"),
                author=manifest.get("author", ""),
                category=manifest.get("category", "general"),
                prompt=prompt,
                tools=manifest.get("tools", []),
                parameters=manifest.get("parameters", {}),
                path=skill_dir,
            )
            self._skills[skill.name] = skill
            logger.debug(f"Loaded skill: {skill.name}")
        except Exception as e:
            logger.error(f"Failed to load skill from {skill_dir}: {e}")

    def get(self, name: str) -> Optional[SkillPack]:
        return self._skills.get(name)

    def list_skills(self, category: Optional[str] = None) -> List[SkillPack]:
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills

    def list_categories(self) -> List[str]:
        return sorted(set(s.category for s in self._skills.values()))

    def reload(self):
        self._skills.clear()
        self._load_all()


_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
