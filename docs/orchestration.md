# Orchestration — planner–executor, critic & reflection

The orchestrator (`src/certmesh/orchestrator.py`) is the top-level agent. It
applies three named reasoning patterns explicitly and exposes the whole
collaboration as an inspectable `OrchestrationTrace`.

## Patterns

1. **Planner–Executor.** The orchestrator first *plans* which specialists to run
   (the routing decision), then *executes* them in order and *aggregates* the
   typed results. The plan and its reasoning are the **first step** in the trace.
2. **Critic / self-reflection (bounded retries).** Grounded agents (Curator,
   Assessment) are run as `draft(iteration, feedback)`. After each draft the
   **critic** verifies grounding. If a claim is ungrounded the orchestrator hands
   the feedback back to the agent for one revision; if the retry budget
   (`MAX_ITERS = 2`) is spent, the agent **abstains** and the result is flagged
   for human review.
3. **Verifier / guardrail.** For the manager view the critic runs a PII +
   k-anonymity scan instead of a grounding check; a finding forces an abstain.

## Routing logic

| Condition | Plan |
|---|---|
| `view == manager` | `[Manager Insights Agent]` |
| learner view, certification resolved (from field, learner record, goal text, or inferred from role) | `[Curator, Study Plan, Engagement, Assessment]` |
| learner view, no cert, goal names an out-of-corpus target (e.g. "AWS", a foreign exam code) | abstain → `unknown_cert` |
| learner view, no cert and nothing specific | abstain → `ambiguous` (ask to clarify) |

Routing accuracy is measured by the eval harness (`routing` + `language` cases).

## The reflection loop, concretely

The Assessment agent's first draft includes a *synthesis* question whose
rationale combines two source facts into one sentence — which is **not** a
verbatim substring of any single source. The critic catches it and asks for a
revision; the second draft cites a verbatim sentence. Both drafts appear in the
trace, so the loop is visible:

```
[0] Orchestrator           plan      ok       → Curator, Study Plan, Engagement, Assessment
[1] Learning Path Curator  draft     ok       critic=accept (9/9 grounded)   1.6ms
[2] Study Plan Generator   run       ok       critic=accept                  0.6ms
[3] Engagement Agent       run       ok       critic=accept                  0.1ms
[4] Assessment Agent       draft     revised  critic=revise (5/6 grounded)   0.5ms
[5] Assessment Agent       revise    ok       critic=accept (6/6 grounded)   0.5ms
```

Step [4]→[5] is the self-reflection loop: the critic rejected the ungrounded
synthesis question, and the agent revised it to a grounded citation. The final
returned output is therefore 100% grounded.

## Trace format (`OrchestrationTrace`)

Each `TraceStep` records:

| field | meaning |
|---|---|
| `step_no`, `agent`, `action` | order, which agent, `plan` / `draft` / `revise` / `run` |
| `inputs` | the resolved inputs handed to the agent |
| `output_summary` | one-line summary of what the agent produced |
| `sources` | the `Citation`s the agent relied on (clickable in the UI) |
| `critic` | the `CriticVerdict`: `action`, `claims_supported/claims_checked`, `pii_findings`, `notes` |
| `reflections` | how many revision iterations this step represents |
| `duration_ms` | per-step latency (also emitted as an OpenTelemetry span) |
| `status` | `ok` / `revised` / `abstained` / `skipped` / `error` |

The top-level result also carries `plan`, `language`, `confidence`
(min of critic confidences), `abstained`, `messages`, and the populated typed
outputs (`curated_path`, `study_plan`, `engagement_plan`, `assessment`,
`manager_insights`). The dashboard's right-hand panel renders the trace top to
bottom; the reflection step is highlighted.

## Observability

Every agent call is wrapped in a `Tracer.span` (`foundry/tracing.py`). Locally
the spans are recorded in-process for the `duration_ms` shown above; when
`APPLICATIONINSIGHTS_CONNECTION_STRING` is set, the Agent Framework's
`configure_otel_providers()` bridges them to Foundry tracing / Azure Monitor.
