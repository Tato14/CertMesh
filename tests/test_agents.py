"""Per-agent behaviour, exercised through the agents directly."""

import pytest

from certmesh.agents import (
    AssessmentAgent,
    CuratorAgent,
    EngagementAgent,
    ManagerInsightsAgent,
    StudyPlanAgent,
)
from certmesh.agents.base import AgentContext
from certmesh.data_access import get_learner_store
from certmesh.iq.fabric_iq import get_fabric_iq
from certmesh.iq.foundry_iq import get_foundry_iq, supports
from certmesh.iq.work_iq import get_work_iq
from certmesh.tools.ms_learn_mcp import get_ms_learn


def make_ctx(cert, role="Cloud Platform Engineer", learner_id=None, hours=None,
             track="technical", view="learner", team=None, language="en"):
    learner = get_learner_store().get(learner_id)
    return AgentContext(
        cert_code=cert, role=role, track=track, language=language, view=view,
        learner=learner, employee_id=(learner.employee_id if learner else None),
        available_hours_per_week=hours, team=team,
        fabric=get_fabric_iq(), foundry=get_foundry_iq(),
        work=get_work_iq(), ms_learn=get_ms_learn(),
    )


def test_curator_all_resources_cited_and_grounded():
    out = CuratorAgent().draft(make_ctx("AZ-204"))
    path = out.output
    assert path.resources and path.skills
    for r in path.resources:
        assert r.citation.snippet
    # every cited snippet is grounded in the retrieved sources
    for c in path.citations:
        assert supports(c.snippet, out.source_texts)


def test_curator_includes_ms_learn_for_real_exam():
    out = CuratorAgent().draft(make_ctx("AZ-204"))
    kinds = {r.citation.kind for r in out.output.resources}
    assert "ms_learn" in kinds  # real Learn URL appears for a real exam code


def test_curator_internal_cert_has_no_learn_but_is_grounded():
    out = CuratorAgent().draft(make_ctx("CLIN-SAFE-1", role="Clinical Systems Specialist",
                                        track="clinical"))
    assert out.output.resources
    # internal certs have no Microsoft Learn content — honest, still grounded
    assert all(c.kind == "foundry_iq" for c in out.output.citations)


@pytest.mark.parametrize("cert,hours", [("CLIN-SAFE-2", None), ("AZ-204", 2.0), ("DP-203", 1.0)])
def test_study_plan_never_exceeds_focus_capacity(cert, hours):
    ctx = make_ctx(cert, learner_id="L-1012" if cert == "CLIN-SAFE-2" else None, hours=hours)
    plan = StudyPlanAgent().run(ctx).output
    cap = plan.capacity
    weekly = cap.available_total_hours / cap.weeks
    assert weekly <= cap.available_hours_per_week + 1e-6
    assert cap.fits


def test_study_plan_constrained_takes_more_weeks_than_strong():
    constrained = StudyPlanAgent().run(make_ctx("AZ-204", hours=3.0)).output
    strong = StudyPlanAgent().run(make_ctx("AZ-204", hours=8.0)).output
    assert constrained.total_weeks > strong.total_weeks


def test_study_plan_sequences_prerequisites_first():
    plan = StudyPlanAgent().run(make_ctx("AZ-400", role="DevOps Engineer")).output
    assert plan.milestones[0].prerequisites == ["AZ-900", "AZ-204"]


def test_engagement_adapts_to_constrained_rhythm():
    eng = EngagementAgent().run(make_ctx("CLIN-SAFE-2", learner_id="L-1012")).output
    assert eng.preferred_slot == "lunch"
    assert "spread out" in eng.capacity_note.lower() or "reduced" in eng.capacity_note.lower()
    assert eng.weekly_windows


def test_assessment_questions_are_grounded():
    out = AssessmentAgent().draft(make_ctx("AZ-204"), iteration=1)
    a = out.output
    assert len(a.questions) >= 5
    for q in a.questions:
        assert q.options[q.answer_index]  # a correct option exists
        assert supports(q.citation.snippet, out.source_texts)


def test_assessment_draft0_has_one_ungrounded_then_draft1_clean():
    ctx = make_ctx("AZ-204")
    d0 = AssessmentAgent().draft(ctx, iteration=0)
    ungrounded0 = [q for q in d0.output.questions if not supports(q.citation.snippet, d0.source_texts)]
    assert len(ungrounded0) == 1  # the synthesis question is ungrounded in draft 0
    d1 = AssessmentAgent().draft(ctx, iteration=1)
    ungrounded1 = [q for q in d1.output.questions if not supports(q.citation.snippet, d1.source_texts)]
    assert ungrounded1 == []


def test_assessment_readiness_bands():
    ready = AssessmentAgent().draft(make_ctx("AZ-204", learner_id="L-1005"), 1).output
    assert ready.readiness == "ready" and ready.passed
    notready = AssessmentAgent().draft(make_ctx("DP-203", learner_id="L-1006"), 1).output
    assert notready.readiness == "not_ready" and not notready.passed


def test_assessment_rationale_localized():
    ca = AssessmentAgent().draft(make_ctx("AZ-204", language="ca"), 1).output
    assert "llindar" in ca.rationale  # Catalan-only term
    es = AssessmentAgent().draft(make_ctx("AZ-204", language="es"), 1).output
    assert "umbral" in es.rationale   # Spanish-only term
    en = AssessmentAgent().draft(make_ctx("AZ-204", language="en"), 1).output
    assert "threshold" in en.rationale


def test_manager_insights_aggregates_and_suppresses():
    mi = ManagerInsightsAgent().run(make_ctx(None, view="manager")).output
    assert mi.summaries and mi.pii_safe
    assert all(s.n_learners >= mi.min_group_size for s in mi.summaries)
    assert "TEAM-A · compliance" in mi.suppressed_groups  # single-person group suppressed
    assert any(r.kind == "exam_risk" for r in mi.risks)
