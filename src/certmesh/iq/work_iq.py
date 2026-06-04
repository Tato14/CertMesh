"""Work IQ — concept-faithful context layer over synthetic work signals.

Microsoft's Work IQ surfaces M365 work-context signals (meeting load, focus time,
working patterns). Here we provide the *same shape* of signal from
data/work_signals.json — aggregate weekly meeting hours, focus hours and a
preferred learning slot — with **no** calendar or message content. The upgrade
path (a real Work IQ / Microsoft Graph connector) is documented in
docs/iq-layers.md; agents consume this interface unchanged.

Privacy by design: the only identifier is a synthetic ``employee_id`` and only
aggregate weekly figures are exposed; nothing here is content-bearing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from ..config import Config, load_config
from ..schemas import WorkSignal

# Concrete time windows per preferred slot (45-minute sessions).
SLOT_WINDOWS: dict[str, str] = {
    "early_morning": "08:00–08:45",
    "lunch": "12:30–13:15",
    "late_afternoon": "16:30–17:15",
    "evening": "19:30–20:15",
}
DEFAULT_FOCUS_HOURS = 6.0
CAPACITY_CONSTRAINED_FOCUS = 6.0  # avg weekly focus hours below this == constrained


@dataclass
class TeamCapacity:
    n: int
    avg_meeting_hours: float
    avg_focus_hours: float
    constrained: bool


class WorkIQ:
    def __init__(self, config: Config | None = None):
        self.config = config or load_config()
        self._signals = self._load()

    def _load(self) -> dict[str, WorkSignal]:
        path = self.config.data_dir / "work_signals.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        out: dict[str, WorkSignal] = {}
        for rec in data.get("records", []):
            sig = WorkSignal(**rec)
            out[sig.employee_id] = sig
        return out

    def signal(self, employee_id: str | None) -> WorkSignal:
        if employee_id and employee_id in self._signals:
            return self._signals[employee_id]
        # Unknown / anonymous learner: a neutral default so planning still works.
        return WorkSignal(
            employee_id=employee_id or "anonymous",
            meeting_hours_per_week=15.0,
            focus_hours_per_week=DEFAULT_FOCUS_HOURS,
            preferred_learning_slot="lunch",
        )

    def available_focus_hours(self, employee_id: str | None) -> float:
        return self.signal(employee_id).focus_hours_per_week

    def preferred_slot(self, employee_id: str | None) -> str:
        return self.signal(employee_id).preferred_learning_slot

    def slot_window(self, employee_id: str | None) -> str:
        return SLOT_WINDOWS.get(self.preferred_slot(employee_id), "12:30–13:15")

    def is_capacity_constrained(self, employee_id: str | None) -> bool:
        return self.available_focus_hours(employee_id) < CAPACITY_CONSTRAINED_FOCUS

    def team_capacity(self, employee_ids: list[str]) -> TeamCapacity:
        sigs = [self.signal(e) for e in employee_ids if e in self._signals]
        if not sigs:
            return TeamCapacity(0, 0.0, 0.0, False)
        avg_meet = sum(s.meeting_hours_per_week for s in sigs) / len(sigs)
        avg_focus = sum(s.focus_hours_per_week for s in sigs) / len(sigs)
        return TeamCapacity(
            n=len(sigs),
            avg_meeting_hours=round(avg_meet, 1),
            avg_focus_hours=round(avg_focus, 1),
            constrained=avg_focus < CAPACITY_CONSTRAINED_FOCUS,
        )


@lru_cache(maxsize=1)
def get_work_iq() -> WorkIQ:
    return WorkIQ()
