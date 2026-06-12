// Interactive assessment (Feature C): exam mode — one question at a time, no
// reveal until submit — then per-question feedback with citation chips and an
// animated score gauge against the certification's Fabric IQ pass threshold.
// Pass → next-certification recommendation; fail → straight back into the
// preparation loop (re-runs planning). A review-all view keeps fast judging.

import { store } from "./state.js";
import { $, badge, citeCollector, emptyState, esc, pct, reducedMotion } from "./util.js";

let assessment = null;
let lastRequest = null;
let answers = [];
let idx = 0;

export function init() {
  renderEmpty();
}

export function setAssessment(result) {
  assessment = result.assessment || null;
  lastRequest = result.request;
  answers = assessment ? new Array(assessment.questions.length).fill(null) : [];
  idx = 0;
  $("quiz-cert-pill").innerHTML = assessment
    ? `<span class="pill mono">${esc(assessment.certification)} · pass ≥ ${pct(assessment.threshold)}</span>` : "";
  if (assessment) renderIntro();
  else renderEmpty();
}

export function open(mode) {
  if (!assessment) { renderEmpty(); return; }
  if (mode === "review") renderReview();
  else renderIntro();
}

function renderEmpty() {
  $("quiz-root").innerHTML = emptyState("✓", "No assessment yet",
    "Run a learner scenario first — the Assessment Agent generates grounded, cited practice questions for the resolved certification.",
    `<button class="btn-primary" id="quiz-run-default">Run the AZ-204 scenario</button>`);
  $("quiz-run-default")?.addEventListener("click", () =>
    store.emit("run-request", { view: "learner", goal: "Help me prepare for AZ-204", role: "Cloud Platform Engineer" }));
}

function renderIntro() {
  const a = assessment;
  $("quiz-root").innerHTML = `
    <div class="gauge-wrap" style="margin-bottom:16px">
      <div>
        <h3>${esc(a.certification)} practice exam</h3>
        <p class="muted" style="margin:6px 0 0">${a.questions.length} grounded questions ·
          every answer cites the approved corpus · pass threshold ${pct(a.threshold)} (Fabric IQ).</p>
        <p class="muted small">Agent's prior estimate: ${pct(a.estimated_score)} → ${badge(a.readiness)}</p>
      </div>
    </div>
    <div style="display:flex;gap:8px">
      <button class="btn-primary" id="quiz-start">Start exam mode</button>
      <button class="btn-secondary" id="quiz-review">Review all questions</button>
    </div>`;
  $("quiz-start").addEventListener("click", () => { answers.fill(null); idx = 0; renderQuestion(); });
  $("quiz-review").addEventListener("click", renderReview);
}

/* ── exam mode ──────────────────────────────────────────────────────────── */

function renderQuestion() {
  const a = assessment;
  const q = a.questions[idx];
  const answered = answers.filter((x) => x !== null).length;
  $("quiz-root").innerHTML = `
    <div class="quiz-progress">
      <span class="n">${idx + 1}/${a.questions.length}</span>
      <div class="bar"><i style="width:${(answered / a.questions.length) * 100}%"></i></div>
      <span class="pill">${esc(q.skill)}</span><span class="pill">${esc(q.difficulty)}</span>
    </div>
    <div class="q-stem">${esc(q.stem)}</div>
    ${q.options.map((opt, i) => `
      <button class="q-option ${answers[idx] === i ? "selected" : ""}" data-opt="${i}">
        <span class="key">${"ABCD"[i]}</span><span>${esc(opt)}</span></button>`).join("")}
    <div class="spread" style="margin-top:16px">
      <button class="btn-ghost" id="q-prev" ${idx === 0 ? "disabled" : ""}>← Previous</button>
      <span class="muted small">no answers are revealed until you submit</span>
      ${idx < a.questions.length - 1
        ? `<button class="btn-secondary" id="q-next" ${answers[idx] === null ? "disabled" : ""}>Next →</button>`
        : `<button class="btn-primary" id="q-submit" ${answers.includes(null) ? "disabled" : ""}>Submit ${a.questions.length} answers</button>`}
    </div>`;
  document.querySelectorAll(".q-option").forEach((b) =>
    b.addEventListener("click", () => { answers[idx] = Number(b.dataset.opt); renderQuestion(); }));
  $("q-prev")?.addEventListener("click", () => { idx--; renderQuestion(); });
  $("q-next")?.addEventListener("click", () => { idx++; renderQuestion(); });
  $("q-submit")?.addEventListener("click", renderResults);
}

/* ── results + gauge ────────────────────────────────────────────────────── */

function gaugeSvg() {
  // 180° arc, r=78; value arc animated via stroke-dasharray
  return `<div class="gauge">
    <svg viewBox="0 0 190 110">
      <path d="M17 102 A 78 78 0 0 1 173 102" fill="none" stroke="var(--bg3)" stroke-width="13" stroke-linecap="round"></path>
      <path id="gauge-val" d="M17 102 A 78 78 0 0 1 173 102" fill="none" stroke="var(--accent)"
        stroke-width="13" stroke-linecap="round" pathLength="100" stroke-dasharray="0 100"></path>
      <line id="gauge-th" x1="0" y1="0" x2="0" y2="0" stroke="var(--warn)" stroke-width="2.5"></line>
    </svg>
    <div class="val" id="gauge-num">0%</div>
    <div class="lbl" id="gauge-lbl"></div>
  </div>`;
}

function animateGauge(score, threshold) {
  const val = $("gauge-val"), num = $("gauge-num");
  const color = score >= threshold ? "var(--good)" : score >= threshold - 0.1 ? "var(--warn)" : "var(--bad)";
  val.style.stroke = color;
  num.style.color = color;
  $("gauge-lbl").textContent = `pass ≥ ${pct(threshold)}`;
  // threshold tick on the arc
  const ang = Math.PI * (1 - threshold);
  const cx = 95, cy = 102, r1 = 68, r2 = 90;
  const th = $("gauge-th");
  th.setAttribute("x1", cx + r1 * Math.cos(ang)); th.setAttribute("y1", cy - r1 * Math.sin(ang));
  th.setAttribute("x2", cx + r2 * Math.cos(ang)); th.setAttribute("y2", cy - r2 * Math.sin(ang));
  const target = Math.round(score * 100);
  if (reducedMotion()) {
    val.setAttribute("stroke-dasharray", `${target} 100`);
    num.textContent = `${target}%`;
    return;
  }
  const t0 = performance.now(), dur = 900;
  (function tick(t) {
    const f = Math.min((t - t0) / dur, 1);
    const eased = 1 - (1 - f) ** 3;
    val.setAttribute("stroke-dasharray", `${(target * eased).toFixed(1)} 100`);
    num.textContent = `${Math.round(target * eased)}%`;
    if (f < 1) requestAnimationFrame(tick);
  })(t0);
}

function renderResults() {
  const a = assessment;
  const cites = citeCollector();
  const correct = a.questions.filter((q, i) => answers[i] === q.answer_index).length;
  const score = correct / a.questions.length;
  const passed = score >= a.threshold;

  // the skills the learner actually got wrong drive the adaptive re-plan
  // (synthesis questions like "X + Y" contribute both underlying skills)
  const weakSkills = [...new Set(a.questions.flatMap((q, i) =>
    answers[i] === q.answer_index ? [] : q.skill.split(" + ")))];

  const items = a.questions.map((q, i) => {
    const ok = answers[i] === q.answer_index;
    return `<div class="q-review-item">
      <div class="spread"><b>${ok ? "✓" : "✗"} Q${i + 1} · ${esc(q.stem)}</b>
        <span class="pill ${ok ? "" : ""}" style="color:${ok ? "var(--good)" : "var(--bad)"}">${ok ? "correct" : "incorrect"}</span></div>
      ${q.options.map((opt, j) => `
        <div class="q-option btn-sm ${j === q.answer_index ? "correct" : j === answers[i] ? "incorrect" : ""}"
          style="cursor:default;padding:8px 12px;margin:6px 0 0">
          <span class="key">${"ABCD"[j]}</span><span>${esc(opt)}</span></div>`).join("")}
      <div class="q-explain">${esc(q.explanation)}<div style="margin-top:4px">${cites.chip(q.citation)}</div></div>
    </div>`;
  }).join("");

  $("quiz-root").innerHTML = `
    <div class="gauge-wrap">
      ${gaugeSvg()}
      <div style="flex:1;min-width:240px">
        <h3>${correct}/${a.questions.length} correct ${badge(passed ? "ready" : score >= a.threshold - 0.1 ? "borderline" : "not_ready", passed ? "passed" : "below threshold")}</h3>
        <p class="dim" style="margin:8px 0 4px">${esc(a.rationale)}</p>
        <p class="muted small"><b>Agent recommendation:</b> ${esc(a.next_recommendation)}</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
          ${passed
            ? `<button class="btn-secondary" id="quiz-again">Retake</button>`
            : `<button class="btn-primary" id="quiz-replan">↻ Re-plan around my ${weakSkills.length} weak skill${weakSkills.length === 1 ? "" : "s"}</button>
               <button class="btn-ghost" id="quiz-again">Retake</button>`}
        </div>
        ${passed ? "" : `<p class="muted small" style="margin-top:8px">Your mistakes
          (${weakSkills.map(esc).join(", ")}) are fed back to the planner — the new study plan
          front-loads them with extra hours. Watch the plan reasoning in the trace.</p>`}
      </div>
    </div>
    <div style="margin-top:20px">${items}</div>`;
  animateGauge(score, a.threshold);
  $("quiz-again")?.addEventListener("click", () => { answers.fill(null); idx = 0; renderQuestion(); });
  $("quiz-replan")?.addEventListener("click", () =>
    store.emit("run-request", { ...lastRequest, focus_skills: weakSkills }));
}

/* ── review-all (fast judging) ──────────────────────────────────────────── */

function renderReview() {
  const a = assessment;
  const cites = citeCollector();
  $("quiz-root").innerHTML = `
    <div class="spread" style="margin-bottom:10px">
      <p class="muted small" style="margin:0">All ${a.questions.length} questions with answers and citations —
        the same data exam mode uses.</p>
      <button class="btn-secondary btn-sm" id="quiz-to-exam">Take it as an exam →</button>
    </div>
    ${a.questions.map((q, i) => `
      <div class="q-review-item">
        <div class="spread"><b>Q${i + 1} · ${esc(q.stem)}</b>
          <span class="pill">${esc(q.skill)}</span></div>
        ${q.options.map((opt, j) => `
          <div class="q-option btn-sm ${j === q.answer_index ? "correct" : ""}" style="cursor:default;padding:8px 12px;margin:6px 0 0">
            <span class="key">${"ABCD"[j]}</span><span>${esc(opt)}</span></div>`).join("")}
        <div class="q-explain">${esc(q.explanation)}<div style="margin-top:4px">${cites.chip(q.citation)}</div></div>
      </div>`).join("")}`;
  $("quiz-to-exam").addEventListener("click", () => { answers.fill(null); idx = 0; renderQuestion(); });
}
