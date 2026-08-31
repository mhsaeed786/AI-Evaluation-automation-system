"""
Centralized Configuration Settings for HealthOS BA/QA Automation Suite.

All database credentials, API keys, paths, and runtime settings are managed here.
Sensitive values are loaded from environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Configuration for a single database connection."""
    server: str
    database: str
    username: str
    password: str
    driver: str = "{ODBC Driver 17 for SQL Server}"
    timeout: int = 30

    @property
    def connection_string(self) -> str:
        return (
            f"DRIVER={self.driver};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout={self.timeout};"
        )


@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    api_key_env: str
    default_model: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    max_tokens: int
    base_url: Optional[str] = None


@dataclass
class PathConfig:
    """File system path configuration."""
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    data_dir: Path = field(default=None)
    output_dir: Path = field(default=None)
    logs_dir: Path = field(default=None)

    def __post_init__(self):
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"
        if self.output_dir is None:
            self.output_dir = self.base_dir / "output"
        if self.logs_dir is None:
            self.logs_dir = self.base_dir / "logs"
        for d in [self.data_dir, self.output_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)


class Settings:
    """Centralized application settings singleton."""

    _instance: Optional["Settings"] = None

    def __new__(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.paths = PathConfig()
        self._init_databases()
        self._init_llm_providers()
        self._init_urls()
        self._init_file_mappings()

    def _init_databases(self):
        """Initialize all database connection configurations."""
        self.databases: Dict[str, DatabaseConfig] = {
            "release01_fhir": DatabaseConfig(
                server="APP_SERVER_10G",
                database="FHIR_DB",
                username=os.getenv("DB_USER_RELEASE01", ""),
                password=os.getenv("DB_PASS_RELEASE01", ""),
            ),
            "release01_muii": DatabaseConfig(
                server="APP_SERVER_10G",
                database="MUII_DB",
                username=os.getenv("DB_USER_RELEASE01", ""),
                password=os.getenv("DB_PASS_RELEASE01", ""),
            ),
            "baseline11x_muii": DatabaseConfig(
                server="APP_SERVER_11X",
                database="MUII_DB",
                username=os.getenv("DB_USER_BASELINE11X", ""),
                password=os.getenv("DB_PASS_BASELINE11X", ""),
            ),
            "baseline11x_fhir": DatabaseConfig(
                server="APP_SERVER_11X",
                database="FHIR_DB",
                username=os.getenv("DB_USER_BASELINE11X", ""),
                password=os.getenv("DB_PASS_BASELINE11X", ""),
            ),
        }

    def _init_llm_providers(self):
        """Initialize LLM provider configurations with cost ranking."""
        self.llm_providers: Dict[str, LLMProviderConfig] = {
            "openai": LLMProviderConfig(
                name="OpenAI",
                api_key_env="OPENAI_API_KEY",
                default_model="gpt-4o",
                cost_per_1k_input=0.0025,
                cost_per_1k_output=0.01,
                max_tokens=128000,
            ),
            "anthropic": LLMProviderConfig(
                name="Anthropic",
                api_key_env="ANTHROPIC_API_KEY",
                default_model=os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-20250514"),
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                max_tokens=200000,
                base_url=os.getenv("ANTHROPIC_BASE_URL"),
            ),
            "gemini": LLMProviderConfig(
                name="Google Gemini",
                api_key_env="GEMINI_API_KEY",
                default_model="gemini-2.0-flash",
                cost_per_1k_input=0.000075,
                cost_per_1k_output=0.0003,
                max_tokens=1048576,
            ),
            "deepseek": LLMProviderConfig(
                name="DeepSeek",
                api_key_env="DEEPSEEK_API_KEY",
                default_model="deepseek-chat",
                cost_per_1k_input=0.00014,
                cost_per_1k_output=0.00028,
                max_tokens=128000,
                base_url="https://api.deepseek.com/v1",
            ),
            "ollama": LLMProviderConfig(
                name="Ollama (Local)",
                api_key_env="OLLAMA_HOST",
                default_model="llama3.1:8b",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                max_tokens=128000,
                base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ),
            "groq": LLMProviderConfig(
                name="Groq",
                api_key_env="GROQ_API_KEY",
                default_model="llama-3.3-70b-versatile",
                cost_per_1k_input=0.00059,
                cost_per_1k_output=0.00079,
                max_tokens=131072,
                base_url="https://api.groq.com/openai/v1",
            ),
            "mistral": LLMProviderConfig(
                name="Mistral AI",
                api_key_env="MISTRAL_API_KEY",
                default_model="mistral-large-latest",
                cost_per_1k_input=0.002,
                cost_per_1k_output=0.006,
                max_tokens=128000,
                base_url="https://api.mistral.ai/v1",
            ),
            "cohere": LLMProviderConfig(
                name="Cohere",
                api_key_env="COHERE_API_KEY",
                default_model="command-r-plus",
                cost_per_1k_input=0.0025,
                cost_per_1k_output=0.01,
                max_tokens=128000,
                base_url="https://api.cohere.ai/v1",
            ),
        }

        # Sorted by cost (cheapest first) for fallback chains
        self.provider_fallback_order = sorted(
            self.llm_providers.keys(),
            key=lambda k: self.llm_providers[k].cost_per_1k_input
            if self.llm_providers[k].cost_per_1k_input > 0
            else 999.0,
        )

    def _init_urls(self):
        """Initialize external service URLs."""
        self.urls = {
            "sharepoint_base": "https://example.sharepoint.com/sites/ApplicationImprovementsTeam/",
            "sharepoint_attachments": "https://example.sharepoint.com/sites/ApplicationImprovementsTeam/Shared%20Documents/",
            "azure_devops": "https://devops.example.com/HealthOS10g/11g",
            "azure_devops_10g": "https://devops.example.com/HealthOS10g",
            "azure_devops_11g": "https://devops.example.com/HealthOS11g",
            "fhir_server_r4": "http://hapi.fhir.org/baseR4",
            "fhir_server_healthos": os.getenv("FHIR_SERVER_URL", "https://fhir.example.com/fhir"),
            "terminology_server": "https://r4.ontoserver.csiro.au/fhir",
            "snomed_browser": "https://browser.ihtsdotools.org",
            "hl7_fhir_base": "https://hl7.org/fhir/R4",
        }

    def _init_file_mappings(self):
        """Initialize file path mappings from Hassan's super-prompt."""
        self.file_mappings = {
            "trigger_folder": r"\\example.com\HealthOSData\ApplicationImprovementTeam\analyst\BA-QA Automation\FHIR Triggers",
            "mapping_folder": r"\\example.com\HealthOSData\ApplicationImprovementTeam\analyst\BA-QA Automation\FHIR Mapping",
            "uscdi_folder": r"\\example.com\HealthOSData\ApplicationImprovementTeam\analyst\BA-QA Automation\USCDI V3",
            "provenance_folder": r"\\example.com\HealthOSData\ApplicationImprovementTeam\analyst\BA-QA Automation\Provenance",
            "scope_folder": r"\\example.com\HealthOSData\ApplicationImprovementTeam\analyst\BA-QA Automation\Scopes",
            "report_output": str(self.paths.output_dir),
            "gap_analysis_folder": r"\\example.com\HealthOSData\ApplicationImprovementTeam\analyst\BA-QA Automation\Gap Analysis",
        }

    def get_db_config(self, key: str) -> DatabaseConfig:
        """Get a specific database configuration by key."""
        if key not in self.databases:
            raise ValueError(
                f"Unknown database key: {key}. Available: {list(self.databases.keys())}"
            )
        return self.databases[key]

    def get_llm_api_key(self, provider: str) -> Optional[str]:
        """Get the API key for a given LLM provider."""
        if provider not in self.llm_providers:
            return None
        env_var = self.llm_providers[provider].api_key_env
        return os.getenv(env_var)

    def get_url(self, key: str) -> str:
        """Get a configured URL by key."""
        return self.urls.get(key, "")

    def get_file_path(self, key: str) -> str:
        """Get a configured file path by key."""
        return self.file_mappings.get(key, "")

    def get_all_provider_status(self) -> Dict[str, Dict]:
        """Get availability status for all LLM providers."""
        status = {}
        for key, cfg in self.llm_providers.items():
            api_key = os.getenv(cfg.api_key_env)
            status[key] = {
                "name": cfg.name,
                "model": cfg.default_model,
                "available": api_key is not None and api_key != "",
                "cost_per_1k_input": cfg.cost_per_1k_input,
                "cost_per_1k_output": cfg.cost_per_1k_output,
            }
        return status


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global Settings singleton."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
