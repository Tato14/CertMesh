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

### 1:45–2:45 — Assessment: exam mode with live scoring  *(Relevance · UX 15%)*
- **Do:** On the Learner tab run **"Over-capacity clinician (L-1012)"** if not
  already, then click **"Take it as an exam →"**.
- **Show:** questions one at a time, progress bar, no answers revealed until
  submit. Answer a few wrong on purpose. Submit → the gauge animates to your score
  against the **80% Fabric IQ threshold**; each question shows the explanation and
  its **citation chip** (Microsoft Learn links are clickable).
- **Do:** Click **"↻ Back into the preparation loop"** — a failed attempt re-runs
  planning, closing the baseline loop on screen.
- **Say:** *"Every question is grounded — the correct option is a verbatim slice of
  the approved corpus, and the critic enforces that. Fail, and you're routed back
  into preparation, not left with a score."*

### 2:45–4:00 — The trace: watch the agents think  *(Reasoning 25%)*
- **Do:** Click preset **"AZ-204 learner (English)"** — the collapsible
  **Orchestration** panel unfolds automatically on the right as the run starts.
- **Show:** the plan reasoning sentence at the top ("why these agents, in this
  order"), then each node pulse through pending → running → ok. At the
  **Assessment Agent**, the critic rejects the draft — the node flashes the revise
  verdict and ends with a dashed **loop-back arc + "↻ revision ×1"** badge.
- **Do:** Click that node — the detail shows the exact rejected claim, the critic's
  note, both iterations with real timings, and the retrieved sources.
- **Say:** *"This is the reflection loop, live: the agent synthesised a rationale
  that wasn't verbatim-grounded, the critic caught it, the agent revised, and the
  final answer cites real source text. The replay uses the real step timings."*
- **Point at:** the closing **Critic / Verifier** node: claims grounded, revisions
  forced, PII findings 0.

### 4:00–5:00 — Manager heatmap + the eval gate  *(Safety 20% · Accuracy 25%)*
- **Do:** Click **"Manager view (all teams)"**.
- **Show:** the teams × tracks readiness heatmap; the **TEAM-A · compliance** cell
  renders **🔒 n < 3 suppressed** — k-anonymity as a designed state, not an
  omission. Severity-coded risk cards; the team trend line (aggregate only); the
  **PII-safe · aggregate only** badge.
- **Do:** Cut to the terminal: `make eval`.
- **Show:** **55 cases · citation grounding 100% (hard gate) · manager PII-leak 0
  (hard gate) · routing 100% · abstention 100%**.
- **Say:** *"Managers see readiness and risk, never people. The critic scans every
  manager response for identifiers, and CI fails on a single leak. Grounding and
  privacy aren't claims here — they're gates."*
- **Optional 5s close:** click **"Out-of-corpus (AWS)"** → the designed
  **Grounded abstain** state: *"outside the approved KB, it refuses and routes to a
  human — safety as a feature."*

---

## Exact presets to run live
| Preset card | Demonstrates |
|---|---|
| Role path: DevOps Engineer | Fabric IQ graph, role path + learner overlay, graph→agents handoff |
| Calendar contrast: L-1012 vs L-1005 | Work IQ capacity calendar, slot rationale, .ics export |
| Over-capacity clinician (L-1012) | Capacity-aware plan + progress chart + mini-week |
| AZ-204 learner (English) | Full fan-out, animated trace, reflection loop |
| Manager view (all teams) | Heatmap + k-anonymity suppression + risks + trend |
| Out-of-corpus (AWS) | Designed grounded-abstain state |
| Strong learner (L-1005) / Catalan input | Contrast schedule · language handling (if time allows) |

## Voiceover length check
~630 words of narration ≈ 4:50 at a natural pace, leaving buffer for clicks.
