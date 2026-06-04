"""Central configuration, loaded from environment with a tiny built-in ``.env``
reader (no python-dotenv dependency required).

CertMesh is cloud-OPTIONAL. With nothing configured it runs fully offline:
deterministic agents, a local vector index that honours the same retrieve-and-
cite contract as Foundry IQ, and the public Microsoft Learn MCP server. Set the
``AZURE_AI_*`` / ``AZURE_SEARCH_*`` values to light up the real Microsoft
Foundry paths. See docs/iq-layers.md and .env.example.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Minimal ``.env`` loader: ``KEY=value`` lines, ``#`` comments, optional
    surrounding quotes. Does not overwrite variables already in the environment."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _first_env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default


@dataclass(frozen=True)
class Config:
    # Model backend
    model_backend: str = "auto"          # auto | foundry | offline
    project_endpoint: str = ""
    model_deployment: str = "gpt-4o"
    api_key: str = ""

    # Foundry IQ / Azure AI Search
    search_endpoint: str = ""
    search_api_key: str = ""
    search_index: str = "certmesh-knowledge"

    # Microsoft Learn MCP
    mcp_enabled: bool = True
    mcp_endpoint: str = "https://learn.microsoft.com/api/mcp"

    # Observability
    appinsights_connection_string: str = ""
    trace_to_console: bool = False

    # Data
    data_dir: Path = _REPO_ROOT / "data"

    @property
    def foundry_configured(self) -> bool:
        """True if a model endpoint is available (key or managed identity)."""
        return bool(self.project_endpoint)

    @property
    def search_configured(self) -> bool:
        return bool(self.search_endpoint)


@lru_cache(maxsize=1)
def load_config() -> Config:
    _load_dotenv(_REPO_ROOT / ".env")

    def _bool(name: str, default: bool) -> bool:
        v = os.environ.get(name)
        if v is None:
            return default
        return v.strip().lower() in ("1", "true", "yes", "on")

    data_dir = os.environ.get("CERTMESH_DATA_DIR")
    return Config(
        model_backend=_first_env("CERTMESH_MODEL_BACKEND", default="auto").lower(),
        project_endpoint=_first_env("AZURE_AI_PROJECT_ENDPOINT", "PROJECT_ENDPOINT"),
        model_deployment=_first_env("AZURE_AI_MODEL_DEPLOYMENT", default="gpt-4o"),
        api_key=_first_env("AZURE_AI_API_KEY", "AZURE_OPENAI_API_KEY"),
        search_endpoint=_first_env("AZURE_SEARCH_ENDPOINT"),
        search_api_key=_first_env("AZURE_SEARCH_API_KEY"),
        search_index=_first_env("AZURE_SEARCH_INDEX", default="certmesh-knowledge"),
        mcp_enabled=_bool("CERTMESH_MCP_ENABLED", True),
        mcp_endpoint=_first_env("CERTMESH_MCP_ENDPOINT",
                                default="https://learn.microsoft.com/api/mcp"),
        appinsights_connection_string=_first_env("APPLICATIONINSIGHTS_CONNECTION_STRING"),
        trace_to_console=_bool("CERTMESH_TRACE_TO_CONSOLE", False),
        data_dir=Path(data_dir) if data_dir else _REPO_ROOT / "data",
    )
