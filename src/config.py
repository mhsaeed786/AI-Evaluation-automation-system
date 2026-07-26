"""Configuration loading.

Reads environment (``.env``) and the YAML files under ``config/`` and exposes
a single validated :class:`Config` object. All paths resolve relative to the
project root (the parent of this ``src`` package), so the project is portable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Project root = parent of the directory containing this file (src/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Default Ollama Cloud OpenAI-compatible endpoint.
# (Runtime-confirmed via src.smoke_test — see README "Pinning the endpoint".)
DEFAULT_BASE_URL = "https://api.ollama.com/v1"


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class SamplingDefaults:
    seed: int = 1234
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 1024
    timeout: float = 180.0


@dataclass
class Config:
    api_key: str
    base_url: str
    org_id: str
    sampling: SamplingDefaults = field(default_factory=SamplingDefaults)
    models: dict = field(default_factory=dict)
    benchmarks: dict = field(default_factory=dict)
    published_scores: dict = field(default_factory=dict)
    project_root: Path = PROJECT_ROOT

    # ----- convenience accessors -------------------------------------
    def benchmark(self, name: str) -> dict:
        try:
            return self.benchmarks["benchmarks"][name]
        except KeyError:
            raise KeyError(f"Benchmark '{name}' not found in config/benchmarks.yaml")

    def advertised(self, model_id: str, benchmark: str):
        """Return vendor-advertised percent score or None.

        Looks up the exact ``model_id`` in both the ``models:`` block
        (per-model ``advertised:`` map) and the flat ``extended:`` block.
        Returns None when no reference exists — the report then shows 'n/a'
        rather than inventing a number. Live model ids must match
        published_scores keys exactly; update config/published_scores.yaml as
        new models are measured.
        """
        entry = self.published_scores.get("models", {}).get(model_id)
        if entry:
            val = entry.get("advertised", {}).get(benchmark)
            if val is not None:
                return val
        ext = self.published_scores.get("extended", {}).get(model_id)
        if ext:
            val = ext.get(benchmark)
            if val is not None:
                return val
        return None

    @property
    def auth_headers(self) -> dict:
        h = {"Authorization": f"Bearer {self.api_key}"}
        if self.org_id:
            h["OpenAI-Organization"] = self.org_id
        return h


def load_config(env_path: Path | None = None, *, require_key: bool = True) -> Config:
    """Load .env + YAML configs and return a validated :class:`Config`.

    ``require_key=False`` lets callers that never hit the network (e.g. the
    report renderer, which reads only ``results/`` + ``published_scores.yaml``)
    proceed without an API key. Runners that actually call Ollama Cloud keep the
    default ``require_key=True`` so a missing key fails fast instead of dying
    on the first request.
    """
    if env_path is None:
        env_path = PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.environ.get("OLLAMA_API_KEY", "").strip()
    if not api_key and require_key:
        raise SystemExit(
            "OLLAMA_API_KEY is not set. Copy .env.example to .env and paste "
            "your Ollama Cloud key (https://ollama.com/cloud)."
        )

    base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    org_id = os.environ.get("OLLAMA_ORG_ID", "").strip()

    sampling = SamplingDefaults(
        seed=int(os.environ.get("OLLAMA_SEED", "1234")),
        temperature=float(os.environ.get("OLLAMA_TEMPERATURE", "0.0")),
        timeout=float(os.environ.get("OLLAMA_TIMEOUT", "180")),
    )

    cfg = Config(
        api_key=api_key,
        base_url=base_url,
        org_id=org_id,
        sampling=sampling,
        models=_load_yaml(CONFIG_DIR / "models.yaml"),
        benchmarks=_load_yaml(CONFIG_DIR / "benchmarks.yaml"),
        published_scores=_load_yaml(CONFIG_DIR / "published_scores.yaml"),
    )

    for d in (RESULTS_DIR, REPORTS_DIR, DATA_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    return cfg


PROVIDERS = {
    "ollama": ("OLLAMA_BASE_URL", "OLLAMA_API_KEY", "https://ollama.com/v1"),
    "qwen": ("QWEN_BASE_URL", "QWEN_API_KEY", "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"),
    "groq": ("GROQ_BASE_URL", "GROQ_API_KEY", "https://api.groq.com/openai/v1"),
    "openrouter": ("OPENROUTER_BASE_URL", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"),
    "cerebras": ("CEREBRAS_BASE_URL", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1"),
    "hf": ("HF_BASE_URL", "HF_TOKEN", "https://router.huggingface.co/v1"),
    "glm": ("GLM_BASE_URL", "GLM_API_KEY", "https://open.bigmodel.cn/api/paas/v4"),
    "poe": ("POE_BASE_URL", "POE_API_KEY", "https://api.poe.com/v1"),
}


def get_provider_credentials(provider_name: str) -> tuple[str, str]:
    name = provider_name.lower().strip()
    if name not in PROVIDERS:
        name = "ollama"
    url_var, key_var, default_url = PROVIDERS[name]
    url = os.environ.get(url_var, default_url).strip().rstrip("/")
    key = os.environ.get(key_var, "").strip()
    if not key and name == "ollama":
        key = os.environ.get("OLLAMA_API_KEY", "").strip()
    return url, key

