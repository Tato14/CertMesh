"""Shared agent context and output wrapper.

``AgentContext`` is the resolved request the orchestrator hands to every agent
(certification, role, learner, capacity, language + the IQ layers). ``AgentOutput``
is what an agent returns: its typed result plus the *source texts* it relied on,
so the critic can verify grounding against exactly what the agent retrieved.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..iq.fabric_iq import FabricIQ
from ..iq.foundry_iq import FoundryIQ
from ..iq.work_iq import WorkIQ
from ..schemas import Citation, Language, Learner
from ..tools.ms_learn_mcp import MsLearnMCP


@dataclass
class AgentContext:
    cert_code: str | None
    role: str
    track: str
    language: Language
    view: str = "learner"
    learner: Learner | None = None
    employee_id: str | None = None
    available_hours_per_week: float | None = None
    team: str | None = None
    goal: str = ""

    # IQ layers + tools (injected so agents never construct their own).
    fabric: FabricIQ = None  # type: ignore[assignment]
    foundry: FoundryIQ = None  # type: ignore[assignment]
    work: WorkIQ = None  # type: ignore[assignment]
    ms_learn: MsLearnMCP = None  # type: ignore[assignment]


@dataclass
class AgentOutput:
    """An agent's result plus everything the critic and trace need."""

    output: object                       # the typed schema (CuratedPath, …)
    summary: str = ""
    sources: list[Citation] = field(default_factory=list)       # for display
    source_texts: list[str] = field(default_factory=list)       # for grounding
    quoted_claims: list[str] = field(default_factory=list)      # summary facts to verify
    reflections: int = 0
    notes: list[str] = field(default_factory=list)
    abstained: bool = False
