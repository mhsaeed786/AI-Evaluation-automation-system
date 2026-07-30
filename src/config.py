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

    models_cfg = _load_yaml(CONFIG_DIR / "models.yaml")
    providers_yaml_path = CONFIG_DIR / "providers.yaml"
    if providers_yaml_path.exists():
        models_cfg.setdefault("provider_models", {}).update(
            _load_yaml(providers_yaml_path).get("provider_models", {}))
    cfg = Config(
        api_key=api_key,
        base_url=base_url,
        org_id=org_id,
        sampling=sampling,
        models=models_cfg,
        benchmarks=_load_yaml(CONFIG_DIR / "benchmarks.yaml"),
        published_scores=_load_yaml(CONFIG_DIR / "published_scores.yaml"),
    )

    for d in (RESULTS_DIR, REPORTS_DIR, DATA_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    return cfg


# Provider registry: name -> (api_type, url_env, key_env, default_url).
# api_type selects the chat-client dialect in src/provider_clients.py:
#   "openai"    -> OpenAI-compatible (OpenAI/Ollama/Groq/OpenRouter/...; also
#                  Google Gemini via its /v1beta/openai compat URL).
#   "anthropic" -> Anthropic Messages API (anthropic SDK, optional).
#   "gemini"    -> Google Gemini native API (google-genai SDK, optional).
DEFAULT_PROVIDERS = {
    "openai":     ("openai",    "OPENAI_BASE_URL",     "OPENAI_API_KEY",     "https://api.openai.com/v1"),
    "ollama":     ("openai",    "OLLAMA_BASE_URL",     "OLLAMA_API_KEY",     "https://api.ollama.com/v1"),
    "qwen":       ("openai",    "QWEN_BASE_URL",       "QWEN_API_KEY",       "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"),
    "groq":       ("openai",    "GROQ_BASE_URL",       "GROQ_API_KEY",       "https://api.groq.com/openai/v1"),
    "openrouter": ("openai",    "OPENROUTER_BASE_URL", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"),
    "cerebras":   ("openai",    "CEREBRAS_BASE_URL",   "CEREBRAS_API_KEY",   "https://api.cerebras.ai/v1"),
    "hf":         ("openai",    "HF_BASE_URL",         "HF_TOKEN",           "https://router.huggingface.co/v1"),
    "together":   ("openai",    "TOGETHER_BASE_URL",   "TOGETHER_API_KEY",   "https://api.together.xyz/v1"),
    "mistral":    ("openai",    "MISTRAL_BASE_URL",    "MISTRAL_API_KEY",    "https://api.mistral.ai/v1"),
    "deepinfra":  ("openai",    "DEEPINFRA_BASE_URL",  "DEEPINFRA_API_KEY",  "https://api.deepinfra.com/v1"),
    "fireworks":  ("openai",    "FIREWORKS_BASE_URL",  "FIREWORKS_API_KEY",  "https://api.fireworks.ai/inference/v1"),
    "novita":     ("openai",    "NOVITA_BASE_URL",     "NOVITA_API_KEY",     "https://api.novita.ai/v3/openai"),
    "perplexity": ("openai",    "PERPLEXITY_BASE_URL", "PERPLEXITY_API_KEY", "https://api.perplexity.ai"),
    "cohere":     ("openai",    "COHERE_BASE_URL",     "COHERE_API_KEY",     "https://api.cohere.ai/compatibility/v1"),
    "glm":        ("openai",    "GLM_BASE_URL",        "GLM_API_KEY",        "https://api.z.ai/api/coding/paas/v4"),
    "poe":        ("openai",    "POE_BASE_URL",        "POE_API_KEY",        "https://api.poe.com/v1"),
    "vercel":     ("openai",    "VERCEL_BASE_URL",     "VERCEL_API_KEY",     "https://ai-gateway.vercel.com/v1"),
    "thinkingmachines": ("openai", "THINKING_MACHINES_BASE_URL", "THINKING_MACHINES_API_KEY", "https://api.thinkingmachines.ai/v1"),
    "gemini":     ("openai",    "GEMINI_BASE_URL",     "GEMINI_API_KEY",     "https://generativelanguage.googleapis.com/v1beta/openai"),
    "anthropic":  ("anthropic", "ANTHROPIC_BASE_URL",  "ANTHROPIC_API_KEY",  "https://api.anthropic.com"),
}

PROVIDERS = dict(DEFAULT_PROVIDERS)
try:
    _custom = _load_yaml(CONFIG_DIR / "custom_providers.yaml").get("providers", {})
    for k, v in _custom.items():
        if isinstance(v, list) and len(v) >= 4:
            PROVIDERS[k] = (v[0], v[1], v[2], v[3])
except Exception:
    pass


def provider_api_type(provider_name: str) -> str:
    name = provider_name.lower().strip()
    return PROVIDERS[name][0] if name in PROVIDERS else "openai"


def get_provider_credentials(provider_name: str) -> tuple[str, str]:
    name = provider_name.lower().strip()
    if name not in PROVIDERS:
        name = "ollama"
    _api_type, url_var, key_var, default_url = PROVIDERS[name]
    url = os.environ.get(url_var, default_url).strip().rstrip("/")
    key = os.environ.get(key_var, "").strip()
    if not key and name == "ollama":
        key = os.environ.get("OLLAMA_API_KEY", "").strip()
    return url, key

