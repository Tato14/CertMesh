"""Engagement Agent.

Keeps learners progressing by scheduling study around their real work rhythm.
Grounded by the Work IQ context layer (synthetic meeting-load, focus-hours,
preferred slot). Chooses reminder timing and study windows from the learner's
rhythm rather than a one-size-fits-all schedule, and is privacy-conscious: it
uses aggregate signals only, never calendar or message content.

Reasoning pattern: context-conditioned planning over the Work IQ signal.
"""

from __future__ import annotations

import math

from ..i18n import t
from ..iq.work_iq import SLOT_WINDOWS
from ..schemas import EngagementPlan, StudyWindow
from .base import AgentContext, AgentOutput

NAME = "Engagement Agent"
_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_SESSION_MINUTES = 45


class EngagementAgent:
    name = NAME

    def run(self, ctx: AgentContext, weekly_study_hours: float | None = None) -> AgentOutput:
        sig = ctx.work.signal(ctx.employee_id)
        slot = sig.preferred_learning_slot
        window = SLOT_WINDOWS.get(slot, "12:30–13:15")
        start_time = window.split("–")[0]

        focus = (ctx.available_hours_per_week
                 if ctx.available_hours_per_week is not None
                 else sig.focus_hours_per_week)
        weekly = weekly_study_hours if weekly_study_hours is not None else min(focus, 8.0)
        weekly_minutes = int(round(weekly * 60))
        n_sessions = max(1, min(5, math.ceil(weekly_minutes / _SESSION_MINUTES)))

        # Spread sessions across the week, skipping days to leave recovery room
        # when the meeting load is heavy.
        constrained = sig.meeting_hours_per_week >= 22 or focus < 6.0
        day_order = ["Tue", "Thu", "Mon", "Wed", "Fri"] if constrained else _WEEKDAYS[:5]
        windows: list[StudyWindow] = []
        for i in range(n_sessions):
            day = day_order[i % len(day_order)]
            rationale = (
                f"{slot.replace('_', ' ')} slot; fits around ~{sig.meeting_hours_per_week:.0f}h/week of meetings"
            )
            windows.append(StudyWindow(day=day, slot=window, minutes=_SESSION_MINUTES,
                                       rationale=rationale))

        next_day = windows[0].day if windows else "Mon"
        next_reminder = t("reminder.next", ctx.language, day=next_day, time=start_time,
                          slot=slot.replace("_", " "))
        cadence = (
            f"{n_sessions} × {_SESSION_MINUTES}-min sessions/week in the {slot.replace('_', ' ')} slot"
        )
        capacity_note = (
            "Sessions reduced and spread out because of a heavy meeting load and limited focus time."
            if constrained else
            "Comfortable cadence given current meeting load and focus time."
        )
        plan = EngagementPlan(
            preferred_slot=slot,
            weekly_windows=windows,
            next_reminder=next_reminder,
            cadence=cadence,
            weekly_capacity_minutes=weekly_minutes,
            capacity_note=capacity_note,
        )
        return AgentOutput(output=plan, summary=f"{cadence}. {next_reminder}")
