# Agents

CertMesh has an orchestrator, five specialist agents and a cross-cutting critic.
Every agent is **deterministic**: it reasons over the IQ layers and returns a
typed [schema](../src/certmesh/schemas.py). The language model (when configured)
is used only for optional natural-language glosses, which the critic re-checks —
never for a routing, capacity, grounding or scoring decision. That is what keeps
the system correct, testable and CI-gated even with no model at all.

| Agent | Responsibility | Grounding / tools | Input → Output |
|---|---|---|---|
| **Orchestrator** | Parse + plan routing (with a **deliberation ledger** of rejected routes + resolution sources), **policy refusal** for unsafe goals, dispatch, aggregate, build the trace | Fabric IQ (resolve cert/role), language detection, unsafe-request patterns | `LearningRequest` → `OrchestrationResult` |
| **Learning Path Curator** | Map cert → role-relevant skills → cited resources | Foundry IQ + Microsoft Learn MCP | ctx → `CuratedPath` |
| **Study Plan Generator** | Capacity-aware schedule, sequenced by difficulty/prereqs | Fabric IQ (skills, prereqs, hours, threshold) + Work IQ (focus hours) | ctx → `StudyPlan` |
| **Engagement Agent** | Reminder timing + study windows from work rhythm | Work IQ (meeting load, focus, preferred slot) | ctx → `EngagementPlan` |
| **Assessment Agent** | Grounded cited questions + readiness scoring | Foundry IQ (facts) + Fabric IQ (threshold) | ctx → `Assessment` |
| **Manager Insights Agent** | Aggregate team readiness + risk, PII-safe | Work IQ (capacity) + Fabric IQ (thresholds) + learner roster (aggregate only) | ctx → `ManagerInsights` |
| **Critic / Verifier** | Verify grounding + scan PII; drive reflection/abstain | Foundry IQ corpus (substring grounding), PII regex + k-anonymity | agent output → `CriticVerdict` |

## 1. Learning Path Curator — `agents/curator.py`
- **Reasoning:** decomposition (cert → skills) + tool-augmented retrieval.
- For each Fabric IQ skill it retrieves a grounded resource from Foundry IQ and emits a `Resource` with a verbatim `Citation`. It then calls the **Microsoft Learn MCP** for real Learn content (present for real exam codes; honestly absent for internal certs).
- The prose `summary` is a meta lead-in plus a single **quoted, verbatim** source snippet, so it carries no unsupported free text.
- Implements `draft(iteration, feedback)` for the critic's reflection loop.

## 2. Study Plan Generator — `agents/study_plan.py`
- **Reasoning:** constraint-satisfaction planning. Weekly study hours never exceed the learner's available focus capacity (Work IQ) — the horizon is extended instead. Skills are sequenced foundational→advanced (Fabric IQ difficulty measure); prerequisite certs are sequenced first; a capstone mock-exam milestone closes the plan.
- **Adaptive re-plan:** when the request carries `focus_skills` (the learner's actual exam mistakes), those skills are front-loaded as "Priority review" milestones with a 1.5× share of the SAME hour pool — totals conserved, so the capacity check is unaffected. The plan reasoning and trace say so explicitly.
- **What-if override:** `available_hours_per_week` re-solves the same plan under a different capacity constraint — the dashboard's live what-if slider.
- Emits a `CapacityCheck` (`fits`, `utilisation`, `weeks`, note) the dashboard renders as a badge.

## 3. Engagement Agent — `agents/engagement.py`
- **Reasoning:** context-conditioned scheduling. Picks 45-minute sessions in the learner's preferred slot, reduces and spreads them when the meeting load is heavy / focus time is low, and sets the next reminder just before the slot.
- Privacy-conscious: aggregate rhythm signals only; never reads calendar/message content.

## 4. Assessment Agent — `agents/assessment.py`
- **Reasoning:** generation + a real self-reflection loop. Each per-skill question's correct option is a **verbatim** fact from Foundry IQ with a citation; distractors are clearly-fabricated generic statements. Readiness is scored against the Fabric IQ pass threshold (`ready` / `borderline` / `not_ready`) and feeds the next-certification recommendation.
- `draft(0)` adds a richer *synthesis* question whose rationale combines two facts (not verbatim → the critic rejects it); `draft(1)` revises it to cite a verbatim source. See [orchestration.md](orchestration.md).

## 5. Manager Insights Agent — `agents/manager_insights.py`
- **Reasoning:** privacy-preserving aggregation. Groups learners by (team, track); groups below the **k-anonymity** threshold (`min_group_size = 3`) are suppressed and never reported. Emits readiness bands and exam-risk / capacity / coverage flags. No `learner_id`, `employee_id`, name or individual figure is ever emitted.

## Critic / Verifier — `agents/critic.py`
- **Grounding:** every citation snippet and every quoted summary claim must be a verbatim substring of the sources the agent retrieved (`verify_grounded`). Ungrounded → `revise` (bounded retries) → `abstain`.
- **Privacy:** `verify_manager_insights` scans the serialized output for individual identifiers and for any sub-threshold group; either → `abstain`. This is the safety gate the CI enforces (PII-leak == 0).
