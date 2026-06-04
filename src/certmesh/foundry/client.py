"""Model backend abstraction: Microsoft Foundry (via the Microsoft Agent
Framework) with a deterministic offline fallback.

Design principle (see docs/responsible-ai.md): the language model is used ONLY
for natural-language *generation* — explanatory prose, localised learner-facing
text and question phrasing. Every correctness- and safety-critical decision
(agent routing, capacity-fit arithmetic, the grounding/citation guard, readiness
scoring against thresholds, the manager PII filter) is made deterministically by
the pipeline and can never be produced or overridden by the model. That is why
CertMesh stays correct, testable and CI-gated even with no model at all.

APIs verified June 2026 against:
  - https://learn.microsoft.com/en-us/agent-framework/overview/
  - https://learn.microsoft.com/en-us/agent-framework/get-started/your-first-agent
  - https://learn.microsoft.com/en-us/agent-framework/support/upgrade/python-2026-significant-changes
  - https://learn.microsoft.com/en-us/azure/foundry/quickstarts/get-started-code
The 2026 reorg: client is ``agent_framework.foundry.FoundryChatClient`` (ctor
param ``model``, not ``model_id``); agents are created with the top-level
``Agent(client=..., instructions=...)`` class (``client.as_agent()`` was removed)
and awaited via ``agent.run(...)``.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from abc import ABC, abstractmethod

from ..config import Config, load_config


class ModelUnavailable(Exception):
    """Raised when a real language model cannot be reached. Callers degrade to
    deterministic templates rather than failing the task."""


def _run_sync(coro):
    """Run an async coroutine to completion from sync code, even if an event
    loop is already running (e.g. inside FastAPI) by using a worker thread."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


class ModelBackend(ABC):
    name: str = "abstract"
    available: bool = False

    @abstractmethod
    def generate(self, system: str, user: str, *, temperature: float = 0.0,
                 max_tokens: int = 512) -> str:
        ...


class OfflineStubBackend(ModelBackend):
    """No language model. The pipeline falls back to deterministic templates;
    decisions are unaffected because they are deterministic anyway."""

    name = "offline_stub"
    available = False

    def generate(self, system: str, user: str, *, temperature: float = 0.0,
                 max_tokens: int = 512) -> str:
        raise ModelUnavailable("No model configured — running offline stub.")


class FoundryBackend(ModelBackend):
    """Calls a model deployed in Microsoft Foundry through the Agent Framework.

    Uses ``FoundryChatClient`` with Entra ID (``DefaultAzureCredential``) by
    default; if an API key is supplied, uses the OpenAI-compatible client.
    """

    name = "foundry"
    available = True

    def __init__(self, config: Config):
        self._config = config
        self._client = None
        self._agents: dict[str, object] = {}
        self._init_client()

    def _init_client(self) -> None:
        cfg = self._config
        try:
            if cfg.api_key:
                # OpenAI-compatible path (API key on the Foundry endpoint).
                # https://learn.microsoft.com/en-us/agent-framework/overview/
                from agent_framework.openai import OpenAIChatClient  # type: ignore

                self._client = OpenAIChatClient(
                    base_url=cfg.project_endpoint,
                    api_key=cfg.api_key,
                    model_id=cfg.model_deployment,
                )
            else:
                # Entra ID path (recommended). Run `az login` or use a managed
                # identity. Param is `model` as of the 2026 rename.
                from agent_framework.foundry import FoundryChatClient  # type: ignore
                from azure.identity import DefaultAzureCredential  # type: ignore

                self._client = FoundryChatClient(
                    project_endpoint=cfg.project_endpoint,
                    model=cfg.model_deployment,
                    credential=DefaultAzureCredential(),
                )
        except Exception as exc:  # ImportError or auth/config error
            raise ModelUnavailable(f"Could not initialise Foundry client: {exc}") from exc

    def _get_agent(self, system: str):
        agent = self._agents.get(system)
        if agent is None:
            try:
                from agent_framework import Agent  # type: ignore

                agent = Agent(
                    client=self._client,
                    name="certmesh-narrator",
                    instructions=system,
                )
            except Exception as exc:  # pragma: no cover - needs live SDK
                raise ModelUnavailable(f"Could not create agent: {exc}") from exc
            self._agents[system] = agent
        return agent

    def generate(self, system: str, user: str, *, temperature: float = 0.0,
                 max_tokens: int = 512) -> str:
        async def _go() -> str:
            agent = self._get_agent(system)
            result = await agent.run(user)  # type: ignore[attr-defined]
            # AgentRunResponse stringifies to its text content.
            return str(getattr(result, "text", result)).strip()

        try:
            return _run_sync(_go())
        except ModelUnavailable:
            raise
        except Exception as exc:  # pragma: no cover - needs live SDK
            raise ModelUnavailable(f"Foundry generation failed: {exc}") from exc


def get_model_backend(config: Config | None = None) -> ModelBackend:
    """Factory honouring CERTMESH_MODEL_BACKEND (auto | foundry | offline)."""
    cfg = config or load_config()
    mode = (cfg.model_backend or "auto").lower()

    if mode == "offline":
        return OfflineStubBackend()
    if mode == "foundry":
        # Explicitly requested: surface init errors instead of silently degrading.
        return FoundryBackend(cfg)
    # auto
    if cfg.foundry_configured:
        try:
            return FoundryBackend(cfg)
        except ModelUnavailable:
            return OfflineStubBackend()
    return OfflineStubBackend()
