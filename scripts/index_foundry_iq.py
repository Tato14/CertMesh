"""Create (or refresh) the Azure AI Search index that backs Foundry IQ and upload
the chunked ``data/knowledge/`` corpus.

This is the one-time indexing step for the *real* Foundry IQ path. It reuses the
exact same chunker the local BM25 index uses (``foundry_iq._chunk_markdown``), so
the retrieve-and-cite contract — and therefore the grounding guarantee — is
identical whether CertMesh retrieves from Azure AI Search or the local fallback.

Requires the ``[azure]`` extra and these env vars (or a ``.env``):
    AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX (default certmesh-knowledge)

Run:
    PYTHONPATH=src ./.venv/bin/python scripts/index_foundry_iq.py
"""

from __future__ import annotations

import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)

from certmesh.config import load_config
from certmesh.iq.foundry_iq import _chunk_markdown


def _index_schema(name: str) -> SearchIndex:
    return SearchIndex(
        name=name,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="locator", type=SearchFieldDataType.String),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="url", type=SearchFieldDataType.String),
            SimpleField(name="kind", type=SearchFieldDataType.String, filterable=True),
        ],
    )


def main() -> int:
    cfg = load_config()
    if not (cfg.search_endpoint and cfg.search_api_key):
        print("ERROR: set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY (.env).")
        return 2
    cred = AzureKeyCredential(cfg.search_api_key)

    # 1) (re)create the index
    idx_client = SearchIndexClient(endpoint=cfg.search_endpoint, credential=cred)
    try:
        idx_client.delete_index(cfg.search_index)
        print(f"deleted existing index '{cfg.search_index}'")
    except Exception:
        pass
    idx_client.create_index(_index_schema(cfg.search_index))
    print(f"created index '{cfg.search_index}'")

    # 2) chunk data/knowledge/ exactly like the local Foundry IQ index
    kb = cfg.data_dir / "knowledge"
    docs = []
    for path in sorted(kb.glob("*.md")):
        for c in _chunk_markdown(path):
            docs.append({
                "id": c.id.replace("#", "_"),   # '#' is illegal in a Search key
                "title": c.title,
                "content": c.text,              # verbatim — preserves grounding
                "locator": c.locator,
                "source": c.source,
                "url": c.url or "",
                "kind": "foundry_iq",
            })
    if not docs:
        print(f"ERROR: no chunks found under {kb}")
        return 2

    # 3) upload
    search = SearchClient(endpoint=cfg.search_endpoint, index_name=cfg.search_index, credential=cred)
    result = search.upload_documents(documents=docs)
    ok = sum(1 for r in result if r.succeeded)
    print(f"uploaded {ok}/{len(docs)} chunks to '{cfg.search_index}'")
    return 0 if ok == len(docs) else 1


if __name__ == "__main__":
    sys.exit(main())
