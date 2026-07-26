import os
import json
import hashlib
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

REGISTRY_FILE_PATH = os.path.join(os.path.dirname(__file__), "storage", "modules_registry.json")


@dataclass
class ModuleProvenance:
    generated_by: str
    token_count: int
    parent_framework: str
    prompt_hash: str
    created_at: str
    checksum: str
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleProvenance":
        return cls(
            generated_by=data.get("generated_by", "OneAgent Meta Core"),
            token_count=data.get("token_count", 0),
            parent_framework=data.get("parent_framework", "OneAgent Meta Engine v1.0"),
            prompt_hash=data.get("prompt_hash", ""),
            created_at=data.get("created_at", ""),
            checksum=data.get("checksum", ""),
            version=data.get("version", "1.0.0")
        )


@dataclass
class SelfAuthoredModule:
    id: str
    name: str
    slug: str
    description: str
    prompt_origin: str
    model_author: str
    timestamp: str
    status: str  # 'pending', 'approved', 'rejected', 'reverted'
    code_snippet: str
    tests_code: str
    test_pass_rate: float
    sandbox_output: str
    provenance: ModuleProvenance

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["provenance"] = self.provenance.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SelfAuthoredModule":
        prov_dict = data.get("provenance", {})
        prov = ModuleProvenance.from_dict(prov_dict) if isinstance(prov_dict, dict) else prov_dict
        return cls(
            id=data["id"],
            name=data["name"],
            slug=data["slug"],
            description=data.get("description", ""),
            prompt_origin=data.get("prompt_origin", ""),
            model_author=data.get("model_author", "gemini-3.1-pro-preview"),
            timestamp=data.get("timestamp", ""),
            status=data.get("status", "pending"),
            code_snippet=data.get("code_snippet", ""),
            tests_code=data.get("tests_code", ""),
            test_pass_rate=float(data.get("test_pass_rate", 100.0)),
            sandbox_output=data.get("sandbox_output", ""),
            provenance=prov
        )


class ModuleRegistry:
    """
    Registry for tracking self-authored modules, their lifecycle states,
    code definitions, and provenance metadata.
    """

    def __init__(self, storage_path: str = REGISTRY_FILE_PATH):
        self.storage_path = storage_path
        self._modules: Dict[str, SelfAuthoredModule] = {}
        self._ensure_storage_dir()
        self.load()

    def _ensure_storage_dir(self):
        storage_dir = os.path.dirname(self.storage_path)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)

    def load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._modules = {
                        item["id"]: SelfAuthoredModule.from_dict(item)
                        for item in data
                    }
            except Exception as e:
                print(f"[ModuleRegistry] Warning loading registry file: {e}")
                self._modules = {}
        else:
            self._modules = {}

    def save(self):
        self._ensure_storage_dir()
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump([mod.to_dict() for mod in self._modules.values()], f, indent=2)
        except Exception as e:
            print(f"[ModuleRegistry] Error saving registry file: {e}")

    @staticmethod
    def compute_checksum(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def compute_prompt_hash(prompt: str) -> str:
        return hashlib.md5(prompt.encode("utf-8")).hexdigest()[:12]

    def register(
        self,
        name: str,
        slug: str,
        description: str,
        code_snippet: str,
        tests_code: str,
        model_author: str = "gemini-3.1-pro-preview",
        test_pass_rate: float = 100.0,
        sandbox_output: str = "",
        token_count: int = 850
    ) -> SelfAuthoredModule:
        module_id = f"meta-{int(time.time() * 1000)}"
        prompt_hash = self.compute_prompt_hash(description)
        checksum = self.compute_checksum(code_snippet)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        provenance = ModuleProvenance(
            generated_by=f"OneAgent Meta Self-Authoring Sandbox ({model_author})",
            token_count=token_count,
            parent_framework="OneAgent Meta Core v1.0",
            prompt_hash=prompt_hash,
            created_at=now_str,
            checksum=checksum,
            version="1.0.0"
        )

        module = SelfAuthoredModule(
            id=module_id,
            name=name,
            slug=slug,
            description=description,
            prompt_origin=description,
            model_author=model_author,
            timestamp=now_str,
            status="pending",
            code_snippet=code_snippet,
            tests_code=tests_code,
            test_pass_rate=test_pass_rate,
            sandbox_output=sandbox_output,
            provenance=provenance
        )

        self._modules[module_id] = module
        self.save()
        return module

    def get_module(self, module_id_or_slug: str) -> Optional[SelfAuthoredModule]:
        if module_id_or_slug in self._modules:
            return self._modules[module_id_or_slug]
        for mod in self._modules.values():
            if mod.slug == module_id_or_slug:
                return mod
        return None

    def list_modules(self, status_filter: Optional[str] = None) -> List[SelfAuthoredModule]:
        modules = list(self._modules.values())
        if status_filter:
            modules = [m for m in modules if m.status == status_filter]
        return sorted(modules, key=lambda x: x.timestamp, reverse=True)

    def update_status(self, module_id: str, new_status: str) -> Optional[SelfAuthoredModule]:
        if new_status not in ["pending", "approved", "rejected", "reverted"]:
            raise ValueError(f"Invalid status: {new_status}")

        module = self.get_module(module_id)
        if not module:
            return None

        module.status = new_status
        self.save()
        return module

    def update_test_results(self, module_id: str, pass_rate: float, sandbox_output: str) -> Optional[SelfAuthoredModule]:
        module = self.get_module(module_id)
        if not module:
            return None

        module.test_pass_rate = pass_rate
        module.sandbox_output = sandbox_output
        self.save()
        return module

    def delete_module(self, module_id: str) -> bool:
        if module_id in self._modules:
            del self._modules[module_id]
            self.save()
            return True
        return False
