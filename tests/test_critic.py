"""Critic/verifier: grounding detection, bounded reflection, PII scan."""

from certmesh.agents.base import AgentOutput
from certmesh.agents.critic import Critic
from certmesh.schemas import (
    Citation,
    CuratedPath,
    ManagerInsights,
    RiskFlag,
    TeamReadiness,
)

SOURCE = ["Azure Key Vault stores secrets and is accessed using a managed identity."]


def _curated(snippet):
    cite = Citation(source_id="x", title="t", snippet=snippet)
    return AgentOutput(output=CuratedPath(certification="AZ-204", role="r", citations=[cite]),
                       source_texts=SOURCE)


def test_critic_accepts_grounded_claim():
    out = _curated("Azure Key Vault stores secrets and is accessed using a managed identity.")
    v = Critic().verify_grounded("Learning Path Curator", out, iteration=0)
    assert v.grounded and v.action == "accept" and v.confidence == 1.0


def test_critic_requests_revision_then_abstains():
    out = _curated("Secrets should be stored in plain text in the codebase.")  # ungrounded
    c = Critic()
    v0 = c.verify_grounded("Learning Path Curator", out, iteration=0)
    assert not v0.grounded and v0.action == "revise"
    v1 = c.verify_grounded("Learning Path Curator", out, iteration=1)
    assert v1.action == "abstain"  # retry budget spent


def test_critic_pii_scan_clean():
    mi = ManagerInsights(summaries=[TeamReadiness(scope="TEAM-A · technical", track="technical",
                                                  n_learners=5, avg_practice_score=0.7,
                                                  pct_on_track=0.8, readiness_band="ready")])
    v = Critic().verify_manager_insights(mi)
    assert v.grounded and not v.pii_findings and mi.pii_safe


def test_critic_pii_scan_catches_identifier():
    mi = ManagerInsights(summaries=[], risks=[RiskFlag(kind="exam_risk", scope="TEAM-B",
                         severity="high", detail="learner L-1006 is far behind")])
    v = Critic().verify_manager_insights(mi)
    assert v.pii_findings and v.action == "abstain" and not mi.pii_safe


def test_critic_pii_scan_catches_subthreshold_group():
    mi = ManagerInsights(min_group_size=3,
                         summaries=[TeamReadiness(scope="TEAM-X · clinical", track="clinical",
                                    n_learners=1, avg_practice_score=0.7, pct_on_track=1.0,
                                    readiness_band="ready")])
    v = Critic().verify_manager_insights(mi)
    assert any("k-anonymity" in f for f in v.pii_findings)
