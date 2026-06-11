"""Fabric IQ — concept-faithful semantic layer over the synthetic certification
ontology (data/fabric_seed.json).

Microsoft's Fabric IQ exposes a governed semantic model (entities + relationships
+ measures) over enterprise data. Here we model the same idea for certifications:

* **entities** — certification, skill, role, track
* **relationships** — prerequisite_of, required_for_role, covers_skill
* **measures** — recommended_hours, pass_threshold, skill-gap

Agents query this layer for the *meaning* of a request (what skills a cert needs,
what its prerequisites and threshold are, which certs a role requires) rather than
hard-coding it. The upgrade path to a real Fabric semantic model / OneLake source
is documented in docs/iq-layers.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from ..config import Config, load_config
from ..schemas import Difficulty


@dataclass
class CertInfo:
    code: str
    title: str
    track: str
    real_exam: bool
    recommended_hours: float
    pass_threshold: float
    prerequisites: list[str]
    skills: list[str]


class FabricIQ:
    def __init__(self, config: Config | None = None):
        self.config = config or load_config()
        self._certs, self._roles = self._load()
        self._title_index = {v.title.lower(): k for k, v in self._certs.items()}

    def _load(self):
        path = self.config.data_dir / "fabric_seed.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        certs: dict[str, CertInfo] = {}
        for code, c in data.get("certifications", {}).items():
            certs[code] = CertInfo(
                code=code,
                title=c["title"],
                track=c.get("track", "technical"),
                real_exam=c.get("real_exam", False),
                recommended_hours=float(c.get("recommended_hours", 30)),
                pass_threshold=float(c.get("pass_threshold", 0.7)),
                prerequisites=list(c.get("prerequisites", [])),
                skills=list(c.get("skills", [])),
            )
        roles = data.get("roles", {})
        return certs, roles

    # -- normalisation -------------------------------------------------------
    def resolve_cert(self, value: str | None) -> str | None:
        """Map a code or a title (any case) to a canonical cert code."""
        if not value:
            return None
        v = value.strip()
        if v.upper() in self._certs:
            return v.upper()
        low = v.lower()
        if low in self._title_index:
            return self._title_index[low]
        # loose contains match on title or code mention in free text
        for code, info in self._certs.items():
            if code.lower() in low or info.title.lower() in low:
                return code
        return None

    def resolve_role(self, value: str | None) -> str | None:
        if not value:
            return None
        v = value.strip().lower()
        for name in self._roles:
            if name.lower() == v:
                return name
        for name in self._roles:
            if name.lower() in v or v in name.lower():
                return name
        return None

    # -- entity queries ------------------------------------------------------
    def is_known_cert(self, code: str | None) -> bool:
        return self.resolve_cert(code) is not None

    def cert(self, code: str) -> CertInfo | None:
        resolved = self.resolve_cert(code)
        return self._certs.get(resolved) if resolved else None

    def skills_for(self, code: str) -> list[str]:
        info = self.cert(code)
        return list(info.skills) if info else []

    def recommended_hours(self, code: str) -> float:
        info = self.cert(code)
        return info.recommended_hours if info else 30.0

    def pass_threshold(self, code: str) -> float:
        info = self.cert(code)
        return info.pass_threshold if info else 0.7

    def track_for(self, code: str) -> str:
        info = self.cert(code)
        return info.track if info else "technical"

    # -- relationship queries ------------------------------------------------
    def prerequisites(self, code: str) -> list[str]:
        info = self.cert(code)
        return list(info.prerequisites) if info else []

    def prerequisite_chain(self, code: str) -> list[str]:
        """Full, de-duplicated prerequisite chain in dependency order."""
        chain: list[str] = []
        seen: set[str] = set()

        def visit(c: str) -> None:
            for pre in self.prerequisites(c):
                if pre not in seen:
                    seen.add(pre)
                    visit(pre)
                    chain.append(pre)

        visit(self.resolve_cert(code) or code)
        return chain

    def required_certs(self, role: str) -> list[str]:
        name = self.resolve_role(role)
        if not name:
            return []
        return list(self._roles[name].get("required_certs", []))

    def role_for_cert(self, code: str) -> str | None:
        """A role whose required certs include this cert (for role-alignment)."""
        resolved = self.resolve_cert(code)
        for name, info in self._roles.items():
            if resolved in info.get("required_certs", []):
                return name
        return None

    def next_certification(self, role: str, current: str) -> str | None:
        """Recommend the next required cert for a role after passing ``current``."""
        required = self.required_certs(role)
        cur = self.resolve_cert(current)
        for code in required:
            if code != cur and cur in self.prerequisite_chain(code):
                return code
        for code in required:
            if code != cur:
                return code
        return None

    # -- measures ------------------------------------------------------------
    def skill_difficulty(self, code: str, skill: str) -> Difficulty:
        """Semantic measure: order skills foundational→advanced by position."""
        skills = self.skills_for(code)
        if skill not in skills or len(skills) < 2:
            return "intermediate"
        pos = skills.index(skill) / (len(skills) - 1)
        if pos < 0.34:
            return "foundational"
        if pos < 0.67:
            return "intermediate"
        return "advanced"

    def skill_gap(self, practice_score: float, code: str) -> float:
        """Semantic measure: estimated gap to the cert's pass threshold (0..1)."""
        gap = self.pass_threshold(code) - practice_score
        return round(max(0.0, gap), 3)

    def role_track(self, role: str) -> str:
        """The role's declared track from the seed ontology (deterministic), with
        a majority-of-required-certs fallback for roles that omit it."""
        name = self.resolve_role(role)
        if not name:
            return "technical"
        declared = self._roles[name].get("track")
        if declared:
            return declared
        tracks = [self.track_for(c) for c in self._roles[name].get("required_certs", [])]
        return max(sorted(set(tracks)), key=tracks.count) if tracks else "technical"

    def known_roles(self) -> list[str]:
        return list(self._roles)

    def known_certs(self) -> list[str]:
        return list(self._certs)


@lru_cache(maxsize=1)
def get_fabric_iq() -> FabricIQ:
    return FabricIQ()
