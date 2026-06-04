# Microsoft IQ layers

The contest requires at least one Microsoft IQ layer. CertMesh implements
**Foundry IQ for real** (knowledge base + agentic retrieve-and-cite) as the
required layer, and **Work IQ** and **Fabric IQ** as concept-faithful layers
over synthetic signals, each with a documented upgrade path to the managed
product. We are explicit about what is real vs. simulated.

## Foundry IQ — *required, real layer* (`src/certmesh/iq/foundry_iq.py`)

**What it is.** A knowledge base over the approved synthetic corpus
(`data/knowledge/`) that the Curator and Assessment agents call as
retrieve-and-cite. Every returned chunk carries verbatim source text, so the
critic can verify that any cited snippet is an actual substring of a retrieved
source — that is what makes the citation-grounding rate a hard CI gate.

**Two backends, one contract.**

| Backend | When | Notes |
|---|---|---|
| **Azure AI Search** (`backend == "azure_search"`) | `AZURE_SEARCH_ENDPOINT` set | Mirrors how Foundry IQ indexes a knowledge source. Queries the index and maps results to the same citable chunk shape. |
| **Local BM25 index** (`backend == "local"`) | default | Dependency-free index over `data/knowledge/`, identical retrieve-and-cite contract, so the system is fully demoable and CI-gated with zero cloud. |

**Upgrade path to managed Foundry IQ.** In a full Foundry deployment the
knowledge base is created over a knowledge source (Azure Blob / OneLake /
SharePoint) and consumed by an agent through the **`knowledge_base_retrieve`**
MCP tool exposed at
`{search_endpoint}/knowledgebases/{kb}/mcp?api-version=2026-05-01-preview`, wired
via a `RemoteTool` project connection (`ProjectManagedIdentity`). Citations are
returned as source references. CertMesh keeps the same retrieve-and-cite contract
locally, so the agents are unchanged when you switch the backend on. See
[../deploy/deploy_hosted_agent.md](../deploy/deploy_hosted_agent.md) and
<https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/foundry-iq-connect>.

## Work IQ — concept-faithful (`src/certmesh/iq/work_iq.py`)

**What it is.** A context layer providing the *same shape* of signal as
Microsoft's Work IQ — aggregate weekly meeting hours, focus hours and a preferred
learning slot per employee (`data/work_signals.json`). The Engagement and Manager
Insights agents consume it.

**Real vs. simulated.** The *signal shape and the way agents consume it* are
faithful; the *values* are synthetic. There is **no** real Microsoft 365 / Graph
connection — and we deliberately expose only aggregate, content-free figures (no
calendar or message content), which is also the privacy posture you'd want with
the real product.

**Upgrade path.** Replace the JSON loader with a Microsoft Graph / Work IQ
connector that returns the same `WorkSignal` shape (meeting load, focus time,
working pattern). Agent code is unchanged.

## Fabric IQ — concept-faithful (`src/certmesh/iq/fabric_iq.py`)

**What it is.** A semantic layer (ontology) over the synthetic certification seed
(`data/fabric_seed.json`):

- **entities** — certification, skill, role, track
- **relationships** — `prerequisite_of`, `required_for_role`, `covers_skill`
- **measures** — `recommended_hours`, `pass_threshold`, skill-difficulty, skill-gap

The Study Plan, Assessment and Manager Insights agents query it for the *meaning*
of a request (skills, prerequisites, thresholds, role alignment) instead of
hard-coding it.

**Real vs. simulated.** The semantic-model concept (governed entities +
relationships + measures queried by agents) is faithful; the model is backed by a
local JSON seed rather than a Fabric semantic model over OneLake.

**Upgrade path.** Back the same interface with a Microsoft Fabric semantic model
/ OneLake source; the `FabricIQ` query methods become semantic-model queries.

## Microsoft Learn MCP (`src/certmesh/tools/ms_learn_mcp.py`)

Not an IQ layer, but the real external grounding source for the Curator: the
public Microsoft Learn MCP server (`https://learn.microsoft.com/api/mcp`, tool
`microsoft_docs_search`, no auth). When the network/`mcp` client is unavailable
the tool falls back to a small offline cache of **real, stable** Microsoft Learn
URLs so a demo always shows a real Learn citation. Internal certs correctly
return no Learn content.

## Honesty statement

- **Real when configured:** Foundry IQ over Azure AI Search; the Foundry model; OTel→Foundry tracing; managed `azure-ai-evaluation`; the live Microsoft Learn MCP.
- **Concept-faithful (synthetic-backed):** Work IQ and Fabric IQ — faithful interfaces and agent integration, synthetic values, no live M365/Fabric tenant.
- We do **not** claim a live Microsoft 365 or Microsoft Fabric tenant integration; the upgrade paths above are how you would connect them.
