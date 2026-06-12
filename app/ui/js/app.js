// CertMesh dashboard entry point: tabs, presets, run flow, status pills.
// Zero-build: native ES modules served by the FastAPI app.

import { api } from "./api.js";
import { store } from "./state.js";
import * as trace from "./trace.js";
import * as learner from "./learner.js";
import * as graph from "./graph.js";
import * as calendar from "./calendar.js";
import * as quiz from "./quiz.js";
import * as manager from "./manager.js";
import * as quality from "./quality.js";
import { $, esc, highlightSnippet } from "./util.js";

/* ── tabs ───────────────────────────────────────────────────────────────── */

function switchTab(name) {
  document.querySelectorAll("#tabs [role=tab]").forEach((b) =>
    b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  document.querySelectorAll(".view").forEach((v) =>
    v.classList.toggle("active", v.id === `view-${name}`));
  if (name === "graph") graph.activate();
  if (name === "calendar") calendar.activate();
  if (name === "quality") quality.activate();
}

/* ── evidence inspector: Foundry IQ citation chips open the verbatim source ── */

function closeEvidence() {
  document.getElementById("source-pop")?.remove();
}

async function openEvidence(chipEl) {
  closeEvidence();
  const id = chipEl.dataset.sourceId;
  const snippet = chipEl.dataset.snippet || "";
  const pop = document.createElement("div");
  pop.id = "source-pop";
  pop.className = "source-pop";
  pop.innerHTML = `<div class="spread"><b>Evidence inspector</b>
      <button class="btn-ghost btn-sm" data-close>✕</button></div>
    <div class="skeleton" style="height:60px;margin-top:8px"></div>`;
  document.body.appendChild(pop);
  pop.querySelector("[data-close]").addEventListener("click", closeEvidence);
  try {
    const src = await api.source(id);
    pop.innerHTML = `<div class="spread"><b>Evidence inspector</b>
        <button class="btn-ghost btn-sm" data-close>✕</button></div>
      <div class="muted small mono" style="margin:4px 0 8px">${esc(src.locator)} · ${esc(src.source)}</div>
      <div class="src-text">${highlightSnippet(src.text, snippet)}</div>
      <p class="muted small" style="margin:8px 0 0">The <mark>highlighted</mark> span is the verbatim
        slice the agent cited — the critic verified it is a substring of this retrieved source.
        Synthetic corpus.</p>`;
    pop.querySelector("[data-close]").addEventListener("click", closeEvidence);
  } catch (e) {
    pop.innerHTML = `<div class="spread"><b>Evidence inspector</b>
      <button class="btn-ghost btn-sm" data-close>✕</button></div>
      <p class="muted small">Source unavailable: ${esc(e.message)}</p>`;
    pop.querySelector("[data-close]").addEventListener("click", closeEvidence);
  }
}

/* ── request form ───────────────────────────────────────────────────────── */

function applyForm(req) {
  $("f-view").value = req.view || "learner";
  $("f-goal").value = req.goal || "";
  $("f-role").value = req.role || "";
  $("f-learner").value = req.learner_id || "";
  $("f-team").value = req.team || "";
  $("f-hours").value = req.available_hours_per_week ?? "";
}

function reqFromForm() {
  const r = { view: $("f-view").value, goal: $("f-goal").value };
  if ($("f-role").value) r.role = $("f-role").value;
  if ($("f-learner").value) r.learner_id = $("f-learner").value.trim();
  if ($("f-team").value) r.team = $("f-team").value.trim();
  if ($("f-hours").value) r.available_hours_per_week = parseFloat($("f-hours").value);
  return r;
}

/* ── run flow: results stream in as the trace replays ───────────────────── */

let running = false;

function toast(msg) {
  document.getElementById("app-toast")?.remove();
  const el = document.createElement("div");
  el.id = "app-toast"; el.className = "app-toast"; el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2200);
}

async function runRequest(req) {
  if (running) { toast("Agents are still running — one moment…"); return; }
  running = true;
  const btn = $("btn-run");
  btn.disabled = true; btn.textContent = "Agents running…";
  $("btn-clear").disabled = true;
  setTraceCollapsed(false);          // unfold the orchestration panel for the run
  store.lastRequest = req;
  applyForm(req);
  const isManager = req.view === "manager";
  switchTab(isManager ? "manager" : "learner");
  if (isManager) manager.showLoading(); else learner.showLoading();
  trace.showRunning(req);
  try {
    const r = await api.run(req);
    store.lastResult = r;
    quiz.setAssessment(r);
    if (isManager) {
      await trace.replay(r);
      manager.render(r);
    } else {
      learner.render(r);
      await trace.replay(r, (agent) => learner.reveal(agent));
      await learner.finish(r);
    }
  } catch (e) {
    console.error(e);
    (isManager ? manager : learner).showError(e.message);
    trace.init();
  } finally {
    running = false;
    btn.disabled = false; btn.textContent = "Run agents";
    $("btn-clear").disabled = false;
  }
}

/* ── presets ────────────────────────────────────────────────────────────── */

function presetCard(p) {
  const b = document.createElement("button");
  b.className = "preset-card";
  b.innerHTML = `<span class="t"><span class="k">${esc(p.view)}</span>${esc(p.label)}</span>
    <span class="w">${esc(p.watch || p.description)}</span>`;
  b.addEventListener("click", () => {
    if (p.request) runRequest({ ...p.request });
    else if (p.ui?.tab === "graph") { switchTab("graph"); graph.preselectRole(p.ui.role); }
    else if (p.ui?.tab === "calendar") { switchTab("calendar"); calendar.showCompare(p.ui.compare); }
  });
  return b;
}

async function loadPresets() {
  try {
    const d = await api.presets();
    store.presets = d.presets;
    $("disclosure-text").textContent = d.disclosure;
    const box = $("presets");
    box.innerHTML = "";
    d.presets.forEach((p) => box.appendChild(presetCard(p)));
  } catch (e) {
    $("presets").innerHTML = `<div class="error-state">Could not load presets: ${esc(e.message)}</div>`;
  }
}

async function loadHealth() {
  try {
    const h = await api.health();
    store.health = h;
    $("status-pills").innerHTML = `
      <span class="pill mono"><span class="dot ok"></span>model: ${esc(h.model_backend)}</span>
      <span class="pill mono"><span class="dot ok"></span>retrieval: ${esc(h.retrieval_backend)}</span>
      <span class="pill mono"><span class="dot ${h.mcp_enabled ? "ok" : "warn"}"></span>Learn MCP</span>`;
  } catch {
    $("status-pills").innerHTML = `<span class="pill"><span class="dot warn"></span>backend unreachable</span>`;
  }
}

/* ── boot ───────────────────────────────────────────────────────────────── */

function setTraceCollapsed(collapsed) {
  document.body.classList.toggle("trace-collapsed", collapsed);
  $("trace-toggle").setAttribute("aria-pressed", String(!collapsed));
  $("trace-toggle").textContent = collapsed ? "⚙ Orchestration ▾" : "⚙ Orchestration ▴";
}

function boot() {
  trace.init(); learner.init(); quiz.init(); manager.init();

  document.querySelectorAll("#tabs [role=tab]").forEach((b) =>
    b.addEventListener("click", () => switchTab(b.dataset.tab)));

  $("btn-run").addEventListener("click", () => runRequest(reqFromForm()));
  $("btn-clear").addEventListener("click", () => {
    applyForm({}); learner.init(); trace.init();
  });

  $("trace-toggle").addEventListener("click", () =>
    setTraceCollapsed(!document.body.classList.contains("trace-collapsed")));

  store.on("run-request", runRequest);
  store.on("switch-tab", switchTab);
  store.on("open-quiz", (mode) => { switchTab("assessment"); quiz.open(mode); });

  // evidence inspector (delegated: chips are re-rendered constantly)
  document.addEventListener("click", (e) => {
    const chip = e.target.closest(".cite[data-source-id]");
    if (chip) { e.preventDefault(); openEvidence(chip); return; }
    if (!e.target.closest("#source-pop")) closeEvidence();
  });

  loadPresets();
  loadHealth();
  switchTab("graph");                // the knowledge graph is the main view
}

boot();
