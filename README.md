# CertMesh

**A multi-agent enterprise learning & certification-management system on the
Microsoft Agent Framework + Microsoft Foundry.**

> Microsoft Agents League @ AI Skills Fest — Battle #2: Reasoning Agents with
> Microsoft Foundry.
>
> 🧪 **All data, identifiers and documents in this repository are SYNTHETIC and
> for demonstration only** — a fictional healthcare provider, *Northwind Health*,
> with fabricated ids (`L-1001`, `EMP-001`, `TEAM-A`). No real people, PII, or
> tenant data. See [Responsible AI](docs/responsible-ai.md).

---

## The problem

Enterprises run internal certification programmes (cloud, data, clinical safety,
compliance) but managing them is hard: requirements map to roles in non-obvious
ways, study plans ignore how busy people actually are, practice questions drift
from approved material, and managers want team-level readiness **without** seeing
individuals' data. CertMesh is a team of cooperating agents that:

- maps a certification target to role-relevant skills and **cited** resources,
- builds a **capacity-aware** study plan around the learner's real work rhythm,
- generates **grounded, cited** practice questions and scores readiness,
- keeps learners on track with rhythm-aware reminders, and
- gives managers **aggregate, PII-free** readiness and risk insight.

A learner states a goal → the **orchestrator** plans and fans out to five
specialists → a **critic** verifies every claim is grounded → results come back
cited, with a fully inspectable reasoning trace.

## How it scores against the rubric

| Weight | Criterion | Where it lives |
|---|---|---|
| 25% | **Accuracy & Relevance** | Citation grounding enforced at 1.0; capacity-respecting plans; thresholded readiness. ([evals](evals/), [iq-layers](docs/iq-layers.md)) |
| 25% | **Reasoning & multi-step** | Planner–executor + 5 specialists + critic self-reflection loop — replayed live in the dashboard as an **animated agent flow** with visible loop-back edges on every critic-forced revision. ([orchestration](docs/orchestration.md)) |
| 15% | **Creativity & originality** | Healthcare-org scenario, interactive Fabric IQ knowledge graph, simulated capacity calendar with .ics export, critic grounding loop, real Microsoft Learn MCP content. |
| 15% | **UX & presentation** | A six-view dashboard (Learner · Graph · Calendar · Assessment · Manager · persistent Trace panel): dark design system, scenario cards, role-path graph highlighting, exam mode with live scoring, teams×tracks heatmap with designed k-anonymity suppression, skeleton/empty/abstain states, `prefers-reduced-motion` support — zero-build, served by `make run`. ([app](app/)) |
| 20% | **Reliability & safety** | Grounding guard, PII + k-anonymity guard, abstain/clarify, CI eval gates. ([responsible-ai](docs/responsible-ai.md)) |

## 30-second quickstart

```bash
# 1) install (Python 3.10+). Runs fully offline — no cloud needed.
python -m pip install -e ".[dev,i18n]"

# 2) serve the dashboard at http://localhost:8000
make run            # or:  PYTHONPATH=src uvicorn app.api:app --reload --port 8000

# 3) tests + the evaluation scorecard (the CI gate)
make test           # 51 tests (incl. graph/calendar/progress API + PII suppression)
make eval           # prints the scorecard below
```

PowerShell (Windows): `make` may be absent — use the explicit commands, e.g.
`$env:PYTHONPATH="src"; uvicorn app.api:app --reload --port 8000` and
`$env:PYTHONPATH="src"; python -m evals.run_evals`.

Open the dashboard and click a scenario card: **AZ-204 learner**, **Over-capacity
clinician (L-1012)**, **Manager view**, **Out-of-corpus (AWS)**, **Catalan input**,
**Role path: DevOps Engineer** (knowledge graph) or **Calendar contrast: L-1012 vs
L-1005** (capacity calendar). Each card says what to watch for.

## The dashboard

Six views, zero build step — static HTML/CSS/ES-modules served by the same
FastAPI app, in a light, training-oriented design system (Microsoft-inspired
palette). Demo scenario cards sit in a collapsible strip available on every tab.

- **Graph (the main view)** — the full learning ecosystem as an interactive
  Cytoscape graph over the Fabric IQ ontology: **31 certifications** (the major
  Microsoft AZ/AI/DP/SC/PL/MS/MD exams plus fictional internal ones) and **21
  roles**. Explore by track (technical/clinical/compliance/security), toggle the
  ~130 skills, pick a role to light up its certification path in prerequisite
  order, overlay a learner's completed/in-progress/at-risk states, and click any
  cert to launch a real agent run. Internal (fictional) certs render dashed.
- **Learner** — request form; results stream in agent order with grounded
  citation chips, a compact capacity week and a progress chart.
- **Calendar** — a *simulated* Outlook-style week per learner: meetings (muted),
  focus time (green), the Engagement Agent's proposed study slots (accented, with
  why-this-slot tooltips) and a `[SYNTHETIC DEMO]` .ics export.
- **Assessment** — exam mode: one question at a time, live score gauge against the
  Fabric IQ pass threshold, per-question citations; failing routes you back into
  the preparation loop.
- **Manager** — teams × tracks readiness heatmap with k-anonymity-suppressed cells
  rendered honestly (🔒 n < 3), severity risk cards, aggregate team trend.
- **Orchestration trace** (collapsible side panel; unfolds automatically when
  agents run) — the multi-agent run as an animated flow; critic-forced revisions
  draw a visible loop-back arc, and every node opens a detail view with inputs,
  outputs, verdicts and timings.

<!-- screenshots: docs/img/learner.png · docs/img/graph.png · docs/img/calendar.png
     docs/img/assessment.png · docs/img/manager.png · docs/img/trace.png -->
*(screenshot placeholders — capture each tab at 1440×900 before submission)*

## The multi-agent system

```
Orchestrator (planner–executor)
 ├─ Learning Path Curator   → Foundry IQ + Microsoft Learn MCP   (cited resources)
 ├─ Study Plan Generator    → Fabric IQ + Work IQ                (capacity-aware schedule)
 ├─ Engagement Agent        → Work IQ                            (rhythm-aware reminders)
 ├─ Assessment Agent        → Foundry IQ + Fabric IQ             (cited questions + readiness)
 └─ Manager Insights Agent  → Work IQ + Fabric IQ (aggregate)    (PII-safe team view)
Critic / Verifier (cross-cutting) → grounding + PII guard, drives reflection / abstain
```

See [docs/architecture.md](docs/architecture.md) for the diagram and
[docs/agents.md](docs/agents.md) for each agent's contract.

## Microsoft IQ statement

CertMesh implements **Foundry IQ for real** (the required layer) and **Work IQ**
and **Fabric IQ** as concept-faithful layers — and is explicit about which is
which:

- **Foundry IQ (real):** a knowledge base with agentic **retrieve-and-cite** over
  the approved corpus. Uses **Azure AI Search** when configured (consumed in a
  full Foundry deployment via the `knowledge_base_retrieve` MCP tool); falls back
  to a local BM25 index with the **identical** citation contract otherwise.
- **Work IQ / Fabric IQ (concept-faithful):** faithful signal shapes and agent
  integration over synthetic data, with a documented upgrade path to Microsoft
  Graph / a Fabric semantic model. No live M365/Fabric tenant is claimed.
- **Microsoft Learn MCP (real):** the Curator calls the public Learn MCP server
  (`microsoft_docs_search`) for real, cited Microsoft Learn content.

Details and upgrade paths: [docs/iq-layers.md](docs/iq-layers.md).

## Evaluation scorecard

55 labelled synthetic gold cases (`evals/gold_cases.jsonl`) across routing,
grounding, capacity-fit, PII, readiness, abstention and ca/es language. The two
hard gates fail CI if violated.

| Metric | Result | Gate |
|---|---|---|
| Agent-routing accuracy | **100%** | ≥ 90% |
| **Citation grounding rate** | **100%** | **== 1.0 (hard)** |
| Assessment grounding pass | **100%** | — |
| **Manager PII-leak total** | **0** | **== 0 (hard)** |
| Capacity-fit pass rate | **100%** | == 1.0 |
| Assessment scoring accuracy | **100%** | — |
| Abstention correctness | **100%** | == 1.0 |
| Language accuracy (en/ca/es) | **100%** | — |

Run `make eval` to reproduce. The managed Foundry `GroundednessEvaluator` /
`RelevanceEvaluator` integration is in `evals/foundry_eval.py` (used when
`azure-ai-evaluation` + a judge model are configured; the local harness is the
always-on gate).

## Cloud-optional configuration

Everything above runs offline. Copy `.env.example` → `.env` to light up the real
Microsoft Foundry paths (model deployment, Foundry IQ over Azure AI Search, OTel →
Foundry tracing, managed evaluators). Managed identity (`DefaultAzureCredential`)
is preferred over keys. Deploy as a Foundry **Hosted Agent**:
[deploy/deploy_hosted_agent.md](deploy/deploy_hosted_agent.md).

## Synthetic data & Responsible AI

- **Synthetic only.** No real PII anywhere; real Microsoft exam codes (AZ-204,
  AZ-400, DP-203, AZ-900) are referenced for realism alongside fictional internal
  certs (`CLIN-SAFE-1/2`, `GDPR-HC-2`, `TELEHEALTH-1`, `HL7-FHIR-1`).
- **Grounding guard:** no fabricated facts or questions; abstain under uncertainty.
- **Privacy:** manager insights are aggregate + k-anonymity-suppressed; the critic
  scans for identifiers; CI fails on any leak.
- **Transparency + oversight:** the UI discloses AI use; the system recommends, a
  human decides. Full policy: [docs/responsible-ai.md](docs/responsible-ai.md).

## Before pushing (secrets)
```bash
git ls-files | grep -E '^\.env$' && echo "ERROR: .env tracked" || echo "ok: .env not tracked"
git grep -nE '(API_KEY|SECRET|PASSWORD)\s*=\s*["'"'"']?[A-Za-z0-9/+]{12,}' -- '*.py' '*.toml' '*.md' || echo "ok: no obvious secrets"
```

## Repository layout
See [docs/architecture.md](docs/architecture.md#code-map). Key dirs: `src/certmesh`
(agents, IQ layers, orchestrator), `app` (dashboard), `evals`, `deploy`, `docs`,
`data` (synthetic), `tests`.

## Demo video
▶️ *Add your ≤5-min YouTube/Vimeo link here.* Script: [docs/demo-script.md](docs/demo-script.md).

## License
MIT — see [LICENSE](LICENSE).
