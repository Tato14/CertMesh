"""Planner–Executor orchestrator.

The top-level agent. It (1) parses the request and detects language, (2) plans
which specialists to run and in what order (the routing decision), (3) executes
them, running the critic between drafts so grounded agents can self-correct
(bounded reflection) or abstain, and (4) assembles a typed
:class:`OrchestrationResult` with a fully inspectable :class:`OrchestrationTrace`.

It stays focused on routing/aggregation; all domain reasoning lives in the
specialists and the IQ layers. Deployable as a Foundry Agent Service Hosted
Agent (see deploy/), with a graceful local fallback when no cloud is configured.
"""

from __future__ import annotations

import re
import time

from .agents import (
    AgentContext,
    AssessmentAgent,
    Critic,
    CuratorAgent,
    EngagementAgent,
    ManagerInsightsAgent,
    StudyPlanAgent,
)
from .agents.base import AgentOutput
from .config import Config, load_config
from .data_access import get_learner_store
from .foundry.client import get_model_backend
from .foundry.tracing import Tracer
from .i18n import detect_language, t
from .iq.fabric_iq import get_fabric_iq
from .iq.foundry_iq import get_foundry_iq
from .iq.work_iq import get_work_iq
from .schemas import (
    LearningRequest,
    OrchestrationResult,
    OrchestrationTrace,
    PlanDecision,
    TraceStep,
)
from .tools.ms_learn_mcp import get_ms_learn

# Tokens that signal an externally-named but out-of-corpus target.
_EXTERNAL_HINTS = (
    "aws", "gcp", "google cloud", "kubernetes", "cka", "oracle", "cisco", "ccna",
    "comptia", "blockchain", "quantum", "terraform", "salesforce", "pmp", "scrum",
)
_CODE_RE = re.compile(r"\b[A-Z]{2,}-?\d{2,}\b")
_CERTISH_RE = re.compile(r"\b(certif|exam|certified)\w*", re.IGNORECASE)


def _looks_like_named_target(goal: str) -> bool:
    low = goal.lower()
    if any(h in low for h in _EXTERNAL_HINTS):
        return True
    if _CODE_RE.search(goal):
        return True
    return False


class Orchestrator:
    def __init__(self, config: Config | None = None):
        self.config = config or load_config()
        self.fabric = get_fabric_iq()
        self.foundry = get_foundry_iq()
        self.work = get_work_iq()
        self.ms_learn = get_ms_learn()
        self.learners = get_learner_store()
        self.model = get_model_backend(self.config)
        self.curator = CuratorAgent()
        self.study = StudyPlanAgent()
        self.engagement = EngagementAgent()
        self.assessment = AssessmentAgent()
        self.manager = ManagerInsightsAgent()
        self.critic = Critic()

    # ── resolution ──────────────────────────────────────────────────────────
    def _resolve(self, req: LearningRequest):
        learner = self.learners.get(req.learner_id)
        cert = self.fabric.resolve_cert(req.certification)
        if not cert and learner:
            cert = self.fabric.resolve_cert(learner.certification)
        if not cert and req.goal:
            cert = self.fabric.resolve_cert(req.goal)
        role = req.role or (learner.role if learner else None)
        if not cert and role:
            required = self.fabric.required_certs(role)
            cert = required[0] if required else None
        role = role or (self.fabric.role_for_cert(cert) if cert else None) or "learner"
        track = (req.track or (learner.track if learner else None)
                 or (self.fabric.track_for(cert) if cert else "technical"))
        employee_id = learner.employee_id if learner else None
        return learner, cert, role, track, employee_id

    def _context(self, req, language, cert, role, track, learner, employee_id) -> AgentContext:
        return AgentContext(
            cert_code=cert, role=role, track=track, language=language, view=req.view,
            learner=learner, employee_id=employee_id,
            available_hours_per_week=req.available_hours_per_week,
            team=req.team, goal=req.goal,
            fabric=self.fabric, foundry=self.foundry, work=self.work, ms_learn=self.ms_learn,
        )

    # ── planning ──────────────────────────────────────────────────────────────
    def _plan(self, req, cert, role) -> tuple[PlanDecision, str | None]:
        if req.view == "manager":
            return PlanDecision(
                view="manager",
                agents_to_run=[self.manager.name],
                reasoning=("Manager view: route to the Manager Insights Agent for aggregate, "
                           "PII-safe team readiness and risk; no learner-specific specialists needed."),
            ), None
        if cert:
            return PlanDecision(
                view="learner",
                agents_to_run=[self.curator.name, self.study.name,
                               self.engagement.name, self.assessment.name],
                reasoning=(f"Learner view with a resolved certification ({cert}): curate cited "
                           "content → build a capacity-aware plan → schedule around work rhythm → "
                           "assess readiness with grounded questions. Critic verifies grounding throughout."),
            ), None
        # no cert resolved → abstain (clarify vs out-of-corpus)
        if req.goal and _looks_like_named_target(req.goal):
            return PlanDecision(view="learner", agents_to_run=[],
                                reasoning="Named a certification outside the approved knowledge base — abstaining."), "unknown_cert"
        return PlanDecision(view="learner", agents_to_run=[],
                            reasoning="No certification or role identified — asking the learner to clarify."), "ambiguous"

    # ── execution helpers ─────────────────────────────────────────────────────
    def _timed(self, name: str, fn):
        start = time.perf_counter()
        with self.tracer.span(name):
            out = fn()
        return out, (time.perf_counter() - start) * 1000.0

    def _run_grounded(self, agent, ctx, steps: list[TraceStep], step_no: int):
        """Draft → critic → (revise)* loop. Returns (final_out, final_verdict, next_step_no)."""
        iteration = 0
        action = "draft"
        out: AgentOutput
        verdict = None
        while True:
            out, ms = self._timed(f"{agent.name}:{iteration}",
                                   lambda it=iteration, fb=(verdict.ungrounded_claims if verdict else None):
                                   agent.draft(ctx, it, fb))
            verdict = self.critic.verify_grounded(agent.name, out, iteration)
            status = {"accept": "ok", "revise": "revised", "abstain": "abstained"}[verdict.action]
            steps.append(TraceStep(
                step_no=step_no, agent=agent.name, action=action,
                inputs={"certification": ctx.cert_code, "iteration": iteration},
                output_summary=out.summary, sources=out.sources, critic=verdict,
                reflections=iteration, duration_ms=round(ms, 1), status=status,
            ))
            step_no += 1
            if verdict.action != "revise":
                break
            iteration += 1
            action = "revise"
        return out, verdict, step_no

    def _run_plain(self, agent, ctx, steps, step_no, verdict_fn=None, **kwargs):
        out, ms = self._timed(agent.name, lambda: agent.run(ctx, **kwargs))
        verdict = verdict_fn(out) if verdict_fn else self.critic.note_ok(agent.name, out.summary)
        status = "abstained" if verdict.action == "abstain" else "ok"
        steps.append(TraceStep(
            step_no=step_no, agent=agent.name, action="run",
            inputs={"certification": ctx.cert_code, "view": ctx.view},
            output_summary=out.summary, sources=out.sources, critic=verdict,
            duration_ms=round(ms, 1), status=status,
        ))
        return out, verdict, step_no + 1

    # ── entrypoint ────────────────────────────────────────────────────────────
    def run(self, req: LearningRequest) -> OrchestrationResult:
        self.tracer = Tracer(self.config)
        t0 = time.perf_counter()
        language = detect_language(req.goal or "", req.language)
        learner, cert, role, track, employee_id = self._resolve(req)
        plan, abstain_reason = self._plan(req, cert, role)

        steps: list[TraceStep] = []
        # Step 0: the planner's own reasoning is part of the trace.
        steps.append(TraceStep(
            step_no=0, agent="Orchestrator", action="plan",
            inputs={"view": req.view, "goal": req.goal, "resolved_cert": cert, "role": role},
            output_summary=plan.reasoning + (f" → {', '.join(plan.agents_to_run)}" if plan.agents_to_run else ""),
            status="ok",
        ))

        result = OrchestrationResult(
            request=req, language=language, plan=plan,
            trace=OrchestrationTrace(
                request_id=req.request_id, plan=plan,
                model_backend=self.model.name, retrieval_backend=self.foundry.backend,
                language=language,
            ),
        )

        if abstain_reason:
            msg = t(f"abstain.{abstain_reason}", language)
            result.abstained = True
            result.confidence = 0.0
            result.messages.append(msg)
            steps[0] = steps[0].model_copy(update={"status": "abstained", "output_summary": msg})
            result.trace.steps = steps
            result.trace.total_duration_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            return result

        ctx = self._context(req, language, cert, role, track, learner, employee_id)
        confidences: list[float] = []
        step_no = 1

        if req.view == "manager":
            out, verdict, step_no = self._run_plain(
                self.manager, ctx, steps, step_no,
                verdict_fn=lambda o: self.critic.verify_manager_insights(o.output),
            )
            result.manager_insights = out.output
            confidences.append(verdict.confidence)
            if verdict.action == "abstain":
                result.abstained = True
                result.messages.append(t("review_banner", language))
        else:
            # 1) Curator (grounded, reflection-capable)
            cur_out, cur_v, step_no = self._run_grounded(self.curator, ctx, steps, step_no)
            confidences.append(cur_v.confidence)
            if cur_v.action != "abstain":
                result.curated_path = cur_out.output
            else:
                result.messages.append(t("review_banner", language))

            # 2) Study plan (capacity-aware planning)
            sp_out, _sp_v, step_no = self._run_plain(self.study, ctx, steps, step_no)
            result.study_plan = sp_out.output
            weekly = min(sp_out.output.capacity.available_hours_per_week, 8.0)

            # 3) Engagement (Work IQ rhythm)
            eng_out, _eng_v, step_no = self._run_plain(
                self.engagement, ctx, steps, step_no, weekly_study_hours=weekly)
            result.engagement_plan = eng_out.output

            # 4) Assessment (grounded, reflection loop)
            as_out, as_v, step_no = self._run_grounded(self.assessment, ctx, steps, step_no)
            confidences.append(as_v.confidence)
            if as_v.action != "abstain":
                result.assessment = as_out.output
            else:
                result.abstained = True
                result.messages.append(t("review_banner", language))

        result.confidence = round(min(confidences), 3) if confidences else 1.0
        result.trace.steps = steps
        result.trace.total_duration_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return result


_ORCH: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _ORCH
    if _ORCH is None:
        _ORCH = Orchestrator()
    return _ORCH


def run_request(req: LearningRequest) -> OrchestrationResult:
    return get_orchestrator().run(req)
