"""Manager Insights Agent.

Team-level visibility for managers: progress by team/track, capacity-constrained
teams and exam-risk areas. Uses Work IQ (team capacity) + Fabric IQ (thresholds).

Privacy by design — the core safety control of the manager view:
* learners are read ONLY through aggregation;
* a group smaller than ``min_group_size`` (k-anonymity) is suppressed, never
  reported;
* no learner_id, employee_id, name or any individual figure is ever emitted.

The critic independently scans the output for PII patterns; the CI gate fails if
the manager-insight PII-leak rate is above 0.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from ..data_access import get_learner_store
from ..schemas import ManagerInsights, RiskFlag, TeamReadiness
from .base import AgentContext, AgentOutput

NAME = "Manager Insights Agent"
MIN_GROUP_SIZE = 3


class ManagerInsightsAgent:
    name = NAME

    def run(self, ctx: AgentContext) -> AgentOutput:
        store = get_learner_store()
        learners = store.by_team(ctx.team) if ctx.team else store.all()

        groups: dict[tuple[str, str], list] = defaultdict(list)
        for lr in learners:
            groups[(lr.team, lr.track)].append(lr)

        summaries: list[TeamReadiness] = []
        risks: list[RiskFlag] = []
        suppressed: list[str] = []

        for (team, track), members in sorted(groups.items()):
            scope = f"{team} · {track}"
            if len(members) < MIN_GROUP_SIZE:
                suppressed.append(scope)
                continue

            avg = sum(m.practice_score_avg for m in members) / len(members)
            primary = Counter(m.certification for m in members).most_common(1)[0][0]
            threshold = ctx.fabric.pass_threshold(primary)
            on_track = sum(1 for m in members if m.practice_score_avg >= threshold - 0.1)
            pct_on_track = round(on_track / len(members), 2)
            band = ("ready" if avg >= threshold
                    else "borderline" if avg >= threshold - 0.1 else "not_ready")

            summaries.append(TeamReadiness(
                scope=scope, track=track, n_learners=len(members),
                avg_practice_score=round(avg, 2), pct_on_track=pct_on_track,
                readiness_band=band,
            ))

            # exam-risk flag
            if avg < threshold:
                sev = "high" if avg < threshold - 0.1 else "medium"
                risks.append(RiskFlag(
                    kind="exam_risk", scope=scope, severity=sev,
                    detail=(f"Average practice {avg:.0%} below the {threshold:.0%} pass threshold "
                            f"for {primary}; prioritise focused remediation before booking exams."),
                ))
            # capacity flag (Work IQ)
            cap = ctx.work.team_capacity([m.employee_id for m in members])
            if cap.constrained:
                risks.append(RiskFlag(
                    kind="capacity", scope=scope, severity="medium",
                    detail=(f"Average focus time {cap.avg_focus_hours:.1f}h/week against "
                            f"{cap.avg_meeting_hours:.1f}h of meetings; lengthen schedules rather than weekly hours."),
                ))

        for scope in suppressed:
            risks.append(RiskFlag(
                kind="coverage", scope=scope, severity="low",
                detail=f"Group smaller than {MIN_GROUP_SIZE} learners — suppressed for privacy; not enough data to report.",
            ))

        insights = ManagerInsights(
            generated_for=ctx.team or "all teams",
            min_group_size=MIN_GROUP_SIZE,
            summaries=summaries, risks=risks, pii_safe=True,
            suppressed_groups=suppressed,
            notes=("Aggregate, threshold-based decision-support. No individual learner is "
                   "identified; groups below the k-anonymity threshold are suppressed."),
        )
        summary = (
            f"{len(summaries)} reportable group(s), {len(risks)} risk flag(s), "
            f"{len(suppressed)} group(s) suppressed for privacy."
        )
        return AgentOutput(output=insights, summary=summary)
