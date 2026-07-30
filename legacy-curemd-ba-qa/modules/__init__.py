"""
modules/ — HealthOS BA-QA Automation Suite Module Layer.

Each top-level module exposes a run(params: dict) -> dict function that
dispatches based on params['action'] and returns standardized results.

Active sub-package modules (manifest-based): fhir, leap, research, work_ops, files, coding, content
Standalone tool modules (run-function-based): see MODULES dict below.
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sub-package module discovery (manifest-based)
# ---------------------------------------------------------------------------
AVAILABLE_MODULES = [
    "fhir", "leap", "research", "work_ops", "files", "coding", "content",
]


def discover_modules() -> List[str]:
    """Auto-discover available sub-package modules."""
    modules_dir = Path(__file__).parent
    found = []
    for d in modules_dir.iterdir():
        if d.is_dir() and (d / "manifest.py").exists():
            found.append(d.name)
    return found


def load_module(name: str) -> Dict:
    """Load a sub-package module's registration info."""
    try:
        mod = importlib.import_module(f"modules.{name}.manifest")
        return mod.register()
    except Exception as e:
        logger.error(f"Failed to load module {name}: {e}")
        return {"name": name, "error": str(e)}


def load_all_modules() -> List[Dict]:
    """Load all discovered sub-package modules."""
    return [load_module(name) for name in discover_modules()]


# ---------------------------------------------------------------------------
# Standalone tool module registry (run-function-based)
# ---------------------------------------------------------------------------
STANDALONE_MODULE_NAMES = [
    "fhir_tools",
    "trigger_tester",
    "mapping_converter",
    "provenance_remapper",
    "db_analyzer",
    "scope_generator",
    "snomed_validator",
    "gap_analyzer",
    "web_discovery",
    "email_teams_extractor",
    "sharepoint_downloader",
    "devops_automation",
    "content_generator",
    "music_creator",
    "learning_engine",
]

MODULES: Dict[str, Any] = {}


def _load_standalone_modules() -> None:
    """Lazily import all standalone modules and populate MODULES dict."""
    for mod_name in STANDALONE_MODULE_NAMES:
        try:
            mod = importlib.import_module(f"modules.{mod_name}")
            if hasattr(mod, "run"):
                MODULES[mod_name] = mod.run
        except Exception as exc:
            logger.warning(f"Could not import standalone module '{mod_name}': {exc}")


def get_module(module_name: str):
    """Get a module's run function by name, loading if needed."""
    if not MODULES:
        _load_standalone_modules()
    return MODULES.get(module_name)


def run_module(module_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a module's run function by name."""
    fn = get_module(module_name)
    if fn is None:
        return {
            "success": False,
            "error": f"Module '{module_name}' not found. Available: {list(MODULES.keys())}",
        }
    try:
        return fn(params)
    except Exception as exc:
        return {"success": False, "error": f"Module '{module_name}' error: {exc}"}


__all__ = [
    "AVAILABLE_MODULES",
    "discover_modules",
    "load_module",
    "load_all_modules",
    "STANDALONE_MODULE_NAMES",
    "MODULES",
    "get_module",
    "run_module",
]
