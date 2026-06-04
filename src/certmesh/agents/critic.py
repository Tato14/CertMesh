"""Critic / Verifier — the cross-cutting grounding and safety control.

Before any answer that claims sources is returned (curator content, assessment
questions), the critic checks that every cited snippet and every quoted summary
claim is a verbatim substring of what the producing agent actually retrieved. If
not, it tells the agent to revise (bounded self-reflection) or, once the retry
budget is spent, to abstain and flag for human review.

For the manager view it independently scans the output for individual identifiers
and for any group reported below the k-anonymity threshold. This is the safety
gate the CI enforces: assessment/curator grounding == 1.0 and manager PII == 0.
"""

from __future__ import annotations

import re

from ..iq.foundry_iq import supports
from ..schemas import CriticVerdict
from .base import AgentOutput

NAME = "Critic / Verifier"
MAX_ITERS = 2  # total drafts allowed for a grounded agent (draft 0 + one revise)

# Synthetic individual identifiers that must never appear in a manager view.
_PII_RE = re.compile(r"\bL-\d{4}\b|\bEMP-\d{3}\b")


class Critic:
    name = NAME

    # -- grounding (curator, assessment) -------------------------------------
    def verify_grounded(self, agent: str, out: AgentOutput, iteration: int,
                        max_iters: int = MAX_ITERS) -> CriticVerdict:
        citations = list(getattr(out.output, "citations", []) or [])
        obligations: list[tuple[str, str]] = [("citation", c.snippet) for c in citations]
        obligations += [("summary", q) for q in out.quoted_claims]

        checked = len(obligations)
        ungrounded: list[str] = []
        for _kind, snippet in obligations:
            if not supports(snippet, out.source_texts):
                ungrounded.append(snippet)
        supported = checked - len(ungrounded)

        grounded = not ungrounded
        if grounded:
            action, notes = "accept", f"All {checked} cited claim(s) grounded in retrieved sources."
        elif iteration < max_iters - 1:
            action = "revise"
            notes = (f"{len(ungrounded)} claim(s) not grounded in sources — returning to "
                     f"{agent} to revise (iteration {iteration + 1}/{max_iters - 1}).")
        else:
            action = "abstain"
            notes = (f"{len(ungrounded)} claim(s) still ungrounded after {max_iters} draft(s) — "
                     f"abstaining and flagging for human review.")

        return CriticVerdict(
            agent=agent, grounded=grounded, claims_checked=checked,
            claims_supported=supported, ungrounded_claims=ungrounded[:8],
            action=action, confidence=round(supported / checked, 3) if checked else 1.0,
            reflection_iteration=iteration, notes=notes,
        )

    # -- privacy (manager insights) ------------------------------------------
    def verify_manager_insights(self, insights) -> CriticVerdict:
        text = insights.model_dump_json()
        findings = sorted(set(_PII_RE.findall(text)))
        for s in insights.summaries:
            if s.n_learners < insights.min_group_size:
                findings.append(f"group below k-anonymity: {s.scope} (n={s.n_learners})")

        safe = not findings
        # keep the schema's own flag honest
        insights.pii_safe = safe
        action = "accept" if safe else "abstain"
        notes = ("No individual identifiers and no sub-threshold groups in the manager view."
                 if safe else
                 "Potential PII / sub-threshold group detected — suppressing and flagging for review.")
        return CriticVerdict(
            agent="Manager Insights Agent", grounded=safe,
            claims_checked=len(insights.summaries),
            claims_supported=len(insights.summaries),
            pii_findings=findings[:8], action=action,
            confidence=1.0 if safe else 0.0, notes=notes,
        )

    # -- trivial pass for non-grounded planning agents -----------------------
    def note_ok(self, agent: str, detail: str) -> CriticVerdict:
        return CriticVerdict(agent=agent, grounded=True, action="accept", notes=detail)
