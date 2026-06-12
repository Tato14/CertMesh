# Deploying CertMesh as a Foundry Agent Service Hosted Agent

CertMesh runs fully locally with no cloud. This runbook lights up the real
Microsoft Foundry path: a model deployment, Foundry IQ over Azure AI Search, and
the orchestrator packaged as a **Hosted Agent** (container image â†’ Azure Container
Registry â†’ Foundry Agent Service, with a Microsoft Entra agent identity and a
managed endpoint). Secrets never enter the image â€” managed identity is used at
runtime.

> APIs verified June 2026. The product was renamed to **Microsoft Foundry**
> (formerly Azure AI Foundry); `azure-ai-projects >= 2.0.0` is the current
> "Foundry projects (new)" API. Adjust to the exact API version in your tenant.

## 0. Prerequisites
- A Microsoft Foundry project (Overview â–¸ Endpoints gives the project endpoint).
- A deployed model in the project catalog (e.g. `gpt-4o`).
- `az login`, Docker, and an Azure Container Registry (ACR).
- (For real Foundry IQ) an Azure AI Search resource.

## 1. Build & push the image
```bash
az acr login --name <ACR_NAME>
docker build -t <ACR_NAME>.azurecr.io/certmesh:latest -f deploy/Dockerfile .
docker push <ACR_NAME>.azurecr.io/certmesh:latest
```

## 2. Configuration (no secrets in the image)
Set these as Hosted Agent environment variables (values supplied by the platform /
managed identity, not committed):

| Variable | Purpose |
|---|---|
| `AZURE_AI_PROJECT_ENDPOINT` | Foundry project endpoint (`https://<resource>.services.ai.azure.com/api/projects/<project>`) |
| `AZURE_AI_MODEL_DEPLOYMENT` | model deployment name (default `gpt-4o`) |
| `AZURE_SEARCH_ENDPOINT` / `AZURE_SEARCH_INDEX` | Foundry IQ knowledge base (Azure AI Search) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Foundry tracing / Azure Monitor |
| `CERTMESH_MCP_ENABLED` | `true` to use the live Microsoft Learn MCP server |

Authentication uses **`DefaultAzureCredential`** (the Hosted Agent's Entra agent
identity / managed identity) â€” no API keys in the image. Grant that identity
`Cognitive Services User` on the Foundry project and `Search Index Data Reader` on
the search service.

## 3. Foundry IQ knowledge base (real grounding)
1. Create an Azure AI Search index over `data/knowledge/` (or point a Foundry
   knowledge source at the blob container holding those docs).
2. In Foundry, create a **knowledge base** over that knowledge source.
3. Expose it to the agent as the `knowledge_base_retrieve` MCP tool via a
   `RemoteTool` project connection (`authType: ProjectManagedIdentity`) targeting
   `{search_endpoint}/knowledgebases/{kb}/mcp?api-version=2026-05-01-preview`.

CertMesh's `iq/foundry_iq.py` already speaks the same retrieve-and-cite contract,
so once `AZURE_SEARCH_ENDPOINT` is set it uses the managed index; the agents are
unchanged. Ref:
<https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/foundry-iq-connect>.

## 4. Provision the Hosted Agent
Register the orchestrator as a hosted agent pointing at the pushed image, e.g.
(Python, `azure-ai-projects >= 2.0.0`):

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
agent = project.agents.create_version(
    agent_name="certmesh-orchestrator",
    definition=PromptAgentDefinition(
        model="gpt-4o",
        instructions="CertMesh planner-executor orchestrator (containerised endpoint).",
        # attach the Foundry IQ knowledge_base_retrieve MCP tool here
    ),
)
```

Foundry Agent Service provisions compute, assigns the Entra agent identity, and
exposes the endpoint. The FastAPI `/healthz` route backs the container health
probe.

## 5. Verify
- `GET /healthz` â†’ `model_backend: foundry`, `retrieval_backend: azure_search`.
- `make eval` from CI still enforces all six hard gates (grounding == 1.0, PII == 0, redteam == 1.0, routing, capacity, abstention).
- Traces appear in Foundry tracing / Azure Monitor (Application Insights).

## Graceful degradation
If any of the above is absent, CertMesh automatically falls back to the
deterministic model stub, the local BM25 Foundry IQ index, and the Microsoft Learn
offline cache â€” so the app never hard-blocks on cloud provisioning.
