"""Pydantic data contracts for every agent input/output and the orchestration
trace. These types are the *interface* between the orchestrator, the five
specialist agents, the critic and the IQ layers — and the shape the dashboard
and evaluators consume.

Two design choices make the system testable and CI-gateable:

* **Citations are first-class.** Any agent claim that asserts a certification
  fact, a resource, or an assessment question carries a :class:`Citation` whose
  ``snippet`` must be a verbatim slice of a retrieved source. The critic checks
  that contract deterministically (see ``agents/critic.py``).
* **Everything is plain data.** No method does I/O. Agents return these models;
  the orchestrator assembles them into an :class:`OrchestrationResult` with a
  fully inspectable :class:`OrchestrationTrace`.

All identifiers and content are SYNTHETIC (e.g. ``L-1001``, ``EMP-001``).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["en", "ca", "es", "other"]
SourceKind = Literal["foundry_iq", "ms_learn"]
View = Literal["learner", "manager"]


# ───────────────────────── retrieval & grounding primitives ─────────────────

class EvidenceSpan(BaseModel):
    """A located substring of some text (used for concept matching / highlighting)."""

    text: str
    start: int
    end: int
    field: str = "note"


class Citation(BaseModel):
    """A grounded reference. ``snippet`` MUST be a verbatim slice of the source
    chunk it points at — the critic enforces this. ``url`` is set for Microsoft
    Learn citations and optionally for Foundry IQ blob sources."""

    source_id: str
    title: str
    snippet: str
    locator: str = ""                 # human pointer, e.g. "Enablement Guide › AZ-204"
    url: str | None = None
    kind: SourceKind = "foundry_iq"
    score: float = 0.0


class RetrievedChunk(BaseModel):
    """A unit of retrieved knowledge returned by an IQ retriever."""

    id: str
    title: str
    text: str
    source: str                       # file name or Learn doc id
    url: str | None = None
    kind: SourceKind = "foundry_iq"
    score: float = 0.0
    locator: str = ""

    def to_citation(self, snippet: str | None = None) -> Citation:
        return Citation(
            source_id=self.id,
            title=self.title,
            snippet=(snippet or self.text)[:400],
            locator=self.locator or self.title,
            url=self.url,
            kind=self.kind,
            score=self.score,
        )


class RetrievalResult(BaseModel):
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    backend: str = "local"            # "azure_search" | "local" | "ms_learn_mcp"

    @property
    def is_empty(self) -> bool:
        return len(self.chunks) == 0


# ───────────────────────────── domain records ──────────────────────────────

ExamOutcome = Literal["pass", "fail", "not_attempted"]


class Learner(BaseModel):
    learner_id: str
    employee_id: str = ""             # links to WorkSignal; shares numeric suffix
    role: str
    track: str = "technical"          # clinical | technical | compliance
    team: str = "TEAM-A"
    certification: str
    practice_score_avg: float = 0.0   # 0..1
    hours_studied: float = 0.0
    exam_outcome: ExamOutcome = "not_attempted"


class WorkSignal(BaseModel):
    employee_id: str
    meeting_hours_per_week: float
    focus_hours_per_week: float
    preferred_learning_slot: str      # e.g. "early_morning" | "lunch" | "late_afternoon"


# ─────────────────────────── orchestration request ─────────────────────────

class LearningRequest(BaseModel):
    """A request from the dashboard or API. Most fields are optional; the
    orchestrator infers role/cert/capacity from the synthetic datasets when not
    supplied."""

    request_id: str = "req-local"
    view: View = "learner"
    goal: str = ""                    # free text, any supported language
    certification: str | None = None
    role: str | None = None
    learner_id: str | None = None
    team: str | None = None
    track: str | None = None
    available_hours_per_week: float | None = None  # override learner capacity
    language: Language | None = None               # explicit hint; else detected


# ──────────────────────────── Learning Path Curator ────────────────────────

ResourceKind = Literal["module", "doc", "guide", "assessment", "learning_path"]


class Resource(BaseModel):
    title: str
    kind: ResourceKind = "module"
    skill: str
    est_hours: float = 2.0
    citation: Citation


class CuratedPath(BaseModel):
    certification: str
    role: str
    skills: list[str] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)
    summary: str = ""                 # grounded prose; every claim cited
    citations: list[Citation] = Field(default_factory=list)


# ──────────────────────────── Study Plan Generator ─────────────────────────

Difficulty = Literal["foundational", "intermediate", "advanced"]


class Milestone(BaseModel):
    order: int
    week: int
    skill: str
    title: str
    hours: float
    difficulty: Difficulty = "intermediate"
    prerequisites: list[str] = Field(default_factory=list)
    citation: Citation | None = None


class CapacityCheck(BaseModel):
    available_hours_per_week: float
    weeks: int
    available_total_hours: float
    allocated_total_hours: float
    recommended_total_hours: float
    utilisation: float                # allocated / available_total
    fits: bool
    note: str = ""


class StudyPlan(BaseModel):
    certification: str
    role: str
    milestones: list[Milestone] = Field(default_factory=list)
    capacity: CapacityCheck
    total_weeks: int = 0
    pass_threshold: float = 0.7
    citations: list[Citation] = Field(default_factory=list)


# ──────────────────────────────── Engagement ───────────────────────────────

class StudyWindow(BaseModel):
    day: str                          # Mon..Sun
    slot: str                         # e.g. "08:00–08:45"
    minutes: int = 45
    rationale: str = ""


class EngagementPlan(BaseModel):
    preferred_slot: str
    weekly_windows: list[StudyWindow] = Field(default_factory=list)
    next_reminder: str = ""
    cadence: str = ""
    weekly_capacity_minutes: int = 0
    capacity_note: str = ""
    privacy_note: str = (
        "Scheduling uses aggregate work-rhythm signals only; no meeting content "
        "or calendar details are read."
    )


# ──────────────────────────────── Assessment ───────────────────────────────

class AssessmentQuestion(BaseModel):
    id: str
    stem: str
    options: list[str]
    answer_index: int
    explanation: str
    skill: str
    difficulty: Difficulty = "intermediate"
    citation: Citation


ReadinessBand = Literal["ready", "borderline", "not_ready"]


class Assessment(BaseModel):
    certification: str
    questions: list[AssessmentQuestion] = Field(default_factory=list)
    estimated_score: float = 0.0      # 0..1 readiness estimate
    threshold: float = 0.7
    readiness: ReadinessBand = "not_ready"
    passed: bool = False
    rationale: str = ""
    next_recommendation: str = ""
    citations: list[Citation] = Field(default_factory=list)


# ───────────────────────────── Manager Insights ────────────────────────────

class TeamReadiness(BaseModel):
    scope: str                        # e.g. "TEAM-A · technical"
    track: str
    n_learners: int
    avg_practice_score: float
    pct_on_track: float
    readiness_band: ReadinessBand


RiskKind = Literal["capacity", "exam_risk", "coverage"]


class RiskFlag(BaseModel):
    kind: RiskKind
    scope: str
    severity: Literal["low", "medium", "high"]
    detail: str


class ManagerInsights(BaseModel):
    generated_for: str = "all teams"
    min_group_size: int = 3           # k-anonymity threshold for aggregation
    summaries: list[TeamReadiness] = Field(default_factory=list)
    risks: list[RiskFlag] = Field(default_factory=list)
    pii_safe: bool = True
    suppressed_groups: list[str] = Field(default_factory=list)
    notes: str = ""


# ───────────────────────────── Critic / Verifier ───────────────────────────

CriticAction = Literal["accept", "revise", "abstain"]


class CriticVerdict(BaseModel):
    agent: str
    grounded: bool
    claims_checked: int = 0
    claims_supported: int = 0
    ungrounded_claims: list[str] = Field(default_factory=list)
    pii_findings: list[str] = Field(default_factory=list)
    action: CriticAction = "accept"
    confidence: float = 1.0
    reflection_iteration: int = 0
    notes: str = ""

    @property
    def grounding_rate(self) -> float:
        if self.claims_checked == 0:
            return 1.0
        return self.claims_supported / self.claims_checked


# ──────────────────────────── Orchestration trace ──────────────────────────

StepStatus = Literal["ok", "revised", "abstained", "skipped", "error"]


class PlanDecision(BaseModel):
    view: View
    agents_to_run: list[str] = Field(default_factory=list)
    reasoning: str = ""


class TraceStep(BaseModel):
    step_no: int
    agent: str
    action: str
    inputs: dict = Field(default_factory=dict)
    output_summary: str = ""
    sources: list[Citation] = Field(default_factory=list)
    critic: CriticVerdict | None = None
    reflections: int = 0
    duration_ms: float = 0.0
    status: StepStatus = "ok"


class OrchestrationTrace(BaseModel):
    request_id: str
    plan: PlanDecision
    steps: list[TraceStep] = Field(default_factory=list)
    model_backend: str = "offline_stub"
    retrieval_backend: str = "local"
    language: Language = "en"
    total_duration_ms: float = 0.0


class OrchestrationResult(BaseModel):
    """The complete, demo-able output of one orchestrated request."""

    request: LearningRequest
    language: Language = "en"
    plan: PlanDecision
    curated_path: CuratedPath | None = None
    study_plan: StudyPlan | None = None
    engagement_plan: EngagementPlan | None = None
    assessment: Assessment | None = None
    manager_insights: ManagerInsights | None = None
    trace: OrchestrationTrace
    abstained: bool = False
    confidence: float = 1.0
    messages: list[str] = Field(default_factory=list)

    @property
    def all_citations(self) -> list[Citation]:
        cites: list[Citation] = []
        for part in (self.curated_path, self.study_plan, self.assessment):
            if part is not None:
                cites.extend(getattr(part, "citations", []) or [])
        return cites
