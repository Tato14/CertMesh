# 5-minute demo script

A tight, rubric-mapped walkthrough. Start the app (`make run`) and open
<http://localhost:8000>. Each preset button reproduces a scenario instantly.

> On-screen one-liner to keep visible: *"All data synthetic — fictional Northwind
> Health workforce certification programme."*

---

### 0:00–0:45 — Hook: a cited plan in one click  *(UX 15% · Relevance 25%)*
- **Do:** Click preset **"AZ-204 learner (English)"**.
- **Show:** the four cards appear — a cited learning path, a capacity-aware
  schedule, a reminder window, and a readiness assessment with citations.
- **Say:** *"A learner asks to prepare for AZ-204. The orchestrator fans out to
  five specialist agents and comes back with a plan where every claim is cited —
  from an approved knowledge base and from Microsoft Learn."*
- **Point at:** the citation chips and the "Sources" card.

### 0:45–2:15 — Open the orchestration trace  *(Reasoning 25%)*
- **Do:** Look at the right-hand **Orchestration trace** panel.
- **Say:** *"This is the multi-agent reasoning. The planner decided the route,
  then each specialist ran. The Curator and Assessment outputs pass through a
  critic that checks grounding."*
- **Point at:** steps **[4] Assessment — draft — revised** then **[5] Assessment
  — revise — ok**, and read the highlighted reflection box:
  *"the critic rejected an ungrounded synthesis question, so the agent revised it
  to cite verbatim source text."* This is the self-reflection loop.

### 2:15–3:15 — Capacity-aware planning  *(Relevance + Work IQ)*
- **Do:** Click **"Over-capacity clinician (L-1012)"**, note **14 weeks** and the
  capacity note. Then click **"Strong learner (L-1005)"**, note the **shorter**
  schedule.
- **Say:** *"Same certification family, two learners. L-1012 has only 3 focus
  hours a week against a heavy meeting load, so the plan stretches over more weeks
  instead of overloading them — driven by the Work IQ signal. The Engagement
  agent also schedules fewer, spread-out sessions in their preferred slot."*

### 3:15–4:00 — Manager view, PII-free  *(Safety 20%)*
- **Do:** Click **"Manager view (all teams)"**.
- **Show:** the readiness heatmap by team/track, the **PII-safe** badge, the risk
  flags (DP-203 exam risk, clinical capacity), and "Suppressed for privacy:
  TEAM-A · compliance".
- **Say:** *"Managers get aggregate readiness and risk — never individual data.
  Groups below three learners are suppressed by k-anonymity. The critic scans
  every manager response for identifiers; our eval gate fails the build if a
  single one leaks."*
- **Optional cut:** terminal showing `make eval` → **Manager PII-leak total: 0**.

### 4:00–4:40 — Evals, tracing, real Learn content  *(Accuracy 25% · Creativity 15%)*
- **Do:** Show the terminal `make eval` scorecard: **Citation grounding 100%,
  PII-leak 0, routing 100%, 55 cases**.
- **Say:** *"Grounding is enforced as a hard gate — not a hope. Citations trace to
  Foundry IQ and to real Microsoft Learn pages via the Learn MCP server."*
- **Point at:** a Microsoft Learn citation chip (blue, opens a real learn.microsoft.com URL).

### 4:40–5:00 — Architecture + deployment + oversight close
- **Do:** Show `docs/architecture.md` Mermaid diagram and mention the Foundry
  Hosted Agent path (`deploy/`).
- **Say:** *"Built on the Microsoft Agent Framework, grounded by Foundry IQ, with
  Work IQ and Fabric IQ context layers, deployable as a Foundry Hosted Agent. The
  AI is decision-support — a learning lead always has the final say. Try an
  out-of-corpus cert and watch it safely abstain."*
- **Optional cut:** Click **"Out-of-corpus (AWS)"** → safe abstain message.

---

## Exact cases to run live
| Preset | Demonstrates |
|---|---|
| AZ-204 learner (English) | Full fan-out, citations, trace |
| Over-capacity clinician (L-1012) | Capacity-aware plan (14 weeks) + Work IQ |
| Strong learner (L-1005) | Contrast schedule (shorter) |
| Manager view (all teams) | PII-safe aggregation + suppression + risks |
| Out-of-corpus (AWS) | Safe abstain |
| Catalan input | Responds in the learner's language |

## Voiceover length check
~640 words of narration ≈ 4:50 at a natural pace, leaving buffer for clicks.
