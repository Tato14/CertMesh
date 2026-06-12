// Learner results: staggered cards in agent order (curator → plan → engagement
// → assessment), designed abstain state, compact calendar embed, progress card.

import { api } from "./api.js";
import { store } from "./state.js";
import { individualCard } from "./progress.js";
import {
  $, badge, citeCollector, emptyState, errorState, esc, pct, skeletonCard, sourcesCard,
} from "./util.js";

const AGENT_CARD = {
  "Learning Path Curator": "card-curator",
  "Study Plan Generator": "card-plan",
  "Engagement Agent": "card-engagement",
  "Assessment Agent": "card-assessment",
};

let cites = null;
let renderGen = 0;   // bumped on every re-render; stale what-if callbacks bail

export function init() {
  renderGen++;
  $("learner-results").innerHTML = emptyState("◎", "Ready when you are",
    "Pick a scenario above or describe a goal — the orchestrator plans, five specialists execute, and the critic verifies every claim.");
}

export function showLoading() {
  renderGen++;
  $("learner-results").innerHTML = [
    skeletonCard("① Learning Path Curator", 3),
    skeletonCard("② Study Plan Generator", 4),
    skeletonCard("③ Engagement Agent — Work IQ", 2),
    skeletonCard("④ Assessment Agent", 3),
  ].join("");
}

export function showError(msg) {
  $("learner-results").innerHTML = errorState(msg);
}

/* Build all cards hidden; the trace replay reveals them in agent order. */
export function render(result) {
  renderGen++;
  cites = citeCollector();
  const out = $("learner-results");

  if (result.abstained && result.plan.agents_to_run.length === 0) {
    out.innerHTML = abstainCard(result);
    wireAbstain(out);
    return;
  }

  const html = [];
  if (result.curated_path) html.push(curatorCard(result.curated_path));
  if (result.study_plan) html.push(planCard(result.study_plan, result.request));
  if (result.study_plan) html.push(whatifCard(result));
  if (result.engagement_plan) html.push(engagementCard(result, result.engagement_plan));
  if (result.assessment) html.push(assessmentCard(result.assessment));
  if (result.abstained) {
    html.push(`<div class="abstain-state" data-reveal="end">
      <div class="head">⚠ Human review recommended</div>
      <div class="dim">${esc(result.messages.join(" ") || "A specialist abstained after the reflection budget was spent; output withheld rather than risk an ungrounded answer.")}</div>
    </div>`);
  }
  html.push(`<div data-reveal="end" id="learner-progress-slot"></div>`);
  html.push(`<div data-reveal="end" id="learner-sources-slot"></div>`);
  out.innerHTML = html.join("");
  out.querySelectorAll("[data-reveal]").forEach((el) => { el.style.display = "none"; });

  out.querySelector("#open-exam")?.addEventListener("click", () => store.emit("open-quiz", "exam"));
  out.querySelector("#open-review")?.addEventListener("click", () => store.emit("open-quiz", "review"));
}

/* Called by the run flow as each agent settles in the trace replay. */
export function reveal(agent) {
  const id = AGENT_CARD[agent];
  if (!id) return;
  const el = document.getElementById(id);
  if (el) { el.style.display = ""; el.classList.add("fade-up"); }
  if (agent === "Engagement Agent") hydrateMiniWeek();
}

/* After the replay finishes: sources, progress, anything not yet shown. */
export async function finish(result) {
  document.querySelectorAll("#learner-results [data-reveal]").forEach((el) => {
    el.style.display = ""; el.classList.add("fade-up");
  });
  hydrateMiniWeek();
  wireWhatif(result);
  const srcSlot = $("learner-sources-slot");
  if (srcSlot && cites) srcSlot.innerHTML = sourcesCard(cites.list());

  const progSlot = $("learner-progress-slot");
  const lid = result.request.learner_id;
  if (progSlot && lid) {
    try {
      const data = await api.progress(lid);
      progSlot.innerHTML = `<div class="card fade-up">
        <div class="card-title spread"><span>Progress &amp; feedback <span class="pill mono">${esc(lid)}</span></span>
          <span class="pill">synthetic history</span></div>
        ${individualCard(data)}</div>`;
    } catch { progSlot.innerHTML = ""; }
  }
}

/* ── cards ──────────────────────────────────────────────────────────────── */

function curatorCard(p) {
  const resources = p.resources.map((r) => `
    <div class="resource">
      <div class="top"><b>${esc(r.title)}</b>
        <span class="pill">${esc(r.skill)}</span>${r.est_hours ? `<span class="pill mono">${r.est_hours}h</span>` : ""}</div>
      <div>${cites.chip(r.citation)}</div>
    </div>`).join("");
  return `<div class="card" id="card-curator" data-reveal>
    <div class="card-title"><span class="step-no">1</span> Learning Path Curator
      <span class="pill">Foundry IQ + Learn MCP</span></div>
    <p class="dim">${esc(p.summary)}</p>
    <div class="wrap" style="margin-bottom:8px">
      <span class="pill">${p.skills.length} skills</span>
      <span class="pill">${p.resources.length} cited resources</span>
    </div>
    ${resources}</div>`;
}

function planCard(s, request) {
  const c = s.capacity;
  // banner driven by what the agent ACTUALLY front-loaded, not the raw request
  const focus = s.milestones.filter((m) => m.title.startsWith("Priority review")).map((m) => m.skill);
  const rows = s.milestones.map((m) => `<tr class="${m.title.startsWith("Priority review") ? "prio" : ""}">
      <td class="mono">W${m.week}</td><td>${esc(m.title)}</td>
      <td class="mono">${m.hours}h</td><td><span class="pill">${esc(m.difficulty)}</span></td>
      <td>${m.citation ? cites.chip(m.citation) : ""}</td></tr>`).join("");
  const replanBanner = focus.length ? `
    <div class="replan-banner">↻ <b>Re-planned from your exam mistakes.</b>
      ${focus.map((f) => `<span class="pill">${esc(f)}</span>`).join(" ")}
      front-loaded with extra hours — same total, redistributed.</div>` : "";
  return `<div class="card" id="card-plan" data-reveal>
    <div class="card-title"><span class="step-no">2</span> Study Plan Generator
      <span class="pill">Fabric IQ + Work IQ</span></div>
    ${replanBanner}
    <div class="kpis" style="margin-bottom:10px">
      <div class="kpi"><div class="k">weeks</div><div class="v">${s.total_weeks}</div></div>
      <div class="kpi"><div class="k">focus h/week</div><div class="v">${c.available_hours_per_week}</div></div>
      <div class="kpi"><div class="k">utilisation</div><div class="v">${pct(c.utilisation)}</div></div>
      <div class="kpi"><div class="k">capacity</div><div class="v">${badge(c.fits ? "fit" : "nofit", c.fits ? "fits" : "over")}</div></div>
    </div>
    <p class="muted small">${esc(c.note)}</p>
    <table><thead><tr><th>Wk</th><th>Milestone</th><th>Hrs</th><th>Level</th><th>Source</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

function engagementCard(result, e) {
  const windows = e.weekly_windows.map((w) =>
    `<span class="pill" title="${esc(w.rationale)}"><span class="mono">${esc(w.day)}</span> ${esc(w.slot)}</span>`).join(" ");
  return `<div class="card" id="card-engagement" data-reveal>
    <div class="card-title spread"><span><span class="step-no">3</span> Engagement Agent
      <span class="pill">Work IQ rhythm</span></span>
      <button class="btn-ghost btn-sm" data-goto-calendar>Open calendar →</button></div>
    <div><b>${esc(e.cadence)}</b></div>
    <div class="windows">${windows}</div>
    <div class="dim">${esc(e.next_reminder)}</div>
    <div id="mini-week-slot" data-learner="${esc(result.request.learner_id || "")}"></div>
    <p class="muted small" style="margin:8px 0 0">${esc(e.capacity_note)} · ${esc(e.privacy_note)}</p>
  </div>`;
}

function assessmentCard(a) {
  return `<div class="card" id="card-assessment" data-reveal>
    <div class="card-title"><span class="step-no">4</span> Assessment Agent
      <span class="pill">grounded questions</span></div>
    <div class="wrap" style="align-items:center">
      ${badge(a.readiness)}
      <span class="pill mono">est ${pct(a.estimated_score)} vs ${pct(a.threshold)} threshold</span>
      <span class="pill">${a.questions.length} questions</span>
    </div>
    <p class="dim" style="margin:10px 0 4px">${esc(a.rationale)}</p>
    <p class="muted small"><b>Next:</b> ${esc(a.next_recommendation)}</p>
    <div style="display:flex;gap:8px;margin-top:10px">
      <button class="btn-primary" id="open-exam">Take it as an exam →</button>
      <button class="btn-secondary" id="open-review">Review all questions</button>
    </div></div>`;
}

/* What-if (Feature: counterfactual re-planning). Dragging the slider re-runs
   the SAME request with a different weekly capacity — live constraint
   propagation through Study Plan → Engagement — and diffs the outcome. */
function whatifCard(result) {
  const cur = result.study_plan.capacity.available_hours_per_week;
  return `<div class="card" id="whatif-card" data-reveal>
    <div class="card-title spread">
      <span>What if? <span class="pill">live constraint propagation</span></span>
      <span class="pill mono" id="whatif-value">${cur}h focus/week</span>
    </div>
    <input type="range" id="whatif-slider" min="1" max="14" step="0.5" value="${cur}"
      aria-label="What-if weekly focus hours" style="width:100%">
    <div id="whatif-diff" class="muted small" style="margin-top:8px">
      Drag to re-solve the plan under a different weekly capacity — the agents
      re-run live with the override.</div>
  </div>`;
}

function wireWhatif(baseline) {
  const slider = document.getElementById("whatif-slider");
  if (!slider) return;
  const myGen = renderGen;                            // this run's generation
  let timer = null;
  let seq = 0;
  // stale = the results pane was re-rendered (new run, Clear, …) since wiring
  const stale = () => myGen !== renderGen || !slider.isConnected;
  slider.addEventListener("input", () => {
    if (stale()) return;
    document.getElementById("whatif-value").textContent = `${slider.value}h focus/week`;
    clearTimeout(timer);
    timer = setTimeout(async () => {
      if (stale()) return;
      const v = parseFloat(slider.value);
      const mySeq = ++seq;
      const box = document.getElementById("whatif-diff");
      if (!box) return;
      box.innerHTML = `<span class="pulse">Re-running Study Plan + Engagement with ${v}h/week…</span>`;
      try {
        const alt = await api.run({ ...baseline.request, available_hours_per_week: v });
        if (mySeq !== seq || stale()) return;         // a newer drag or run won
        const box2 = document.getElementById("whatif-diff");
        if (!box2) return;
        box2.innerHTML = whatifDiff(baseline, alt, v);
        document.getElementById("whatif-apply")?.addEventListener("click", () =>
          store.emit("run-request", { ...baseline.request, available_hours_per_week: v }));
      } catch (e) {
        if (mySeq === seq && !stale()) {
          const box2 = document.getElementById("whatif-diff");
          if (box2) box2.innerHTML = `<span class="muted">What-if failed: ${esc(e.message)}</span>`;
        }
      }
    }, 350);
  });
}

function whatifDiff(base, alt, v) {
  const b = base.study_plan, a = alt.study_plan;
  const arrow = (x, y, unit = "") => x === y
    ? `<b>${y}${unit}</b> <span class="muted">(unchanged)</span>`
    : `<s class="muted">${x}${unit}</s> → <b style="color:${y < x ? "var(--good)" : "var(--warn)"}">${y}${unit}</b>`;
  const bw = base.engagement_plan?.weekly_windows || [];
  const aw = alt.engagement_plan?.weekly_windows || [];
  return `
    <div class="wrap" style="gap:16px;align-items:center">
      <span>weeks to ready: ${arrow(b.total_weeks, a.total_weeks)}</span>
      <span>utilisation: ${arrow(Math.round(b.capacity.utilisation * 100), Math.round(a.capacity.utilisation * 100), "%")}</span>
      <span>sessions/week: ${arrow(bw.length, aw.length)}</span>
      <span>capacity: ${a.capacity.fits ? badge("fit", "fits") : badge("nofit", "over")}</span>
      <button class="btn-secondary btn-sm" id="whatif-apply">Apply scenario →</button>
    </div>
    <div class="muted small" style="margin-top:6px">${esc(a.capacity.note)}</div>`;
}

function abstainCard(result) {
  return `<div class="abstain-state fade-up">
      <div class="head">🛡 Grounded abstain — a safety feature</div>
      <p class="dim">${esc(result.messages.join(" "))}</p>
      <p class="muted small">Confidence ${Math.round(result.confidence * 100)}% — rather than fabricate an
        answer outside the approved knowledge base, the planner stopped and flagged this for human review.
        That behaviour is CI-gated (abstention correctness == 1.0).</p>
      <div class="wrap" id="abstain-suggestions"><span class="muted small">Try a supported certification:</span></div>
    </div>`;
}

async function wireAbstain(out) {
  try {
    const g = store.graphData || (store.graphData = await api.graph());
    const box = out.querySelector("#abstain-suggestions");
    g.elements.nodes.filter((n) => n.data.type === "certification").slice(0, 6).forEach((n) => {
      const b = document.createElement("button");
      b.className = "btn-secondary btn-sm mono";
      b.textContent = n.data.label;
      b.addEventListener("click", () =>
        store.emit("run-request", { view: "learner", goal: `Help me prepare for ${n.data.label}` }));
      box.appendChild(b);
    });
  } catch { /* suggestions are optional */ }
  out.querySelector("[data-goto-calendar]")?.addEventListener("click", () => store.emit("switch-tab", "calendar"));
}

/* Compact week strip inside the engagement card, fed by /api/calendar. */
async function hydrateMiniWeek() {
  const slot = document.getElementById("mini-week-slot");
  if (!slot || slot.dataset.done) return;
  slot.dataset.done = "1";
  document.querySelector("[data-goto-calendar]")?.addEventListener("click", () => {
    store.emit("switch-tab", "calendar");
    if (slot.dataset.learner) store.emit("calendar-show", slot.dataset.learner);
  });
  const lid = slot.dataset.learner;
  if (!lid) { slot.innerHTML = `<p class="muted small" style="margin:8px 0 0">Add a learner id to see the simulated capacity week.</p>`; return; }
  try {
    const cal = await api.calendar(lid);
    const days = cal.days.map((d) => {
      const blocks = cal.blocks.filter((b) => b.day === d).slice(0, 5).map((b) =>
        `<div class="blk ${esc(b.kind)}" title="${esc(b.label)}${b.rationale ? " — " + esc(b.rationale) : ""}">${b.kind === "study" ? "★ " : ""}${esc(b.start)}</div>`).join("");
      return `<div class="mini-day"><div class="d">${esc(d)}</div>${blocks}</div>`;
    }).join("");
    slot.innerHTML = `<div class="mini-week">${days}</div>
      <p class="muted small" style="margin:6px 0 0">★ proposed study slots inside focus time — simulated week, synthetic signals.</p>`;
  } catch { slot.innerHTML = ""; }
}
