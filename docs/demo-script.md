# 5-minute demo script

A tight, rubric-mapped walkthrough of the CertMesh dashboard. Start the app
(`make run`) and open <http://localhost:8000>. Every scenario below is a one-click
preset card; each card states what to watch for.

> On-screen one-liner to keep visible: *"All data synthetic — fictional Northwind
> Health workforce certification programme. The calendar is simulated; no real tenant."*

---

### 0:00–0:45 — Knowledge graph: role-based paths  *(Creativity 15% · Relevance 25%)*
- **Do:** The app *lands* on the Graph — the full learning ecosystem (31
  certifications across the Microsoft AZ/AI/DP/SC/PL/MS/MD families plus internal
  ones, 21 roles). Filter by **track** (try *security*), then click preset
  **"Role path: DevOps Engineer"**.
- **Show:** everything else dims; the summary strip reads
  **DevOps Engineer → AZ-900 → AZ-204 → AZ-400 · 3 certs · 160 h · 2 prerequisites**
  with the prerequisite edges dashed amber. (Bigger flex: select role
  *Security Architect* — a 6-cert, 275 h chain.)
- **Do:** Pick a learner in the **Learner overlay** — the path repaints with
  completed / in-progress / at-risk states. Click **AZ-204** → the side panel shows
  its skills, threshold and hours.
- **Say:** *"This is the Fabric IQ semantic layer as a living map — role-based study
  paths in prerequisite order, not a static list. And the graph feeds the agents:"*
- **Do:** Click **"Generate study plan ▸"** — it pre-fills the request and fires a
  real multi-agent run, landing on the Learner tab.

### 0:45–1:45 — Capacity calendar: same engine, different lives  *(Work IQ · Relevance)*
- **Do:** Click preset **"Calendar contrast: L-1012 vs L-1005"**.
- **Show:** two simulated weeks side by side. L-1012: a wall of grey meetings
  (28 h/week), study sessions squeezed into protected **lunch** slots on spread-out
  days. L-1005: an open calendar, five **early-morning** sessions, done in weeks.
- **Do:** Hover a study block — the tooltip explains *why this slot* (preferred
  rhythm, meeting load). Click **⤓ .ics** — the proposed slots download as an
  Outlook-importable calendar, every event labelled `[SYNTHETIC DEMO]`.
- **Say:** *"The Engagement Agent adapts the schedule to how busy someone actually
  is — from aggregate Work IQ signals only. No meeting titles, no content, and the
  week is simulated, never a real tenant."*

### 1:45–2:45 — Exam → ADAPTIVE re-plan (the loop is real)  *(Reasoning 25% · UX 15%)*
- **Do:** On the Learner tab run **"Over-capacity clinician (L-1012)"** if not
  already, then click **"Take it as an exam →"**.
- **Show:** questions one at a time, no answers until submit. Answer 2-3 wrong on
  purpose. Submit → the gauge animates against the **80% Fabric IQ threshold**;
  every question carries its **citation chip** — click one: the **evidence
  inspector** opens the source document with the verbatim cited span highlighted.
- **Do:** Click **"↻ Re-plan around my N weak skills"** — your actual mistakes
  feed back into the planner.
- **Show:** the new plan opens with an amber **"Re-planned from your exam
  mistakes"** banner, the failed skills as **Priority review** milestones at the
  top with extra hours (same total), and the planner's reasoning saying so.
- **Do:** Open the trace panel's **deliberation ledger** on THIS run — it now
  contains *"original milestone order — rejected: exam feedback flags N weak
  skill(s) to front-load"*: the planner visibly changed its mind from evidence.
- **Do:** Drag the **What-if slider** under the plan card.
- **Say:** *"And the plan re-solves live under a different weekly capacity —
  14 weeks at 3 hours, 20 at 2, 7 at 6. Constraint propagation you can feel."*

### 2:45–4:00 — The trace: watch the agents think  *(Reasoning 25%)*
- **Do:** Click preset **"AZ-204 learner (English)"** — the collapsible
  **Orchestration** panel unfolds automatically on the right as the run starts.
- **Show:** the plan reasoning at the top, and open its **deliberation ledger** —
  the routes the planner considered and REJECTED ("manager route — rejected",
  "abstain (out-of-corpus) — rejected: AZ-204 is in the approved knowledge base")
  plus which source actually resolved the certification, role and capacity. Then
  each node pulses through pending → running → ok. At the **Assessment Agent**,
  the critic rejects the draft — the node flashes the revise verdict and ends
  with a dashed **loop-back arc + "↻ revision ×1"** badge.
- **Do:** Click that node — the detail shows the exact rejected claim, the critic's
  note, both iterations with real timings, and the retrieved sources.
- **Say:** *"This is the reflection loop, live: the agent synthesised a rationale
  that wasn't verbatim-grounded, the critic caught it, the agent revised, and the
  final answer cites real source text. The replay uses the real step timings."*
- **Point at:** the closing **Critic / Verifier** node: claims grounded, revisions
  forced, PII findings 0.

### 4:00–5:00 — Attack it, then run the gates live  *(Safety 20% · Accuracy 25%)*
- **Do:** Click **"Red team: prompt injection"** — an attack that even names a
  valid cert (AZ-204).
- **Show:** the planner refuses **by policy before any agent runs**; the
  Orchestrator node lands abstained with the refusal reasoning.
- **Do:** Click **"Red team: PII exfiltration"** (a manager demanding individual
  scores) → the heatmap answers with aggregates, **TEAM-A · compliance** renders
  **🔒 n < 3 suppressed**, and the Critic node reports **0 PII findings**.
- **Do:** Open the **Quality tab** and click **"▶ Re-run 67 gold cases now"**.
- **Show:** the suite executes in seconds, all **six gate chips** go green —
  including **Adversarial block == 1.0** — and the **critic-ablation card**:
  *without the critic, grounding drops to 91.3%; 100/100 fabricated citations
  caught.*
- **Say:** *"You just watched the system get attacked and refuse, and then watched
  its own CI gate pass live. Grounding and privacy aren't claims in a README —
  they're executable, and the ablation proves the gate is load-bearing."*

---

## Exact presets to run live
| Preset card | Demonstrates |
|---|---|
| Role path: DevOps Engineer | Fabric IQ graph, role path + learner overlay, graph→agents handoff |
| Calendar contrast: L-1012 vs L-1005 | Work IQ capacity calendar, slot rationale, .ics export |
| Over-capacity clinician (L-1012) | Capacity-aware plan → exam → **adaptive re-plan from real mistakes** |
| What-if: L-1012 with 6 hours | Counterfactual constraint propagation (+ the live slider) |
| AZ-204 learner (English) | Full fan-out, animated trace, deliberation ledger, reflection loop |
| Red team: prompt injection / PII exfiltration | Policy refusal + aggregate-only defense, CI-gated |
| Manager view (all teams) | Heatmap + k-anonymity suppression + risks + trend |
| Quality tab (no preset) | 67 gold cases live, 6 gates, critic ablation |
| Out-of-corpus (AWS) · Catalan input | Grounded abstain · language handling (if time allows) |

## Voiceover length check
~630 words of narration ≈ 4:50 at a natural pace, leaving buffer for clicks.
