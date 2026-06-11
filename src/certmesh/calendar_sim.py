"""Simulated capacity calendar (Work IQ extension).

Renders one SYNTHETIC Mon–Fri week of calendar blocks for an employee that is
*consistent* with their aggregate Work IQ signal: total meeting block hours equal
``meeting_hours_per_week``, focus block hours equal ``focus_hours_per_week``, and
the preferred learning slot is kept meeting-free. Proposed study sessions (the
Engagement Agent's :class:`~certmesh.schemas.StudyWindow` list) are placed inside
that protected window, never over meetings.

Privacy by design, same as Work IQ itself: blocks carry NO titles or content —
only kind + duration. Everything is deterministic per ``employee_id`` so demos
and tests are reproducible, and nothing here reads a real tenant.
"""

from __future__ import annotations

from .schemas import StudyWindow, WorkSignal

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
DAY_START = 8 * 60          # 08:00
DAY_END = 18 * 60           # 18:00
_GRAN = 30                  # blocks snap to 30-minute boundaries

# Centre of each preferred slot, used to pull focus time towards the learner's
# rhythm and push meetings away from it ("evening" clamps to late afternoon
# inside the rendered 08:00–18:00 grid; the study sessions themselves keep
# their real Engagement-Agent times).
_SLOT_CENTER = {
    "early_morning": 8 * 60 + 30,
    "lunch": 12 * 60 + 50,
    "late_afternoon": 16 * 60 + 50,
    "evening": 17 * 60 + 30,
}


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _parse_hhmm(value: str, default: int) -> int:
    try:
        h, m = value.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return default


def _seed(employee_id: str) -> int:
    return sum(ord(ch) for ch in employee_id or "anonymous")


def _split_hours(total: float, seed: int) -> list[float]:
    """Deterministically split weekly hours across 5 days at 30-min granularity."""
    base = [3, 4, 2, 4, 3]
    weights = [base[(i + seed) % 5] for i in range(5)]
    wsum = sum(weights)
    out: list[float] = []
    allocated = 0.0
    for i in range(4):
        h = round(total * weights[i] / wsum * 2) / 2
        h = max(0.0, min(h, (DAY_END - DAY_START) / 60))
        out.append(h)
        allocated += h
    out.append(max(0.0, round((total - allocated) * 2) / 2))
    return out


def _subtract(intervals: list[tuple[int, int]], cut: tuple[int, int]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    cs, ce = cut
    for s, e in intervals:
        if ce <= s or cs >= e:
            out.append((s, e))
            continue
        if s < cs:
            out.append((s, cs))
        if ce < e:
            out.append((ce, e))
    return out


def _carve(free: list[tuple[int, int]], hours: float, chunks: list[int],
           order_key, gap: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Carve ``hours`` worth of blocks out of ``free`` intervals.

    ``chunks`` is a cyclic pattern of block lengths (minutes); ``order_key``
    ranks free intervals (so meetings cluster away from the learner's slot and
    focus time clusters near it). Returns (placed_blocks, remaining_free).
    """
    remaining = int(round(hours * 60 / _GRAN)) * _GRAN
    placed: list[tuple[int, int]] = []
    ci = 0
    guard = 0
    while remaining > 0 and guard < 64:
        guard += 1
        usable = sorted((iv for iv in free if iv[1] - iv[0] >= _GRAN), key=order_key)
        if not usable:
            break
        s, e = usable[0]
        length = min(chunks[ci % len(chunks)], remaining, e - s)
        length = max(_GRAN, (length // _GRAN) * _GRAN)
        block = (s, s + length)
        placed.append(block)
        free = _subtract(free, (block[0], block[1] + gap))
        remaining -= length
        ci += 1
    placed.sort()
    return placed, free


def simulate_week(signal: WorkSignal, windows: list[StudyWindow],
                  study_labels: list[str] | None = None) -> list[dict]:
    """Return a week of blocks: ``{day, start, end, kind, label, rationale}``.

    ``windows`` are the Engagement Agent's proposed sessions; ``study_labels``
    (optional, cycled) label them with concrete study-plan content.
    """
    seed = _seed(signal.employee_id)
    meet_by_day = _split_hours(signal.meeting_hours_per_week, seed)
    focus_by_day = _split_hours(signal.focus_hours_per_week, seed + 3)
    slot_center = _SLOT_CENTER.get(signal.preferred_learning_slot, 12 * 60 + 50)

    by_day: dict[str, list[StudyWindow]] = {}
    for w in windows:
        by_day.setdefault(w.day, []).append(w)

    blocks: list[dict] = []
    for di, day in enumerate(DAYS):
        free = [(DAY_START, DAY_END)]

        # 1) study sessions are first-class: place and protect them.
        protected: list[tuple[int, int]] = []
        for si, w in enumerate(by_day.get(day, [])):
            s = _parse_hhmm(w.start, slot_center)
            e = _parse_hhmm(w.end, s + w.minutes)
            label = None
            if study_labels:
                idx = (sum(1 for d in DAYS[:di] for _ in by_day.get(d, [])) + si)
                label = study_labels[idx % len(study_labels)]
            blocks.append({
                "day": day, "start": _hhmm(s), "end": _hhmm(e), "kind": "study",
                "label": label or "Proposed study session",
                "rationale": w.rationale,
            })
            protected.append((s, e))
        # keep the preferred slot region meeting-free even on non-study days, so
        # the learner's rhythm is visible across the whole week; render it as
        # focus time (drawn from the day's focus budget).
        slot_region = (max(DAY_START, slot_center - 45), min(DAY_END, slot_center + 45))
        focus_left = focus_by_day[di]
        if not by_day.get(day) and focus_left >= 1.0:
            blocks.append({"day": day, "start": _hhmm(slot_region[0]),
                           "end": _hhmm(slot_region[1]), "kind": "focus",
                           "label": "Focus time", "rationale": ""})
            focus_left = max(0.0, focus_left - (slot_region[1] - slot_region[0]) / 60)
        protected.append(slot_region)
        for iv in protected:
            free = _subtract(free, iv)

        # 2) meetings: cluster AWAY from the preferred slot.
        meetings, free = _carve(
            free, meet_by_day[di], chunks=[90, 60, 120, 60][seed % 4:] + [90, 60],
            order_key=lambda iv: -abs((iv[0] + iv[1]) // 2 - slot_center), gap=_GRAN // 2 * (di % 2),
        )
        for s, e in meetings:
            blocks.append({"day": day, "start": _hhmm(s), "end": _hhmm(e), "kind": "meeting",
                           "label": "Meetings — busy (no content read)", "rationale": ""})

        # 3) remaining focus time: cluster NEAR the preferred slot.
        focus, free = _carve(
            free, focus_left, chunks=[90, 60],
            order_key=lambda iv: abs((iv[0] + iv[1]) // 2 - slot_center), gap=0,
        )
        for s, e in focus:
            blocks.append({"day": day, "start": _hhmm(s), "end": _hhmm(e), "kind": "focus",
                           "label": "Focus time", "rationale": ""})

    blocks.sort(key=lambda b: (DAYS.index(b["day"]), b["start"]))
    return blocks
