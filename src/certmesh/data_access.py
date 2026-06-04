"""Loader for the synthetic learner roster.

Learner records are the only place individual-level data lives. The Manager
Insights agent reads them *through aggregation only* (see agents/manager_insights.py);
learner-facing flows read a single record by id. All records are synthetic.
"""

from __future__ import annotations

import json
from functools import lru_cache

from .config import Config, load_config
from .schemas import Learner


class LearnerStore:
    def __init__(self, config: Config | None = None):
        self.config = config or load_config()
        self._by_id = self._load()

    def _load(self) -> dict[str, Learner]:
        path = self.config.data_dir / "learners.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        out: dict[str, Learner] = {}
        for rec in data.get("records", []):
            learner = Learner(**rec)
            out[learner.learner_id] = learner
        return out

    def get(self, learner_id: str | None) -> Learner | None:
        return self._by_id.get(learner_id) if learner_id else None

    def all(self) -> list[Learner]:
        return list(self._by_id.values())

    def employee_id(self, learner_id: str | None) -> str | None:
        rec = self.get(learner_id)
        return rec.employee_id if rec and rec.employee_id else None

    def by_team(self, team: str | None = None) -> list[Learner]:
        if not team:
            return self.all()
        return [r for r in self._by_id.values() if r.team == team]

    def teams(self) -> list[str]:
        return sorted({r.team for r in self._by_id.values()})


@lru_cache(maxsize=1)
def get_learner_store() -> LearnerStore:
    return LearnerStore()


def employee_id_for(learner_id: str | None) -> str | None:
    return get_learner_store().employee_id(learner_id)
