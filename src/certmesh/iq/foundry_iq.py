"""Foundry IQ — the required, real IQ layer: a knowledge base with agentic
retrieve-and-cite.

Two interchangeable backends behind one contract (:meth:`FoundryIQ.retrieve`
returns a :class:`RetrievalResult` of verbatim, citable chunks):

* **Azure AI Search** (``backend == "azure_search"``) — used when
  ``AZURE_SEARCH_ENDPOINT`` is configured. This mirrors how Foundry IQ indexes a
  knowledge source. In a full Foundry deployment the knowledge base is consumed
  by an agent through the ``knowledge_base_retrieve`` MCP tool exposed at
  ``{search_endpoint}/knowledgebases/{kb}/mcp?api-version=2026-05-01-preview``
  (see docs/iq-layers.md and deploy/deploy_hosted_agent.md). We keep the same
  retrieve-and-cite contract here so the agents are identical either way.
  Ref: https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/foundry-iq-connect

* **Local index** (``backend == "local"``) — a dependency-free BM25 index over
  data/knowledge/. This is the default so the system runs and is CI-gateable with
  zero cloud provisioning, while honouring the identical citation contract.

The citation contract: every returned chunk carries the *verbatim* source text,
so any agent claim that cites a chunk can be checked — by the critic — for being
an actual substring of a retrieved source (:func:`supports`). That is what makes
the grounding rate a hard, testable gate.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

from ..config import Config, load_config
from ..matching import fold
from ..schemas import RetrievalResult, RetrievedChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "is", "are",
    "be", "with", "that", "this", "it", "as", "at", "by", "so", "can", "you",
    "your", "how", "what", "which", "i", "want", "need", "study", "learn",
    "prepare", "preparing", "cert", "certification", "exam", "module", "modules",
}


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(fold(text)) if t not in _STOPWORDS]


# ───────────────────────────── markdown chunking ───────────────────────────

def _clean_unit(text: str) -> str:
    text = text.lstrip("-* ").strip()
    text = text.replace("**", "")
    return re.sub(r"\s+", " ", text).strip()


def _chunk_markdown(path: Path) -> list[RetrievedChunk]:
    """Split a knowledge doc into fine-grained, citable units.

    A bullet line is one unit; consecutive prose lines form one unit. Each unit
    inherits its parent ``##`` heading as the ``title`` (so e.g. the cert code
    is searchable and shown) and its ``###`` heading in the locator, so a
    citation points at a precise place in a precise document.
    """
    raw = _HTML_COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
    doc_title = path.stem
    chunks: list[RetrievedChunk] = []
    h2 = doc_title
    h3 = ""
    para: list[str] = []
    counter = 0

    def emit(unit: str) -> None:
        nonlocal counter
        if len(unit) < 12:
            return
        counter += 1
        locator = f"{doc_title} › {h2}" + (f" › {h3}" if h3 else "")
        # search_text folds in the subsection so a "{cert} {skill}" query ranks
        # the right unit; the citation text stays the verbatim unit.
        chunks.append(RetrievedChunk(
            id=f"{doc_title}#{counter}",
            title=h2,
            text=unit,
            source=path.name,
            kind="foundry_iq",
            locator=locator,
        ))

    def flush_para() -> None:
        nonlocal para
        if para:
            emit(_clean_unit(" ".join(para)))
            para = []

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_para()
            continue
        if stripped.startswith("## "):
            flush_para()
            h2 = stripped.lstrip("# ").strip()
            h3 = ""
            continue
        if stripped.startswith("#"):
            flush_para()
            h3 = stripped.lstrip("# ").strip()
            continue
        if stripped.startswith(("- ", "* ")):
            flush_para()
            emit(_clean_unit(stripped))
            continue
        para.append(stripped)
    flush_para()
    return chunks


# ──────────────────────────────── BM25 index ───────────────────────────────

class _BM25Index:
    def __init__(self, chunks: list[RetrievedChunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        # searchable text = heading + body so the cert code in the heading boosts
        # the right chunks for a "{cert} {skill}" query.
        self._docs = [_tokenize(f"{c.title} {c.text}") for c in chunks]
        self._dl = [len(d) for d in self._docs]
        self._avgdl = (sum(self._dl) / len(self._dl)) if self._dl else 0.0
        self._df: dict[str, int] = {}
        for d in self._docs:
            for term in set(d):
                self._df[term] = self._df.get(term, 0) + 1
        self._n = len(chunks)
        self._tf: list[dict[str, int]] = []
        for d in self._docs:
            tf: dict[str, int] = {}
            for term in d:
                tf[term] = tf.get(term, 0) + 1
            self._tf.append(tf)

    def _idf(self, term: str) -> float:
        df = self._df.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(1 + (self._n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int) -> list[tuple[float, RetrievedChunk]]:
        q_terms = _tokenize(query)
        if not q_terms:
            return []
        scored: list[tuple[float, RetrievedChunk]] = []
        for i, chunk in enumerate(self.chunks):
            tf = self._tf[i]
            dl = self._dl[i] or 1
            score = 0.0
            for term in q_terms:
                f = tf.get(term, 0)
                if f == 0:
                    continue
                idf = self._idf(term)
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self._avgdl or 1))
                score += idf * (f * (self.k1 + 1)) / denom
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]


# ───────────────────────────────── facade ──────────────────────────────────

class FoundryIQ:
    """Knowledge base with retrieve-and-cite. Prefers Azure AI Search; falls back
    to the local BM25 index over data/knowledge/."""

    def __init__(self, config: Config | None = None):
        self.config = config or load_config()
        self._chunks = self._load_chunks()
        self._index = _BM25Index(self._chunks)
        self._search_client = self._maybe_azure_search()
        self.backend = "azure_search" if self._search_client else "local"

    # -- loading -------------------------------------------------------------
    def _load_chunks(self) -> list[RetrievedChunk]:
        kb = self.config.data_dir / "knowledge"
        chunks: list[RetrievedChunk] = []
        if kb.exists():
            for path in sorted(kb.glob("*.md")):
                chunks.extend(_chunk_markdown(path))
        return chunks

    def _maybe_azure_search(self):
        if not self.config.search_configured:
            return None
        try:  # pragma: no cover - needs a live Azure AI Search instance
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient

            if self.config.search_api_key:
                cred = AzureKeyCredential(self.config.search_api_key)
            else:
                from azure.identity import DefaultAzureCredential
                cred = DefaultAzureCredential()
            return SearchClient(
                endpoint=self.config.search_endpoint,
                index_name=self.config.search_index,
                credential=cred,
            )
        except Exception:
            # Any import/auth/config problem → degrade to the local index.
            return None

    # -- retrieval -----------------------------------------------------------
    def retrieve(self, query: str, *, top_k: int = 4, certification: str | None = None) -> RetrievalResult:
        """Return citable chunks for a query. If ``certification`` is given it is
        folded into the query so the right section is preferred."""
        full_query = f"{certification} {query}".strip() if certification else query
        if self._search_client is not None:
            chunks = self._search_azure(full_query, top_k)
            if chunks:
                return RetrievalResult(query=full_query, chunks=chunks, backend="azure_search")
            # empty Azure result → still try local so a demo never dead-ends.
        hits = self._index.search(full_query, top_k)
        chunks = []
        for score, chunk in hits:
            c = chunk.model_copy(update={"score": round(score, 4)})
            chunks.append(c)
        return RetrievalResult(query=full_query, chunks=chunks, backend="local")

    def _search_azure(self, query: str, top_k: int) -> list[RetrievedChunk]:
        client = self._search_client
        try:  # pragma: no cover - needs a live Azure AI Search instance
            results = client.search(search_text=query, top=top_k)
            out: list[RetrievedChunk] = []
            for r in results:
                out.append(RetrievedChunk(
                    id=str(r.get("id") or r.get("chunk_id") or r.get("title", "")),
                    title=str(r.get("title", "Knowledge base")),
                    text=str(r.get("content") or r.get("text", "")),
                    source=str(r.get("source", self.config.search_index)),
                    url=r.get("url"),
                    kind="foundry_iq",
                    score=float(r.get("@search.score", 0.0)),
                    locator=str(r.get("locator") or r.get("title", "")),
                ))
            return out
        except Exception:
            return []

    # -- introspection for the critic / trace --------------------------------
    @property
    def all_chunk_texts(self) -> list[str]:
        return [c.text for c in self._chunks]

    def known_certifications(self) -> set[str]:
        codes: set[str] = set()
        for c in self._chunks:
            m = re.match(r"([A-Z]{2,}-[A-Z0-9-]+)", c.title)
            if m:
                codes.add(m.group(1))
        return codes


def supports(snippet: str, source_texts: list[str]) -> bool:
    """True if ``snippet`` is grounded in some source text (accent/case-insensitive
    substring). Used by the critic to verify a citation is real."""
    if not snippet:
        return False
    needle = re.sub(r"\s+", " ", fold(snippet)).strip()
    if len(needle) < 8:
        return False
    for src in source_texts:
        hay = re.sub(r"\s+", " ", fold(src)).strip()
        if needle in hay:
            return True
    return False


@lru_cache(maxsize=1)
def get_foundry_iq() -> FoundryIQ:
    return FoundryIQ()
