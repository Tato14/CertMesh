// Orchestration trace as a visual flow (Feature E).
//
// Two levels: a pipeline of agent nodes that animates pending → running →
// ok/revised/abstained while a run "replays" (timings are the real per-step
// duration_ms, scaled so the run is watchable), and a click-through detail view
// per node (inputs, outputs, critic verdict, citations). A critic-forced
// revision draws a dashed loop-back arc + iteration badge on the node — the
// reflection loop is something you SEE, not read about.

import { $, badge, citeCollector, esc, emptyState, reducedMotion, sleep } from "./util.js";

const STATUS_LABEL = { ok: "ok", revised: "revised", abstained: "abstained", running: "running…", pending: "queued" };

let groups = [];          // [{agent, steps:[TraceStep], finalStatus}]
let lastResult = null;
let replayToken = 0;      // bumping it cancels any in-flight replay

export function init() {
  replayToken++;
  $("trace-content").innerHTML = emptyState("⇄",
    "No run yet",
    "Run a scenario to watch the planner fan out to specialists and the critic verify every claim.");
  $("backend-pill").textContent = "";
  $("trace-detail").innerHTML = "";
}

export function showRunning(req) {
  $("trace-detail").innerHTML = "";
  $("trace-content").innerHTML = `
    <div class="plan-reasoning"><span class="pulse">Planning…</span> the orchestrator is resolving
      “${esc(req.goal || req.view)}” and choosing which specialists to run.</div>
    <div class="skeleton" style="height:54px"></div>
    <div class="flow-connector"></div>
    <div class="skeleton" style="height:54px"></div>
    <div class="flow-connector"></div>
    <div class="skeleton" style="height:54px"></div>`;
}

function groupSteps(result) {
  const out = [];
  for (const s of result.trace.steps) {
    const last = out[out.length - 1];
    if (last && last.agent === s.agent) last.steps.push(s);
    else out.push({ agent: s.agent, steps: [s] });
  }
  for (const g of out) g.finalStatus = g.steps[g.steps.length - 1].status;
  return out;
}

function criticLine(step) {
  const v = step.critic;
  if (!v) return "";
  const pii = v.pii_findings?.length ? ` · PII findings: ${v.pii_findings.length}` : "";
  return `<div class="critic-line">critic: <b class="${esc(v.action)}">${esc(v.action)}</b>
    · grounded ${v.claims_supported}/${v.claims_checked}${pii}</div>`;
}

function nodeHtml(g, state, iteration) {
  const dur = g.steps.reduce((a, s) => a + s.duration_ms, 0);
  const stepShown = g.steps[Math.min(iteration ?? g.steps.length - 1, g.steps.length - 1)];
  const stLabel = state === "done" ? STATUS_LABEL[g.finalStatus] : STATUS_LABEL[state];
  const stClass = state === "done" ? g.finalStatus : state;
  const loops = g.steps.length - 1;
  const loopBadge = state === "done" && loops > 0
    ? `<span class="loop-badge" title="The critic rejected an ungrounded claim; the agent revised.">↻ revision ×${loops}</span>
       <svg class="loop-svg" aria-hidden="true"><path d="M2,70 C 16,70 16,10 2,10"></path></svg>`
    : "";
  return `
    <div class="flow-node ${state === "done" ? g.finalStatus : state}" data-agent="${esc(g.agent)}" tabindex="0"
         role="button" aria-label="Trace step: ${esc(g.agent)}">
      ${loopBadge}
      <div class="head">
        <span class="nm">${esc(g.agent)}</span>
        <span class="st ${stClass}">${esc(stepShown.action)} · ${stLabel}${state === "done" ? ` · ${dur.toFixed(0)}ms` : ""}</span>
      </div>
      <div class="sub">${esc(stepShown.output_summary.slice(0, 170))}</div>
      ${state === "done" ? criticLine(g.steps[g.steps.length - 1]) : ""}
    </div>`;
}

function criticSummaryNode(result) {
  const verdicts = result.trace.steps.map((s) => s.critic).filter(Boolean);
  if (!verdicts.length) return "";
  const checked = verdicts.reduce((a, v) => a + v.claims_checked, 0);
  const supported = verdicts.reduce((a, v) => a + v.claims_supported, 0);
  const revisions = result.trace.steps.filter((s) => s.status === "revised").length;
  const pii = verdicts.reduce((a, v) => a + (v.pii_findings?.length || 0), 0);
  const status = result.abstained ? "abstained" : revisions ? "revised" : "ok";
  return `
    <div class="flow-connector done-connector"></div>
    <div class="flow-node ${status}" data-agent="__critic" tabindex="0" role="button" aria-label="Critic summary">
      <div class="head"><span class="nm">Critic / Verifier</span>
        <span class="st ${status}">cross-cutting</span></div>
      <div class="sub">${supported}/${checked} claims grounded · ${revisions} revision${revisions === 1 ? "" : "s"} forced · ${pii} PII finding${pii === 1 ? "" : "s"}</div>
    </div>`;
}

function footer(result) {
  return `<div class="muted small" style="margin-top:10px">
    total ${result.trace.total_duration_ms}ms · language <span class="mono">${esc(result.language)}</span>
    · confidence ${Math.round(result.confidence * 100)}%</div>`;
}

function bindClicks() {
  document.querySelectorAll("#trace-content .flow-node").forEach((n) => {
    const open = () => showDetail(n.dataset.agent, n);
    n.addEventListener("click", open);
    n.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
  });
}

/* Replay the trace: per-step display time proportional to the REAL duration_ms
   (scaled into a watchable window), so the animation is honest. */
export async function replay(result, onAgentSettled) {
  lastResult = result;
  groups = groupSteps(result);
  $("backend-pill").textContent =
    `${result.trace.model_backend} · ${result.trace.retrieval_backend}`;
  $("trace-detail").innerHTML = "";

  const box = $("trace-content");
  const alts = result.plan.alternatives || [];
  const res = result.plan.resolution || {};
  const ledger = (alts.length || Object.keys(res).length) ? `
    <details class="ledger">
      <summary>deliberation — ${alts.length} route${alts.length === 1 ? "" : "s"} rejected · resolution sources</summary>
      ${alts.map((a) => `<div class="alt">✕ ${esc(a)}</div>`).join("")}
      ${Object.entries(res).map(([k, v]) =>
        `<div class="src"><b>${esc(k)}</b> ${esc(String(v))}</div>`).join("")}
    </details>` : "";
  const planHeader = `<div class="plan-reasoning"><b>Plan.</b> ${esc(result.plan.reasoning)}${ledger}</div>`;

  if (reducedMotion()) {
    box.innerHTML = planHeader + groups.map((g) =>
      nodeHtml(g, "done")).join(`<div class="flow-connector"></div>`) +
      criticSummaryNode(result) + footer(result);
    sizeLoopArc(box);
    bindClicks();
    groups.forEach((g) => onAgentSettled?.(g.agent));
    return;
  }

  const total = Math.max(result.trace.steps.reduce((a, s) => a + s.duration_ms, 0), 1);
  const scale = 2400 / total;
  const stepDelay = (s) => Math.min(Math.max(s.duration_ms * scale, 340), 1200);
  const token = ++replayToken;
  // a cleared/replaced trace cancels this replay instead of writing into it
  const cancelled = () => token !== replayToken || !box.querySelector(".slot");

  box.innerHTML = planHeader +
    groups.map((g, i) => `<div class="slot" data-slot="${i}">${nodeHtml(g, "pending")}</div>` +
      (i < groups.length - 1 ? `<div class="flow-connector" data-conn="${i}"></div>` : "")).join("") +
    `<div class="slot" data-slot="critic"></div><div class="slot" data-slot="footer"></div>`;

  for (let i = 0; i < groups.length; i++) {
    const g = groups[i];
    if (cancelled()) return;
    const slot = box.querySelector(`[data-slot="${i}"]`);
    for (let it = 0; it < g.steps.length; it++) {
      slot.innerHTML = nodeHtml(g, "running", it);
      slot.querySelector(".flow-node").classList.add("running");
      slot.querySelector(".st").classList.add("pulse");
      await sleep(stepDelay(g.steps[it]));
      if (cancelled()) return;
      if (g.steps[it].status === "revised" && it < g.steps.length - 1) {
        // show the critic rejection beat before the agent's revision pass
        slot.innerHTML = nodeHtml(g, "revised", it) + "";
        const node = slot.querySelector(".flow-node");
        node.insertAdjacentHTML("beforeend",
          `<div class="critic-line">critic: <b class="revise">revise</b> — ${esc(g.steps[it].critic?.notes || "ungrounded claim, returning to agent")}</div>`);
        await sleep(700);
        if (cancelled()) return;
      }
    }
    slot.innerHTML = nodeHtml(g, "done");
    sizeLoopArc(slot);
    const conn = box.querySelector(`[data-conn="${i}"]`);
    if (conn) conn.classList.add("active");
    onAgentSettled?.(g.agent);
  }
  box.querySelector(`[data-slot="critic"]`).innerHTML = criticSummaryNode(result);
  box.querySelector(`[data-slot="footer"]`).innerHTML = footer(result);
  bindClicks();
}

/* Fit the dashed loop-back arc to the node's actual height. */
function sizeLoopArc(scope) {
  scope.querySelectorAll(".flow-node").forEach((node) => {
    const svg = node.querySelector(".loop-svg");
    if (!svg) return;
    const h = node.getBoundingClientRect().height;
    svg.setAttribute("viewBox", `0 0 16 ${h}`);
    svg.querySelector("path").setAttribute("d",
      `M2,${h - 14} C 15,${h - 14} 15,12 2,12`);
  });
}

function showDetail(agent, nodeEl) {
  document.querySelectorAll("#trace-content .flow-node").forEach((n) => n.classList.remove("selected"));
  nodeEl?.classList.add("selected");
  const detail = $("trace-detail");
  if (agent === "__critic") {
    const verdicts = lastResult.trace.steps.filter((s) => s.critic);
    detail.innerHTML = `<div class="trace-detail">
      <div class="spread"><b>Critic / Verifier</b>
        <button class="btn-ghost btn-sm" id="trace-detail-close">✕</button></div>
      <p class="muted small" style="margin-top:6px">Checks every cited snippet is a verbatim slice of what
        the producing agent retrieved; scans manager output for identifiers. Drives revise / abstain.</p>
      ${verdicts.map((s) => `<dl><dt>${esc(s.agent)}</dt>
        <dd>${esc(s.critic.action)} · ${s.critic.claims_supported}/${s.critic.claims_checked} grounded
        ${s.critic.notes ? `— <span class="muted">${esc(s.critic.notes)}</span>` : ""}</dd></dl>`).join("")}
    </div>`;
  } else {
    const g = groups.find((x) => x.agent === agent);
    if (!g) return;
    const cites = citeCollector();
    const sources = g.steps.flatMap((s) => s.sources || []);
    const chips = sources.map((c) => cites.chip(c)).join(" ");
    detail.innerHTML = `<div class="trace-detail">
      <div class="spread"><b>${esc(g.agent)}</b>
        <button class="btn-ghost btn-sm" id="trace-detail-close">✕</button></div>
      ${g.steps.map((s) => `
        <dl>
          <dt>step</dt><dd>${esc(s.action)} · ${badge(s.status === "ok" ? "ready" : s.status === "revised" ? "borderline" : "not_ready", s.status)} · ${s.duration_ms}ms</dd>
          <dt>inputs</dt><dd class="mono small">${esc(JSON.stringify(s.inputs))}</dd>
          <dt>output</dt><dd>${esc(s.output_summary)}</dd>
          ${s.critic ? `<dt>critic</dt><dd>${esc(s.critic.action)} · grounded ${s.critic.claims_supported}/${s.critic.claims_checked}${s.critic.ungrounded_claims?.length ? ` · rejected: <span class="muted">“${esc(s.critic.ungrounded_claims[0].slice(0, 120))}…”</span>` : ""}${s.critic.notes ? `<div class="muted small">${esc(s.critic.notes)}</div>` : ""}</dd>` : ""}
        </dl>`).join("<hr style='border:0;border-top:1px dashed var(--line)'>")}
      ${chips ? `<div style="margin-top:6px"><span class="muted small">retrieved sources:</span><br>${chips}</div>` : ""}
    </div>`;
  }
  detail.querySelector("#trace-detail-close")?.addEventListener("click", () => {
    detail.innerHTML = "";
    document.querySelectorAll("#trace-content .flow-node").forEach((n) => n.classList.remove("selected"));
  });
}
