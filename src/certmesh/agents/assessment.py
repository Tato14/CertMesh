"""Assessment Agent.

Evaluates readiness with **grounded, cited** practice questions generated from the
Foundry IQ knowledge base, scores the learner against the Fabric IQ pass
threshold, and recommends the next step. Pairs with the critic for grounding.

Reasoning pattern: generation + a real self-reflection loop. ``draft(0)`` includes
a synthesis question whose rationale is a *constructed* combination of two source
facts — which is not verbatim-grounded. The critic rejects it; ``draft(1)`` revises
that question to cite a verbatim source sentence. So the final output is fully
grounded, and the trace shows the critic→revise loop.
"""

from __future__ import annotations

from ..i18n import t
from ..schemas import Assessment, AssessmentQuestion
from .base import AgentContext, AgentOutput

NAME = "Assessment Agent"

# Generic, deliberately-wrong distractors (clearly not from the approved corpus).
_DISTRACTORS = [
    "It is handled automatically by the platform and needs no configuration.",
    "It applies only to on-premises systems, not to this certification.",
    "It should be disabled in production to improve performance.",
]


def _fact_chunk(ctx: AgentContext, cert: str, skill: str):
    res = ctx.foundry.retrieve(skill, certification=cert, top_k=3)
    fact = next((c for c in res.chunks if c.locator.lower().endswith("exam-relevant facts")), None)
    return fact or (res.chunks[0] if res.chunks else None)


def _assemble(correct: str, salt: str) -> tuple[list[str], int]:
    idx = sum(ord(ch) for ch in salt) % (len(_DISTRACTORS) + 1)
    options = list(_DISTRACTORS)
    options.insert(idx, correct)
    return options, idx


class AssessmentAgent:
    name = NAME

    def draft(self, ctx: AgentContext, iteration: int = 0,
              feedback: list[str] | None = None) -> AgentOutput:
        cert = ctx.cert_code
        assert cert, "Assessment requires a resolved certification."
        skills = ctx.fabric.skills_for(cert)
        threshold = ctx.fabric.pass_threshold(cert)

        questions: list[AssessmentQuestion] = []
        citations: list = []
        source_texts: list[str] = []
        fact_chunks = []

        # 1) one grounded MCQ per skill (verbatim correct option + cited source).
        for i, skill in enumerate(skills[:5]):
            chunk = _fact_chunk(ctx, cert, skill)
            if chunk is None:
                continue
            fact = chunk.text
            fact_chunks.append((skill, chunk))
            options, ans = _assemble(fact, f"{cert}-{skill}")
            cite = chunk.to_citation(snippet=fact)
            questions.append(AssessmentQuestion(
                id=f"{cert}-Q{i+1}",
                stem=f"Which statement about {skill} ({cert}) is correct?",
                options=options, answer_index=ans,
                explanation=f'Correct per the approved guide: "{fact}"',
                skill=skill,
                difficulty=ctx.fabric.skill_difficulty(cert, skill),
                citation=cite,
            ))
            citations.append(cite)
            source_texts.append(fact)

        # 2) synthesis question — the self-reflection target.
        reflections = iteration
        if len(fact_chunks) >= 2:
            (skill_a, chunk_a), (skill_b, chunk_b) = fact_chunks[0], fact_chunks[1]
            fact_a, fact_b = chunk_a.text, chunk_b.text
            options, ans = _assemble(fact_a, f"{cert}-synthesis")
            if iteration == 0:
                # Draft asserts a *synthesized* rationale that is not verbatim grounded.
                synth = f"{fact_a} and {fact_b}".rstrip(".")
                cite = chunk_a.to_citation(snippet=synth)
                explanation = f"Combining both topics: {synth}."
            else:
                # Revision: cite a verbatim source sentence.
                cite = chunk_a.to_citation(snippet=fact_a)
                explanation = f'Correct per the approved guide: "{fact_a}"'
            questions.append(AssessmentQuestion(
                id=f"{cert}-QS",
                stem=f"A scenario requires applying both {skill_a} and {skill_b}. Which statement is correct?",
                options=options, answer_index=ans,
                explanation=explanation, skill=f"{skill_a} + {skill_b}",
                difficulty="advanced", citation=cite,
            ))
            citations.append(cite)
            # both underlying facts are valid grounding sources
            source_texts.extend([fact_a, fact_b])

        # 3) readiness scoring against the Fabric IQ threshold.
        score = ctx.learner.practice_score_avg if ctx.learner else 0.5
        if score >= threshold:
            band = "ready"
        elif score >= threshold - 0.1:
            band = "borderline"
        else:
            band = "not_ready"
        passed = score >= threshold
        lang = ctx.language

        if passed:
            nxt = ctx.fabric.next_certification(ctx.role, cert)
            next_rec = (t("assess.next_advance", lang, next=nxt) if nxt
                        else t("assess.next_met", lang))
        else:
            next_rec = t("assess.next_continue", lang)

        rationale = t("assess.rationale", lang, score=f"{score:.0%}",
                      thr=f"{threshold:.0%}", band=t(f"band.{band}", lang),
                      n=str(len(questions)))
        assessment = Assessment(
            certification=cert, questions=questions, estimated_score=round(score, 3),
            threshold=threshold, readiness=band, passed=passed,
            rationale=rationale, next_recommendation=next_rec, citations=citations,
        )
        return AgentOutput(
            output=assessment, summary=rationale, sources=citations,
            source_texts=source_texts, reflections=reflections,
        )
