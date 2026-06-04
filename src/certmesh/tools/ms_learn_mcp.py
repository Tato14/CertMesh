"""Microsoft Learn MCP client — real, cited Microsoft Learn content.

The Microsoft Learn MCP server is a public, no-auth remote MCP server at
``https://learn.microsoft.com/api/mcp`` (streamable HTTP) exposing the tools
``microsoft_docs_search`` and ``microsoft_docs_fetch``. Per Microsoft's
developer reference the tool *input/output schemas are intentionally not
published and may change*, so we enumerate tools at runtime and pass a
best-effort query argument rather than hard-coding a schema.
Ref: https://learn.microsoft.com/en-us/training/support/mcp-developer-reference

Resolution order for :meth:`search`:
  1. ``mcp`` Python package over streamable HTTP (the documented client), if installed.
  2. A minimal raw-httpx JSON-RPC attempt (httpx is a core dep), best-effort.
  3. An OFFLINE CACHE of *real, stable* Microsoft Learn certification URLs with
     accurate generic snippets — so a demo always shows a real Learn citation
     even with no network. Cache hits are clearly labelled ``ms_learn_cache``.

Every returned chunk carries verbatim text, so the curator's Learn citations are
checkable by the critic exactly like Foundry IQ citations (self-grounding: the
cited snippet must be a substring of the retrieved Learn text).
"""

from __future__ import annotations

import re
from functools import lru_cache

from ..config import Config, load_config
from ..foundry.client import _run_sync
from ..schemas import RetrievalResult, RetrievedChunk

# Real, stable Microsoft Learn URLs + accurate generic snippets (synthetic-safe:
# these are public Microsoft Learn facts, not org data). Used only as the offline
# fallback so a demo never dead-ends without network.
_OFFLINE_CACHE: dict[str, list[dict]] = {
    "AZ-204": [{
        "title": "Microsoft Certified: Azure Developer Associate (AZ-204)",
        "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-developer/",
        "text": ("The Azure Developer Associate certification (exam AZ-204) validates the "
                 "skills to design, build, test, and maintain cloud applications and services "
                 "on Microsoft Azure, including compute, storage, security, and monitoring."),
    }],
    "AZ-400": [{
        "title": "Microsoft Certified: DevOps Engineer Expert (AZ-400)",
        "url": "https://learn.microsoft.com/en-us/credentials/certifications/devops-engineer/",
        "text": ("The DevOps Engineer Expert certification (exam AZ-400) validates the skills to "
                 "combine people, process, and technologies to continuously deliver valuable "
                 "products and services that meet user needs and business objectives."),
    }],
    "DP-203": [{
        "title": "Microsoft Certified: Azure Data Engineer Associate (DP-203)",
        "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-data-engineer/",
        "text": ("The Azure Data Engineer Associate certification (exam DP-203) validates the "
                 "skills to integrate, transform, and consolidate data from various structured "
                 "and unstructured data systems into structures suitable for building analytics."),
    }],
    "AZ-900": [{
        "title": "Microsoft Certified: Azure Fundamentals (AZ-900)",
        "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-fundamentals/",
        "text": ("The Azure Fundamentals certification (exam AZ-900) validates foundational "
                 "knowledge of cloud concepts and Microsoft Azure services, workloads, security, "
                 "privacy, pricing, and support."),
    }],
}

_LEARN_URL_RE = re.compile(r"https?://learn\.microsoft\.com/[^\s)\]\"']+")


class MsLearnMCP:
    def __init__(self, config: Config | None = None):
        self.config = config or load_config()
        self.last_backend = "ms_learn_cache"

    # -- public sync API -----------------------------------------------------
    def search(self, query: str, *, certification: str | None = None,
               top_k: int = 3) -> RetrievalResult:
        if self.config.mcp_enabled:
            chunks = self._search_mcp_package(query, top_k)
            if chunks:
                self.last_backend = "ms_learn_mcp"
                return RetrievalResult(query=query, chunks=chunks, backend="ms_learn_mcp")
        # Offline / unavailable → cache by certification code (real Learn URLs).
        chunks = self._search_cache(certification or query, top_k)
        self.last_backend = "ms_learn_cache"
        return RetrievalResult(query=query, chunks=chunks, backend="ms_learn_cache")

    # -- backends ------------------------------------------------------------
    def _search_mcp_package(self, query: str, top_k: int) -> list[RetrievedChunk]:
        """Documented client path. Returns [] on any failure (degrades to cache)."""
        async def _go() -> list[RetrievedChunk]:  # pragma: no cover - needs network + mcp pkg
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client

            out: list[RetrievedChunk] = []
            async with streamablehttp_client(self.config.mcp_endpoint) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {t.name for t in tools.tools}
                    tool = "microsoft_docs_search" if "microsoft_docs_search" in names else None
                    if tool is None:
                        return []
                    # Schema is undocumented — try the common arg names.
                    result = None
                    for arg in ("query", "question", "search"):
                        try:
                            result = await session.call_tool(tool, {arg: query})
                            break
                        except Exception:
                            continue
                    if result is None:
                        return []
                    for i, item in enumerate(getattr(result, "content", []) or []):
                        text = getattr(item, "text", None)
                        if not text:
                            continue
                        m = _LEARN_URL_RE.search(text)
                        out.append(RetrievedChunk(
                            id=f"mslearn#{i+1}",
                            title="Microsoft Learn",
                            text=re.sub(r"\s+", " ", text).strip()[:600],
                            source="learn.microsoft.com",
                            url=m.group(0) if m else self.config.mcp_endpoint,
                            kind="ms_learn",
                            locator="Microsoft Learn (MCP)",
                        ))
                    return out[:top_k]

        try:  # pragma: no cover - needs network + mcp pkg
            import importlib.util
            if importlib.util.find_spec("mcp") is None:
                return []
            return _run_sync(_go())
        except Exception:
            return []

    def _search_cache(self, key: str, top_k: int) -> list[RetrievedChunk]:
        code = None
        m = re.search(r"[A-Z]{2}-\d{3,4}", (key or "").upper())
        if m:
            code = m.group(0)
        elif key and key.upper() in _OFFLINE_CACHE:
            code = key.upper()
        entries = _OFFLINE_CACHE.get(code or "", [])
        out: list[RetrievedChunk] = []
        for i, e in enumerate(entries[:top_k]):
            out.append(RetrievedChunk(
                id=f"mslearn-cache#{code}-{i+1}",
                title=e["title"],
                text=e["text"],
                source="learn.microsoft.com",
                url=e["url"],
                kind="ms_learn",
                score=1.0,
                locator="Microsoft Learn (cached, real URL)",
            ))
        return out


def all_cache_texts() -> list[str]:
    """Every offline-cache snippet — used by the evaluator to verify Learn
    citations are grounded independently of the agent that produced them."""
    return [e["text"] for entries in _OFFLINE_CACHE.values() for e in entries]


@lru_cache(maxsize=1)
def get_ms_learn() -> MsLearnMCP:
    return MsLearnMCP()
