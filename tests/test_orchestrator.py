"""End-to-end orchestration: routing, abstention, language, trace, PII safety."""

import re

from certmesh.schemas import LearningRequest

LEARNER_AGENTS = ["Learning Path Curator", "Study Plan Generator",
                  "Engagement Agent", "Assessment Agent"]
_PII = re.compile(r"\bL-\d{4}\b|\bEMP-\d{3}\b")


def test_routing_learner(orch):
    r = orch.run(LearningRequest(view="learner", goal="Prepare for AZ-204"))
    assert r.plan.agents_to_run == LEARNER_AGENTS
    assert r.curated_path and r.study_plan and r.engagement_plan and r.assessment


def test_routing_manager(orch):
    r = orch.run(LearningRequest(view="manager", goal="team readiness"))
    assert r.plan.agents_to_run == ["Manager Insights Agent"]
    assert r.manager_insights is not None


def test_abstain_out_of_corpus(orch):
    r = orch.run(LearningRequest(view="learner", goal="AWS Solutions Architect certification"))
    assert r.abstained and r.plan.agents_to_run == [] and r.messages


def test_abstain_ambiguous(orch):
    r = orch.run(LearningRequest(view="learner", goal="I want to grow"))
    assert r.abstained and r.plan.agents_to_run == []


def test_language_detection(orch):
    assert orch.run(LearningRequest(goal="Vull preparar el certificat AZ-204")).language == "ca"
    assert orch.run(LearningRequest(goal="Quiero preparar la certificación AZ-204")).language == "es"
    assert orch.run(LearningRequest(goal="I need to study for AZ-400")).language == "en"


def test_trace_shows_reflection_loop(orch):
    r = orch.run(LearningRequest(view="learner", goal="AZ-204"))
    statuses = [(s.agent, s.action, s.status) for s in r.trace.steps]
    # the assessment is drafted, revised once, then accepted
    assert ("Assessment Agent", "draft", "revised") in statuses
    assert ("Assessment Agent", "revise", "ok") in statuses
    # the planner reasoning is the first step
    assert r.trace.steps[0].agent == "Orchestrator"


def test_trace_has_critic_verdicts(orch):
    r = orch.run(LearningRequest(view="learner", goal="AZ-204"))
    cur = next(s for s in r.trace.steps if s.agent == "Learning Path Curator")
    assert cur.critic and cur.critic.grounded and cur.critic.claims_checked > 0


def test_capacity_differs_by_learner(orch):
    slow = orch.run(LearningRequest(view="learner", learner_id="L-1012", goal="CLIN-SAFE-2"))
    fast = orch.run(LearningRequest(view="learner", learner_id="L-1005", goal="AZ-204"))
    assert slow.study_plan.total_weeks > fast.study_plan.total_weeks


def test_manager_views_never_leak_pii(orch):
    for team in [None, "TEAM-A", "TEAM-B", "TEAM-C", "TEAM-D"]:
        r = orch.run(LearningRequest(view="manager", team=team, goal="status"))
        assert not _PII.search(r.model_dump_json())
        assert r.manager_insights.pii_safe
