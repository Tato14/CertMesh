"""Study Plan Generator.

Converts a certification into a practical, capacity-aware schedule. Grounded by
the Fabric IQ semantic layer (skills, prerequisites, recommended hours, pass
threshold, difficulty ordering) and the Work IQ capacity signal (available focus
hours). Allocates study hours against the learner's available weekly focus
capacity, sequences by difficulty/prerequisites, and sets a role-level capstone.

Reasoning pattern: constraint-satisfaction planning — never schedule more weekly
hours than the learner's available focus time; extend the horizon instead.
"""

from __future__ import annotations

import math

from ..schemas import CapacityCheck, Milestone, StudyPlan
from .base import AgentContext, AgentOutput

NAME = "Study Plan Generator"
WEEKLY_STUDY_CAP = 8.0          # humane sustainable weekly ceiling
CAPSTONE_FRACTION = 0.15        # reserve for a final mock-exam milestone


class StudyPlanAgent:
    name = NAME

    def run(self, ctx: AgentContext) -> AgentOutput:
        cert = ctx.cert_code
        assert cert, "Study plan requires a resolved certification."
        skills = ctx.fabric.skills_for(cert)
        recommended = ctx.fabric.recommended_hours(cert)
        threshold = ctx.fabric.pass_threshold(cert)
        prereq_chain = ctx.fabric.prerequisite_chain(cert)

        # Capacity: explicit override > Work IQ focus hours.
        if ctx.available_hours_per_week is not None:
            available_focus = float(ctx.available_hours_per_week)
        else:
            available_focus = ctx.work.available_focus_hours(ctx.employee_id)
        available_focus = max(0.5, available_focus)
        weekly_study = min(available_focus, WEEKLY_STUDY_CAP)

        # Allocate hours: most to skills, a slice to the capstone mock exam.
        skill_pool = round(recommended * (1 - CAPSTONE_FRACTION), 1)
        capstone_hours = round(recommended - skill_pool, 1)

        # Adaptive re-planning: weak skills flagged by exam feedback are
        # front-loaded and get a 1.5× share of the SAME pool (totals conserved,
        # so the capacity check is unaffected). Empty focus list = original plan.
        focus = list(dict.fromkeys(s for s in (ctx.focus_skills or []) if s in skills))
        ordered_skills = focus + [s for s in skills if s not in focus] if focus else skills
        if focus:
            unit = skill_pool / (len(skills) + 0.5 * len(focus))
            hours_for = {s: round(unit * (1.5 if s in focus else 1.0), 1) for s in skills}
        else:
            per = round(skill_pool / max(len(skills), 1), 1)
            hours_for = {s: per for s in skills}

        milestones: list[Milestone] = []
        citations: list = []
        source_texts: list[str] = []
        running = 0.0
        order = 0
        for skill in ordered_skills:
            order += 1
            hours = hours_for[skill]
            mid_point = running + hours / 2
            week = max(1, math.ceil(mid_point / weekly_study))
            res = ctx.foundry.retrieve(skill, certification=cert, top_k=1)
            cite = res.chunks[0].to_citation() if res.chunks else None
            if cite:
                citations.append(cite)
                source_texts.append(res.chunks[0].text)
            milestones.append(Milestone(
                order=order, week=week, skill=skill,
                title=(f"Priority review: {skill} (exam feedback)" if skill in focus
                       else f"Study: {skill}"),
                hours=hours,
                difficulty=ctx.fabric.skill_difficulty(cert, skill),
                prerequisites=prereq_chain if order == 1 else [],
                citation=cite,
            ))
            running += hours

        total_weeks = max(1, math.ceil(recommended / weekly_study))
        order += 1
        milestones.append(Milestone(
            order=order, week=total_weeks, skill="readiness",
            title=f"Capstone: full mock exam for {cert} (pass threshold {int(threshold * 100)}%)",
            hours=capstone_hours, difficulty="advanced",
        ))

        available_total = round(weekly_study * total_weeks, 1)
        utilisation = round(recommended / available_total, 2) if available_total else 1.0
        constrained = available_focus < 6.0
        fits = weekly_study <= available_focus + 1e-9 and recommended <= available_total + 1e-9
        note_parts = [
            f"{weekly_study:.1f}h/week within {available_focus:.1f}h available focus time."
        ]
        if constrained:
            note_parts.append(
                f"Limited focus capacity — plan spread across {total_weeks} weeks rather than packed into fewer."
            )
        if prereq_chain:
            note_parts.append(f"Prerequisites sequenced first: {', '.join(prereq_chain)}.")
        if focus:
            note_parts.append(
                f"Re-prioritised from exam feedback: {', '.join(focus)} front-loaded "
                "with extra hours (same total).")

        capacity = CapacityCheck(
            available_hours_per_week=round(available_focus, 1),
            weeks=total_weeks,
            available_total_hours=available_total,
            allocated_total_hours=recommended,
            recommended_total_hours=recommended,
            utilisation=utilisation,
            fits=fits,
            note=" ".join(note_parts),
        )
        plan = StudyPlan(
            certification=cert, role=ctx.role, milestones=milestones,
            capacity=capacity, total_weeks=total_weeks, pass_threshold=threshold,
            citations=citations,
        )
        summary = (
            f"{total_weeks}-week plan, {weekly_study:.1f}h/week across {len(skills)} skill areas "
            f"plus a capstone mock exam; capacity {'fits' if fits else 'does NOT fit'} "
            f"available focus time."
            + (f" {len(focus)} weak skill(s) front-loaded from exam feedback." if focus else "")
        )
        return AgentOutput(output=plan, summary=summary, sources=citations,
                           source_texts=source_texts)
