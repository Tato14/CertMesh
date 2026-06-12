# Submission checklist — Microsoft Agents League, Battle #2

Mapped to the contest requirements and the rubric.

## Requirements
- [x] **Multi-agent system aligned to the scenario** — orchestrator + 5 specialists + critic; enterprise certification management. (`src/certmesh/`)
- [x] **Uses Microsoft Foundry and/or the Microsoft Agent Framework** — Agent Framework model backend (`foundry/client.py`), Foundry model deployment, Foundry IQ, Hosted Agent deployment path, Foundry tracing + evaluation SDK.
- [x] **Reasoning + multi-step decision-making across agents** — planner–executor routing, decomposition, critic self-reflection loop, abstention. (`docs/orchestration.md`)
- [x] **External tools / APIs / MCP where they add value** — Microsoft Learn MCP (`microsoft_docs_search`) for real, cited Learn content.
- [x] **≥1 Microsoft IQ layer** — Foundry IQ real (KB + agentic retrieve-and-cite); Work IQ + Fabric IQ concept-faithful. (`docs/iq-layers.md`)
- [x] **Synthetic data + documents only; README states this** — fictional Northwind Health; fabricated ids; README + LICENSE notices.
- [x] **Demo-able; explains agent interactions** — one-click presets + live orchestration trace panel. (`docs/demo-script.md`)
- [x] **Docs for responsibilities, flow, tools, data** — `docs/agents.md`, `orchestration.md`, `iq-layers.md`, `architecture.md`.
- [x] **Public GitHub repo** — <https://github.com/Tato14/CertMesh> (secret scan clean; `.env` untracked).
- [x] **Architecture diagram** — `docs/architecture.md` (Mermaid), a required artifact.
- [x] **Project description** — `README.md`.
- [ ] **≤5-min original demo video uploaded to YouTube/Vimeo** — RECORDED: `docs/video/certmesh-demo.webm` (2:58, captioned narration, real timings; gitignored). Upload it to YouTube and paste the link into the README — or re-record with voiceover by reading the on-screen captions.

## Highly-valued extras
- [x] **Evals** — 67 labelled gold cases + scorecard + **6 hard CI gates**, runnable **live in-product** from the Quality tab (`evals/`, `POST /api/evals/run`).
- [x] **Red-team category** — 10 adversarial cases (en/ca/es injection, PII exfiltration) + benign look-alikes, gated at `redteam_block == 1.0`, with two one-click attack presets.
- [x] **Critic ablation** — `make eval-ablation` proves the grounding gate is load-bearing (critic off → 91.3%; 100/100 fabricated citations caught).
- [x] **Telemetry** — per-agent OpenTelemetry spans, Foundry tracing bridge (`foundry/tracing.py`).
- [x] **Advanced reasoning patterns** — planner–executor with a **deliberation ledger**, critic/verifier, bounded self-reflection, abstention, **adaptive re-plan from exam mistakes**, **what-if counterfactual re-planning**.
- [x] **RAI fallbacks** — grounding guard, PII + k-anonymity guard, policy refusal, abstain/clarify under uncertainty (`docs/responsible-ai.md`).
- [x] **Hosted deployment story** — `deploy/Dockerfile` + `deploy/deploy_hosted_agent.md` (ACR → Foundry Agent Service).

## Definition of done (self-check)
- [x] `pytest` green (57 tests).
- [x] `evals/run_evals.py` prints the scorecard; **citation grounding = 1.0**, **manager PII-leak = 0**, **adversarial block = 1.0**; CI enforces all six gates.
- [x] `make run` serves the dashboard; all presets (incl. over-capacity, out-of-corpus, Catalan/Spanish) produce correct, cited, traced results.
- [x] Foundry IQ works against Azure AI Search when configured and via the local fallback otherwise; Microsoft Learn MCP returns real cited content.
- [x] `docs/` complete (architecture, agents, orchestration, iq-layers, demo-script, submission-checklist, responsible-ai).
- [x] `deploy/Dockerfile` + `deploy_hosted_agent.md`; secrets stay out of the image.
- [x] README opens with problem, rubric mapping, 30-sec quickstart, IQ statement, synthetic-data + RAI statement, eval scorecard.

## Before pushing
1. Confirm `.env` is gitignored and only `.env.example` is tracked.
2. Run a secret scan (README has the command).
3. Record the demo video and paste the link into the README.
4. (If a team) collect Microsoft Learn usernames.
5. Submit via the Projects tab before **14 June 2026, 23:59 PT**.
