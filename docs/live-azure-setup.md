# Running CertMesh live on Microsoft Foundry (developer setup)

CertMesh runs **fully offline by default** (deterministic agents + local BM25
index + public MCP). This guide documents the **exact** steps to light up the
**real** Microsoft Foundry path — the Microsoft Agent Framework model backend and
(optionally) Foundry IQ over Azure AI Search — so another developer can reproduce
the environment from scratch.

> Everything here is *additive*. If any cloud piece is missing or misconfigured,
> CertMesh degrades gracefully to the offline path (see `foundry/client.py` and
> `iq/foundry_iq.py`). You can always go back to offline by emptying `.env`.

Verified on: **macOS (Apple Silicon, arm64)**, **Python 3.13**, June 2026.

---

## 0. What gets installed (summary)

| Layer | Tool / package | Version (pinned at setup) | How |
|---|---|---|---|
| Azure CLI | `azure-cli` | **2.87.0** | `brew install azure-cli` |
| Python env | project-local virtualenv | — | `python -m venv .venv` |
| Agent Framework | `agent-framework` (+ `-foundry`, `-openai`) | **1.8.0** | `pip install -e ".[azure,dev,i18n]"` |
| Foundry projects SDK | `azure-ai-projects` | **2.2.0** | (same extra) |
| Auth | `azure-identity` | **1.25.3** | (same extra) |
| Foundry IQ search | `azure-search-documents` | **11.7.0b2** | (same extra) |
| Managed evaluators | `azure-ai-evaluation` | **1.17.0** | (same extra) |
| MCP client | `mcp` | **1.27.2** | (same extra) |
| Tracing | `azure-monitor-opentelemetry` | **1.8.8** | (same extra) |

The full pinned dependency set is in `pyproject.toml` under
`[project.optional-dependencies].azure`.

---

## 1. macOS toolchain

### 1.1 Azure CLI

```bash
brew install azure-cli        # installs azure-cli 2.87.0 + deps
az version                    # verify
```

### 1.2 Python virtual environment (recommended — avoids global conflicts)

We install the heavy Azure SDKs into a **project-local `.venv`**, not the global
interpreter. (Installing globally previously downgraded `pytest` and broke an
unrelated global `pytest-env`; a venv isolates CertMesh cleanly.)

```bash
cd CertMesh
python -m venv .venv
./.venv/bin/python -m pip install -U pip
./.venv/bin/python -m pip install -e ".[azure,dev,i18n]"
```

`.venv/` is ignored by git — never commit it.

### 1.3 Verify the SDKs import and match CertMesh's code

```bash
./.venv/bin/python - <<'PY'
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.search.documents import SearchClient
print("all Foundry / Agent Framework import paths OK")
PY
```

All six paths must print OK — they are exactly what `src/certmesh/foundry/client.py`
and `src/certmesh/iq/foundry_iq.py` import.

---

## 2. Azure account + sign in (interactive — done by the developer)

1. Create a free Azure account: <https://azure.microsoft.com/free>
   (requires a credit card for identity verification; the free tier does not
   charge, and new accounts include $200 credit for 30 days).
2. Sign in from the CLI:
   ```bash
   az login
   az account show -o table          # confirm the active subscription
   ```

<!-- PROVISIONING SECTION (§3–§6) is completed below once the live resources are
     actually created, so the commands recorded here are the ones that ran. -->

## 3. Provision the Foundry resource + model deployment

These are the exact commands that provisioned the live environment (region
`swedencentral`, all names are examples — change them):

```bash
RG=certmesh-rg; LOC=swedencentral; ACCT=cmfoundrydp01

# 3.1 register providers (one-time per subscription; ~1-3 min to finish)
az provider register -n Microsoft.CognitiveServices
az provider register -n Microsoft.Search

# 3.2 resource group
az group create -n $RG -l $LOC

# 3.3 Azure AI Foundry (AIServices) resource — free to create, S0 = pay-per-token
az cognitiveservices account create \
  --name $ACCT --resource-group $RG --location $LOC \
  --kind AIServices --sku S0 --custom-domain $ACCT \
  --assign-identity --yes
```

### ⚠️ Free Trial quota gotcha (important)

On a **Free Trial** subscription (`quotaId: FreeTrial_2014-09-01`) the
`gpt-4o` **GlobalStandard** quota is **0**, so this fails with `InsufficientQuota`:

```bash
# FAILS on Free Trial — GlobalStandard quota = 0
az cognitiveservices account deployment create ... --sku-name GlobalStandard ...
```

But the **Standard** (regional) SKU has a non-zero default quota (50K TPM) and
works — and keeps data in-region, which is better for EU residency anyway. Check
your quotas with `az cognitiveservices usage list -l <region> -o table`. The
deployment that works:

```bash
# WORKS on Free Trial — Standard SKU, 10K TPM. (gpt-4o 2024-08-06 is deprecating;
# use 2024-11-20.)
az cognitiveservices account deployment create \
  --name $ACCT --resource-group $RG \
  --deployment-name gpt-4o \
  --model-name gpt-4o --model-version 2024-11-20 --model-format OpenAI \
  --sku-name Standard --sku-capacity 10
```

### 3.4 Foundry project + RBAC (required for the Entra path)

`agent_framework.foundry.FoundryChatClient` needs a **project** endpoint
(`…/api/projects/<project>`) and an Entra identity with inference rights:

```bash
ACCID=$(az cognitiveservices account show -n $ACCT -g $RG --query id -o tsv)

# create a project under the account
az rest --method put \
  --url "https://management.azure.com${ACCID}/projects/certmesh?api-version=2025-06-01" \
  --body '{"location":"swedencentral","identity":{"type":"SystemAssigned"},"properties":{"displayName":"certmesh"}}'

# grant YOUR user inference rights on the resource
OID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --assignee-object-id $OID --assignee-principal-type User \
  --role "Cognitive Services OpenAI User" --scope "$ACCID"
```

The project endpoint is then
`https://<account>.services.ai.azure.com/api/projects/<project>`
(here: `https://cmfoundrydp01.services.ai.azure.com/api/projects/certmesh`).

## 4. Foundry IQ over Azure AI Search (provisioned)

Create a **Free (F) tier** search service (one free service per subscription),
then index the corpus with the repo's indexer (`scripts/index_foundry_iq.py`),
which reuses the *same* chunker as the local index so the citation contract — and
grounding — is identical to the local fallback.

```bash
RG=certmesh-rg; SVC=certmesh-search-dp01; LOC=swedencentral

# 4.1 free-tier search service
az search service create -n $SVC -g $RG --sku free -l $LOC

# 4.2 endpoint + admin key → into .env (see §5)
EP="https://${SVC}.search.windows.net"
KEY=$(az search admin-key show --service-name $SVC -g $RG --query primaryKey -o tsv)

# 4.3 create the index + upload the chunked data/knowledge/ docs
PYTHONPATH=src ./.venv/bin/python scripts/index_foundry_iq.py
# → "uploaded 110/110 chunks to 'certmesh-knowledge'"
```

The index schema (id, title, content, locator, source, url, kind) is created by
the script. The `content` field stores each chunk **verbatim**, so the critic's
substring grounding check passes against Azure-Search results exactly as it does
locally.

## 5. Wire up `.env`

```ini
AZURE_AI_PROJECT_ENDPOINT=https://cmfoundrydp01.services.ai.azure.com/api/projects/certmesh
AZURE_AI_MODEL_DEPLOYMENT=gpt-4o
CERTMESH_MODEL_BACKEND=auto
AZURE_SEARCH_ENDPOINT=https://certmesh-search-dp01.search.windows.net
AZURE_SEARCH_API_KEY=<search admin key — secret, keep out of git>
AZURE_SEARCH_INDEX=certmesh-knowledge
CERTMESH_MCP_ENABLED=true
```

`.env` is gitignored — never commit it. The model uses `DefaultAzureCredential`
(your `az login` token, no key); Azure AI Search uses its admin key here for
simplicity (you could instead grant `Search Index Data Reader` and use Entra).

## 6. Run & verify the live path

Run the server with the **venv** Python (the global interpreter lacks the Agent
Framework and would silently fall back to offline):

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn app.api:app --port 8000
curl -s http://localhost:8000/healthz
# → "model_backend":"foundry", "foundry_configured":true
```

Direct end-to-end model check (proves gpt-4o is reachable through CertMesh):

```bash
./.venv/bin/python - <<'PY'
import os
os.environ.update({
  "AZURE_AI_PROJECT_ENDPOINT":"https://cmfoundrydp01.services.ai.azure.com/api/projects/certmesh",
  "AZURE_AI_MODEL_DEPLOYMENT":"gpt-4o", "CERTMESH_MODEL_BACKEND":"foundry"})
from certmesh.config import load_config; load_config.cache_clear()
from certmesh.foundry.client import get_model_backend
print(get_model_backend(load_config()).generate("terse assistant", "say hi"))
PY
```

### What actually goes live (honesty note)

| Capability | State after this setup |
|---|---|
| **Microsoft Learn MCP** | **Live** — real HTTP calls to `learn.microsoft.com/api/mcp`; citations resolve to live Learn URLs (the Curator step jumps from ~1 ms to ~1.3 s). |
| **Foundry model (`gpt-4o`)** | **Live and invoked.** The Curator now calls `model.generate()` to add a natural-language coaching narrative (in the learner's language) over its *already-grounded* summary — visible in the dashboard, labelled "AI coach". The narrative is never grounding-checked (it is not a citation/quoted claim); on any model error it falls back to None, so offline behaviour is unchanged. Proven end-to-end (en + ca). |
| **Foundry IQ** | **Live** — Azure AI Search (`retrieval_backend: azure_search`), 110 chunks, verbatim content so grounding stays 1.0. |

A full live learner request runs ~5–8 s (Azure Search + live Learn MCP +
`gpt-4o` generation), vs ~8 ms fully offline.

## 7. Code changes made for the live path (review before committing)

The live integration required small, additive changes (all degrade gracefully to
the offline behaviour — verified by the offline test suite, 39/39):

| File | Change |
|---|---|
| `src/certmesh/schemas.py` | `CuratedPath` gains optional `narrative` / `narrative_source` (model gloss, not grounding-checked). |
| `src/certmesh/agents/base.py` | `AgentContext` gains an optional `model` backend (for prose only). |
| `src/certmesh/orchestrator.py` | passes `model=self.model` into the agent context. |
| `src/certmesh/agents/curator.py` | `_add_narrative()` — optional `gpt-4o` gloss with try/except fallback. |
| `src/certmesh/iq/foundry_iq.py` | `_search_azure` reads a `locator` field (citation fidelity). |
| `app/ui/index.html` | renders the AI-coach narrative, clearly labelled. |
| `scripts/index_foundry_iq.py` | **new** — creates the Search index + uploads chunks. |
| `tests/conftest.py`, `evals/run_evals.py` | force offline/deterministic backends so `make test` / `make eval` stay hermetic **even with a live `.env`** (explicit shell overrides still win). |

> ⚠️ **Determinism:** `make test` and `make eval` are pinned to the offline
> backends + Learn offline cache. This is deliberate — the live Microsoft Learn
> MCP returns best-effort results even for fictional internal cert codes, which
> would otherwise break the "internal certs have no Learn content" invariant and
> dip first-draft grounding below 1.0 (the critic's reflection loop recovers it
> at runtime, but the CI gate must be reproducible).

---

## Cost summary

| Resource | Tier chosen | Cost |
|---|---|---|
| Azure account | Free trial | $0 (CC for verification only) |
| AI Foundry / AI Services resource | base | $0 (pay per token) |
| `gpt-4o` usage | pay-as-you-go | cents for test traffic |
| Azure AI Search | Free (F) | $0 |

## Reverting to offline

Empty or delete `.env` (or set `CERTMESH_MODEL_BACKEND=offline`) and restart.
`/healthz` returns to `model_backend: offline_stub`, `retrieval_backend: local`.
