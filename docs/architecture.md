# CertMesh — Architecture

CertMesh is a multi-agent enterprise learning / certification-management system
built on the **Microsoft Agent Framework** and **Microsoft Foundry**. A
planner–executor orchestrator routes a learner or manager request to five
specialist agents and a cross-cutting critic/verifier, all grounded by three
Microsoft IQ layers (Foundry IQ as the required real layer; Work IQ and Fabric
IQ as concept-faithful layers) plus the Microsoft Learn MCP server.

> All data, identifiers and documents are **synthetic** (a fictional healthcare
> provider, "Northwind Health"). See [responsible-ai.md](responsible-ai.md).

## System diagram

```mermaid
flowchart TD
    U[Learner / Manager dashboard] --> API[FastAPI gateway]
    API --> ORCH[Orchestrator agent\nPlanner-Executor\nMicrosoft Agent Framework]
    subgraph Foundry[Microsoft Foundry]
      MODEL[Model deployment\nAZURE_AI_MODEL_DEPLOYMENT]
      HOSTED[Foundry Agent Service\nHosted Agents]
      FEVAL[Foundry evaluations\n+ tracing / observability]
      FIQ[Foundry IQ knowledge base\nagentic retrieval / Azure AI Search]
    end
    ORCH --> A1[Learning Path Curator]
    ORCH --> A2[Study Plan Generator]
    ORCH --> A3[Engagement Agent]
    ORCH --> A4[Assessment Agent]
    ORCH --> A5[Manager Insights Agent]
    ORCH --> CRIT[Critic / Verifier\ngrounding + reflection]
    A1 --> FIQ
    A1 --> MCP[Microsoft Learn MCP server\nmicrosoft_docs_search]
    A4 --> FIQ
    A2 --> FAB[Fabric IQ semantic layer\nontology over synthetic data]
    A4 --> FAB
    A5 --> FAB
    A3 --> WORK[Work IQ context layer\nsynthetic work signals]
    A5 --> WORK
    ORCH --> MODEL
    ORCH -.deploy as hosted agent.-> HOSTED
    ORCH --> FEVAL
    ORCH --> TRACE[orchestration_trace]
```

## How CertMesh uses Microsoft Foundry

| Foundry capability | How CertMesh uses it | Real vs. concept-faithful |
|---|---|---|
| **Model deployment** | Agents call a Foundry-deployed model through the Agent Framework's `FoundryChatClient` for optional natural-language glosses. Model name in `AZURE_AI_MODEL_DEPLOYMENT` (default `gpt-4o`). | Real when configured; deterministic offline stub otherwise. |
| **Foundry IQ** | A knowledge base over the approved synthetic corpus, exposed to the Curator + Assessment agents as retrieve-and-cite. Azure AI Search when configured; local BM25 index with the identical citation contract otherwise. The managed path consumes the KB via the `knowledge_base_retrieve` MCP tool. | **Real layer** (Azure AI Search) with a faithful local fallback. See [iq-layers.md](iq-layers.md). |
| **Work IQ / Fabric IQ** | Concept-faithful context + semantic layers over synthetic signals, with a documented upgrade path to the managed products. | Concept-faithful. |
| **Hosted Agents** | The orchestrator is packaged as a container image → ACR → Foundry Agent Service (Entra agent identity, managed endpoint). | Documented + Dockerfile; runs locally without it. See [../deploy/deploy_hosted_agent.md](../deploy/deploy_hosted_agent.md). |
| **Evaluations + tracing** | Every agent call runs inside an OpenTelemetry span (bridged to Foundry tracing / Azure Monitor when configured). The eval harness integrates the managed `azure-ai-evaluation` `GroundednessEvaluator`/`RelevanceEvaluator` when available, with always-on local evaluators as the CI gate. | Real when configured; local evaluators otherwise. |
| **Microsoft Learn MCP** | The Curator calls the public Learn MCP server (`microsoft_docs_search`) for real, cited Microsoft Learn content. | Real (public, no auth); offline cache of real Learn URLs as fallback. |

## Request lifecycle

1. **FastAPI gateway** (`app/api.py`) receives a `LearningRequest` and calls the orchestrator.
2. **Orchestrator** (`src/certmesh/orchestrator.py`) detects language, resolves the certification/role/learner/capacity from the IQ layers, and **plans** which specialists to run (the routing decision is the first trace step).
3. **Specialists** run in sequence; **grounded** agents (Curator, Assessment) pass through the **critic** before their output is accepted — an ungrounded claim triggers a bounded **reflection loop** or an abstain.
4. The orchestrator assembles an `OrchestrationResult` with a full `OrchestrationTrace` (every agent, its sources, critic verdicts, reflections, and timings). The dashboard replays that trace as an animated agent flow using the real per-step timings.

## HTTP surface

| Endpoint | Purpose |
|---|---|
| `POST /api/run` | Run the orchestrator (learner or manager view); returns the full `OrchestrationResult` + trace. |
| `GET /api/presets` | Demo scenario cards + the AI-use disclosure string. |
| `GET /api/graph` | The Fabric IQ ontology serialised as Cytoscape elements (`role`/`certification`/`skill` nodes with track + level metadata; `requires`/`covers`/`prerequisite` edges) plus per-role certification paths in prerequisite order and the synthetic learner roster for the overlay. The seed covers 31 certifications (major Microsoft exams + fictional internal ones) and 21 roles; the matching grounded corpus lives in `data/knowledge/certification-catalog-extension.md`. |
| `GET /api/calendar/{id}` | A **simulated** Mon–Fri week for a learner/employee id: synthetic busy blocks consistent with the Work IQ signal (`src/certmesh/calendar_sim.py`) + the Engagement Agent's proposed study slots as first-class events. Never a real tenant. |
| `GET /api/progress/{learner_id}` | Synthetic weekly progress snapshots (`data/progress_history.json`) + trend feedback against the Fabric IQ threshold. |
| `GET /api/progress/team/{team_id}` | **Aggregate-only** team progress, held to the manager-view privacy contract: k-anonymity suppression (n < 3) and a belt-and-braces identifier scan (covered by tests). |
| `GET /healthz` | Backend status for the dashboard's status pills. |

The presentation endpoints (`graph`/`calendar`/`progress`) are additive read-only
layers over the IQ layers and synthetic datasets — agent contracts, trace
semantics and eval behaviour are untouched.

See [orchestration.md](orchestration.md) for the planner–executor + critic detail and the trace format, [agents.md](agents.md) for each agent's contract, and [iq-layers.md](iq-layers.md) for the IQ layers.

## Code map

```
src/certmesh/
  orchestrator.py     planner–executor + reflection loop + trace assembly
  schemas.py          Pydantic contracts for every I/O + the trace
  config.py           env-driven, cloud-optional configuration
  calendar_sim.py     deterministic synthetic week (Work IQ extension)
  agents/             curator, study_plan, engagement, assessment, manager_insights, critic
  iq/                 foundry_iq (real), work_iq, fabric_iq (concept-faithful)
  tools/ms_learn_mcp  Microsoft Learn MCP client
  foundry/            model backend (Agent Framework) + OTel tracing
app/
  api.py              FastAPI gateway (run/graph/calendar/progress/presets/healthz)
  ui/                 zero-build dashboard: index.html + css/ (design system)
                      + js/ native ES modules (app, trace, learner, graph,
                      calendar, quiz, progress, manager) — no bundler, no node
evals/                gold cases + local evaluators + Foundry eval SDK path
deploy/               Dockerfile + hosted-agent runbook
```

The dashboard is intentionally **zero-build**: static files served by the same
FastAPI app (`make run`), Cytoscape + dagre from pinned CDNs for the graph view
(with a designed offline fallback), and hand-rolled SVG for charts and the trace
flow — judges need nothing but Python.
