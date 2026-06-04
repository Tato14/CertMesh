"""Learning Path Curator.

Maps a certification target to role-relevant skills and **cited** resources.
Grounded by Foundry IQ (approved synthetic corpus) *and* the Microsoft Learn MCP
server (real Learn content). Never returns unsupported free text: the prose
summary states a meta lead-in plus a single verbatim, quoted source snippet, and
every resource carries a citation the critic can verify.

Reasoning pattern: tool-augmented retrieval + decomposition (cert → skills →
per-skill grounded resource), with a self-reflection loop driven by the critic
(``draft(iteration, feedback)``).
"""

from __future__ import annotations

import re

from ..i18n import t
from ..schemas import CuratedPath, Resource
from .base import AgentContext, AgentOutput

_MODULE_RE = re.compile(r"Approved resource:\s*(.+?)\s*$")
NAME = "Learning Path Curator"


class CuratorAgent:
    name = NAME

    def draft(self, ctx: AgentContext, iteration: int = 0,
              feedback: list[str] | None = None) -> AgentOutput:
        cert = ctx.cert_code
        assert cert, "Curator requires a resolved certification (orchestrator guards this)."
        skills = ctx.fabric.skills_for(cert)
        recommended = ctx.fabric.recommended_hours(cert)
        per_skill_hours = round(recommended / max(len(skills), 1), 1)

        resources: list[Resource] = []
        sources: list = []
        source_texts: list[str] = []
        citations: list = []

        # 1) decompose cert → skills, retrieve a grounded resource per skill.
        for skill in skills:
            res = ctx.foundry.retrieve(skill, certification=cert, top_k=2)
            chunk = next((c for c in res.chunks if "approved resources" in c.locator.lower()), None)
            chunk = chunk or (res.chunks[0] if res.chunks else None)
            if chunk is None:
                continue
            m = _MODULE_RE.search(chunk.text)
            title = m.group(1) if m else f"{skill} — approved module"
            cite = chunk.to_citation(snippet=chunk.text)
            resources.append(Resource(title=title, kind="module", skill=skill,
                                      est_hours=per_skill_hours, citation=cite))
            sources.append(cite)
            citations.append(cite)
            source_texts.append(chunk.text)

        # 2) Microsoft Learn MCP — real, cited Learn content (empty for internal certs).
        learn = ctx.ms_learn.search(cert, certification=cert, top_k=1)
        for c in learn.chunks:
            cite = c.to_citation(snippet=c.text)
            resources.append(Resource(title=c.title, kind="learning_path",
                                      skill="exam overview", est_hours=0.0, citation=cite))
            sources.append(cite)
            citations.append(cite)
            source_texts.append(c.text)

        # 3) grounded summary: meta lead-in + one verbatim quoted overview snippet.
        overview = ctx.foundry.retrieve(f"{cert} validates recommended preparation",
                                         certification=cert, top_k=1)
        quoted_claims: list[str] = []
        meta = t("summary.path", ctx.language, cert=cert, role=ctx.role)
        if overview.chunks:
            ov = overview.chunks[0]
            snippet = ov.text
            cite = ov.to_citation(snippet=snippet)
            citations.append(cite)
            source_texts.append(ov.text)
            quoted_claims.append(snippet)
            summary = f'{meta} "{snippet}"'
        else:
            summary = meta

        path = CuratedPath(
            certification=cert, role=ctx.role, skills=skills,
            resources=resources, summary=summary, citations=citations,
        )
        return AgentOutput(
            output=path, summary=summary, sources=sources,
            source_texts=source_texts, quoted_claims=quoted_claims,
            reflections=iteration,
            abstained=not resources,
        )
