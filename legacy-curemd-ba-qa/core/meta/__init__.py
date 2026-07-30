"""core/meta — Self-extension engine."""

from .module_author import ModuleAuthor, AuthorResult
from .sandbox import Sandbox, get_sandbox
from .registry import AuthoredModule, ModuleRegistry, get_module_registry

__all__ = [
    "ModuleAuthor", "AuthorResult",
    "Sandbox", "get_sandbox",
    "AuthoredModule", "ModuleRegistry", "get_module_registry",
]
