// Learning-path knowledge graph — the MAIN view: the Fabric IQ ontology
// rendered with Cytoscape + dagre. Explore the ecosystem by track, light up a
// role's certification path in prerequisite order, overlay a learner's
// completed / in-progress / at-risk states, and click any certification to
// launch a real agent run. Degrades to a designed fallback when the CDN is
// unreachable.

import { api } from "./api.js";
import { store } from "./state.js";
import { $, esc, errorState, pct, trackColor } from "./util.js";

// Light, Microsoft-adjacent palette (Cytoscape canvas can't read CSS vars).
const C = {
  accent: "#1d6fd0", good: "#157a4a", warn: "#b07d10", bad: "#b3303e",
  muted: "#5d6e87", faint: "#8d9bb1", line: "#c4cfdf", ink: "#1b2533",
  violet: "#6f4bc4",
};
const TRACK_C = {
  technical: "#1d6fd0", clinical: "#0d8377", compliance: "#6f4bc4", security: "#b1530f",
};
const TRACK_BG = {
  technical: "#eaf2fc", clinical: "#e4f3f1", compliance: "#f0ebfa", security: "#faeede",
};

let cy = null;
let data = null;
let activatePromise = null;
let selectedRole = "";
let selectedLearner = "";

/* Pinned CDN sources, lazy-loaded only when the Graph tab opens (zero-build:
   nothing requires compilation). Order matters: dagre before the adapter. */
const ENGINE_SRC = [
  "https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.30.2/cytoscape.min.js",
  "https://cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js",
  "https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js",
];

const loadScript = (src) => new Promise((resolve, reject) => {
  const s = document.createElement("script");
  s.src = src;
  s.onload = resolve;
  s.onerror = () => reject(new Error(`unreachable: ${src}`));
  document.head.appendChild(s);
});

async function ensureEngine() {
  if (window.cytoscape && window.cytoscapeDagre) return true;
  const timeout = new Promise((_, rej) =>
    setTimeout(() => rej(new Error("CDN timeout")), 12000));
  try {
    await Promise.race([(async () => {
      for (const src of ENGINE_SRC) await loadScript(src);
    })(), timeout]);
  } catch { /* fall through to the designed fallback */ }
  return !!(window.cytoscape && window.cytoscapeDagre);
}

/* All callers share one activation; late callers await the same build. */
export function activate() {
  if (!activatePromise) activatePromise = doActivate();
  return activatePromise;
}

async function doActivate() {
  const root = $("graph-root");
  root.innerHTML = `<div class="muted small">Loading ontology &amp; graph engine…</div>`;
  let engineReady = false;
  try {
    [data, engineReady] = await Promise.all([
      store.graphData ? Promise.resolve(store.graphData) : api.graph(),
      ensureEngine(),
    ]);
    store.graphData = data;
  } catch (e) {
    root.innerHTML = errorState(`Could not load /api/graph: ${e.message}`);
    activatePromise = null;
    return;
  }
  root.innerHTML = layoutHtml();
  fillSelectors();
  if (engineReady) {
    try { window.cytoscape.use(window.cytoscapeDagre); } catch { /* already registered */ }
    buildCy();
  } else {
    $("cy").outerHTML = cdnFallback();
  }
  bind();
}

function layoutHtml() {
  const nCerts = data.elements.nodes.filter((n) => n.data.type === "certification").length;
  const nRoles = Object.keys(data.roles).length;
  return `
  <div class="graph-toolbar">
    <div class="field"><label for="g-role">Role path</label>
      <select id="g-role"><option value="">— all roles —</option></select></div>
    <div class="field"><label for="g-track">Track</label>
      <select id="g-track"><option value="">— all tracks —</option>
        <option value="technical">technical</option><option value="clinical">clinical</option>
        <option value="compliance">compliance</option><option value="security">security</option></select></div>
    <div class="field"><label for="g-learner">Learner overlay</label>
      <select id="g-learner"><option value="">— none —</option></select></div>
    <label class="field" style="flex-direction:row;align-items:center;gap:6px;margin:18px 0 0;cursor:pointer">
      <input type="checkbox" id="g-skills" style="width:auto" /> show skills</label>
    <button class="btn-ghost btn-sm" id="g-fit">Fit</button>
    <button class="btn-ghost btn-sm" id="g-reset">Reset</button>
    <span class="pill" style="margin-left:auto">${nCerts} certifications · ${nRoles} roles</span>
  </div>
  <div class="graph-layout">
    <div>
      <div id="cy" role="img" aria-label="Knowledge graph of roles, certifications and skills"></div>
      <div class="graph-legend">
        <span><span class="sw role"></span>role</span>
        <span><span class="sw cert"></span>certification</span>
        <span><span class="sw skill"></span>skill</span>
        <span><span class="ln"></span>requires / covers</span>
        <span><span class="ln pre"></span>prerequisite</span>
        <span><span class="ln int"></span>internal (fictional)</span>
        ${Object.entries(TRACK_C).map(([t, c]) =>
          `<span><span class="sw" style="background:${c}"></span>${t}</span>`).join("")}
      </div>
      <div id="path-summary"></div>
      <div class="overlay-legend" id="overlay-legend" style="display:none">
        <span class="pill"><span class="dot" style="background:${C.good}"></span>completed</span>
        <span class="pill"><span class="dot" style="background:${C.accent}"></span>in progress</span>
        <span class="pill"><span class="dot" style="background:${C.bad}"></span>at risk</span>
        <span class="pill"><span class="dot" style="background:${C.faint}"></span>not started</span>
      </div>
    </div>
    <div class="subpanel cert-panel" id="cert-panel">
      <p class="muted small" style="margin:0">Pick a <b>role</b> to light up its certification path in
        prerequisite order, filter by <b>track</b>, or click any certification for its skills,
        threshold and hours — and to generate a study plan with the real agents.</p>
    </div>
  </div>`;
}

function cdnFallback() {
  const rows = Object.entries(data.roles).map(([role, r]) => `
    <tr><td>${esc(role)}</td>
      <td class="mono">${r.certs.join(" → ")}</td>
      <td class="mono">${r.total_hours}h</td><td class="mono">${r.prerequisite_edges}</td></tr>`).join("");
  return `<div class="cdn-fallback" id="cy">
    <b>Graph engine unavailable</b> — the Cytoscape CDN could not be reached (offline?).
    The ontology itself is served locally; here are the role-based certification paths:
    <table style="margin-top:10px"><thead><tr><th>Role</th><th>Certification path (prerequisite order)</th><th>Hours</th><th>Prereqs</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

function fillSelectors() {
  const roleSel = $("g-role");
  Object.keys(data.roles).forEach((r) => {
    const o = document.createElement("option"); o.value = r; o.textContent = r; roleSel.appendChild(o);
  });
  const learnerSel = $("g-learner");
  data.learners.forEach((l) => {
    const o = document.createElement("option");
    o.value = l.learner_id;
    o.textContent = `${l.learner_id} · ${l.role}`;
    learnerSel.appendChild(o);
  });
}

const DAGRE = { name: "dagre", rankDir: "LR", rankSep: 80, nodeSep: 12, edgeSep: 8, padding: 16 };

function buildCy() {
  const labelW = (px) => (ele) => ele.data("label").length * px + 16;
  cy = window.cytoscape({
    container: $("cy"),
    elements: data.elements,
    style: [
      { selector: "node", style: {
          label: "data(label)", color: C.ink, "font-family": "Inter, sans-serif",
          "font-size": 10, "text-valign": "center", "text-halign": "center",
          "border-width": 1.5, "transition-property": "opacity", "transition-duration": "180ms",
      } },
      { selector: 'node[type="role"]', style: {
          shape: "round-rectangle", width: labelW(5.6), height: 26,
          "background-color": "#f1ecfb", "border-color": C.violet, color: "#4a3091",
          "font-size": 10.5, "font-weight": 600,
      } },
      { selector: 'node[type="certification"]', style: {
          shape: "round-rectangle", width: labelW(7.2), height: 32,
          "background-color": (ele) => TRACK_BG[ele.data("track")] || "#eaf2fc",
          "border-color": (ele) => TRACK_C[ele.data("track")] || C.accent,
          color: C.ink,
          "font-family": "JetBrains Mono, monospace", "font-size": 11.5, "font-weight": 600,
      } },
      { selector: 'node[type="certification"][!real_exam]', style: { "border-style": "dashed" } },
      { selector: 'node[type="certification"][level="fundamentals"]', style: { height: 26, "font-size": 10.5 } },
      { selector: 'node[type="certification"][level="expert"]', style: { "border-width": 2.5 } },
      { selector: 'node[type="skill"]', style: {
          shape: "ellipse", width: 10, height: 10,
          "background-color": "#e4f3f1", "border-color": "#0d8377",
          color: C.muted, "font-size": 8.5,
          "text-valign": "center", "text-halign": "right", "text-margin-x": 4,
      } },
      { selector: "edge", style: {
          width: 1.2, "line-color": C.line, "curve-style": "bezier",
          "target-arrow-shape": "triangle", "target-arrow-color": C.line, "arrow-scale": 0.7,
          "transition-property": "opacity", "transition-duration": "180ms",
      } },
      { selector: 'edge[type="requires"]', style: { "line-color": "#b9a7e6", "target-arrow-color": "#b9a7e6", width: 1.6 } },
      { selector: 'edge[type="prerequisite"]', style: {
          "line-style": "dashed", "line-color": C.warn, "target-arrow-color": C.warn, width: 1.8 } },
      { selector: ".hide", style: { display: "none" } },
      { selector: ".dim", style: { opacity: 0.13 } },
      { selector: "node.path", style: { "border-width": 2.5 } },
      { selector: "edge.path", style: { width: 2.4 } },
      { selector: "node.state-completed", style: { "background-color": "#e1f2e9", "border-color": C.good, color: C.good } },
      { selector: "node.state-in_progress", style: { "border-color": C.accent, "border-width": 3.5 } },
      { selector: "node.state-at_risk", style: { "background-color": "#f9e7e9", "border-color": C.bad, color: C.bad } },
      { selector: "node.state-not_started", style: { "border-color": C.faint, color: C.muted } },
      { selector: "node:selected", style: { "overlay-color": C.accent, "overlay-opacity": 0.10, "overlay-padding": 6 } },
    ],
    layout: { name: "preset" },   // refreshVisibility() runs the real dagre pass
  });
  window.__cy = cy;   // debugging/testing hook
  cy.on("tap", 'node[type="certification"]', (ev) => showCertPanel(ev.target.data()));
  cy.on("tap", 'node[type="role"]', (ev) => { $("g-role").value = ev.target.data("label"); applyRole(ev.target.data("label")); });

  // lightweight tooltips
  const tip = document.createElement("div");
  tip.className = "cy-tip"; tip.style.display = "none";
  document.body.appendChild(tip);
  cy.on("mouseover", "node", (ev) => {
    const d = ev.target.data();
    tip.innerHTML = d.type === "certification"
      ? `<b>${esc(d.label)}</b> — ${esc(d.title)}<br>${esc(d.track)} · ${esc(d.level)} · ${d.hours}h recommended · pass ≥ ${pct(d.threshold)}${d.real_exam ? "" : " · internal (fictional)"}`
      : d.type === "role" ? `<b>${esc(d.label)}</b> — click to highlight this role's learning path`
      : `<b>${esc(d.label)}</b> — skill`;
    tip.style.display = "block";
  });
  cy.on("mouseout", "node", () => { tip.style.display = "none"; });
  cy.on("mousemove", (ev) => {
    if (tip.style.display === "block" && ev.originalEvent) {
      tip.style.left = `${ev.originalEvent.clientX + 14}px`;
      tip.style.top = `${ev.originalEvent.clientY + 12}px`;
    }
  });
  refreshVisibility();
}

/* Re-run dagre over only what's visible, so hidden skills don't leave gaps. */
function relayout() {
  if (!cy) return;
  cy.elements().not(".hide").layout(DAGRE).run();
  cy.fit(cy.elements().not(".hide").not(".dim"), 30);
}

/* Track filter + skills toggle. Skills on a selected role path stay visible. */
function refreshVisibility() {
  if (!cy) return;
  const showSkills = $("g-skills")?.checked;
  const track = $("g-track")?.value || "";
  cy.batch(() => {
    cy.nodes().removeClass("hide");
    if (!showSkills) cy.nodes('[type="skill"]').addClass("hide");
    if (track) {
      cy.nodes(`[type="certification"][track != "${track}"]`).addClass("hide");
      cy.nodes(`[type="role"][track != "${track}"]`).addClass("hide");
    }
    if (selectedRole) pathSkillNodes(selectedRole).removeClass("hide");
  });
  relayout();
}

function pathSkillNodes(role) {
  let skills = cy.collection();
  (data.roles[role]?.certs || []).forEach((c) => {
    skills = skills.union(cy.getElementById(`cert:${c}`).outgoers('edge[type="covers"]').targets());
  });
  return skills;
}

function bind() {
  $("g-role").addEventListener("change", (e) => applyRole(e.target.value));
  $("g-track").addEventListener("change", () => {
    // a track filter and a role path are different questions — reset the role
    $("g-role").value = ""; selectedRole = "";
    $("path-summary").innerHTML = "";
    cy?.elements().removeClass("dim path state-completed state-in_progress state-at_risk state-not_started");
    refreshVisibility();
  });
  $("g-skills").addEventListener("change", () =>
    selectedRole ? applyRole(selectedRole) : refreshVisibility());
  $("g-learner").addEventListener("change", (e) => applyLearner(e.target.value));
  $("g-fit")?.addEventListener("click", () => cy?.fit(cy.elements().not(".hide"), 30));
  $("g-reset")?.addEventListener("click", () => {
    $("g-role").value = ""; $("g-learner").value = ""; $("g-track").value = "";
    if ($("g-skills")) $("g-skills").checked = false;
    selectedLearner = "";
    applyRole("");
  });
}

/* ── role path highlighting ─────────────────────────────────────────────── */

function applyRole(role) {
  selectedRole = role;
  if (!role) {
    cy?.elements().removeClass("dim path state-completed state-in_progress state-at_risk state-not_started");
    $("path-summary").innerHTML = "";
    $("overlay-legend").style.display = "none";
    refreshVisibility();
    return;
  }
  if ($("g-track").value) { $("g-track").value = ""; }   // a role path spans tracks
  const info = data.roles[role];
  const certIds = info.certs.map((c) => `cert:${c}`);
  if (cy) {
    refreshVisibility();
    cy.batch(() => {
      cy.elements().addClass("dim").removeClass("path");
      const keep = cy.collection()
        .union(cy.getElementById(`role:${role}`))
        .union(certIds.map((id) => cy.getElementById(id)));
      let skills = cy.collection();
      certIds.forEach((id) => {
        const covers = cy.getElementById(id).outgoers('edge[type="covers"]');
        skills = skills.union(covers).union(covers.targets());
      });
      const pathEdges = cy.edges().filter((e) =>
        (certIds.includes(e.source().id()) || e.source().id() === `role:${role}`) &&
        (certIds.includes(e.target().id())));
      keep.union(skills).union(pathEdges).removeClass("dim");
      keep.union(pathEdges).addClass("path");
    });
    cy.fit(cy.elements().not(".dim").not(".hide"), 40);
  }
  $("path-summary").innerHTML = `<div class="path-summary fade-up">
    <b>${esc(role)}</b> <span class="chain">→ ${info.certs.join(" → ")}</span>
    <span class="pill">${info.certs.length} certs</span>
    <span class="pill mono">${info.total_hours}h recommended</span>
    <span class="pill">${info.prerequisite_edges} prerequisite${info.prerequisite_edges === 1 ? "" : "s"}</span>
  </div>`;
  if (selectedLearner) paintLearnerStates();
}

/* ── learner overlay ────────────────────────────────────────────────────── */

function applyLearner(learnerId) {
  selectedLearner = learnerId;
  cy?.nodes().removeClass("state-completed state-in_progress state-at_risk state-not_started");
  if (!learnerId) { $("overlay-legend").style.display = "none"; if (selectedRole) applyRole(selectedRole); return; }
  const learner = data.learners.find((l) => l.learner_id === learnerId);
  if (!learner) return;
  if ($("g-role").value !== learner.role) { $("g-role").value = learner.role; applyRole(learner.role); }
  paintLearnerStates();
  $("overlay-legend").style.display = "flex";
}

function paintLearnerStates() {
  if (!cy || !selectedLearner) return;
  const learner = data.learners.find((l) => l.learner_id === selectedLearner);
  const info = data.roles[learner.role];
  if (!info) return;
  const currentIdx = info.certs.indexOf(learner.certification);
  info.certs.forEach((code, i) => {
    const node = cy.getElementById(`cert:${code}`);
    const cert = data.elements.nodes.find((n) => n.data.id === `cert:${code}`)?.data;
    let state;
    if (code === learner.certification) {
      state = learner.exam_outcome === "pass" ? "completed"
        : learner.practice_score_avg < (cert?.threshold ?? 0.7) - 0.1 ? "at_risk" : "in_progress";
    } else if (currentIdx === -1 ? false : i < currentIdx) {
      state = "completed";      // prerequisite of the active cert — assumed done
    } else {
      state = "not_started";
    }
    node.addClass(`state-${state}`);
  });
}

/* ── certification side panel ───────────────────────────────────────────── */

function showCertPanel(d) {
  const prereqs = data.elements.edges
    .filter((e) => e.data.type === "prerequisite" && e.data.target === d.id)
    .map((e) => e.data.source.replace("cert:", ""));
  $("cert-panel").innerHTML = `
    <div class="spread"><h3 class="mono">${esc(d.label)}</h3>
      <span class="pill" style="border-color:${trackColor(d.track)};color:${trackColor(d.track)}">${esc(d.track)}</span></div>
    <p class="dim" style="margin:4px 0 10px">${esc(d.title)} <span class="pill">${esc(d.level)}</span>${d.real_exam ? "" : " <span class='pill'>fictional</span>"}</p>
    <div class="kpis" style="margin-bottom:10px">
      <div class="kpi"><div class="k">recommended</div><div class="v">${d.hours}h</div></div>
      <div class="kpi"><div class="k">pass threshold</div><div class="v">${pct(d.threshold)}</div></div>
    </div>
    ${prereqs.length ? `<p class="small muted">Prerequisites: <span class="mono">${prereqs.join(", ")}</span></p>` : ""}
    <p class="small muted" style="margin-bottom:4px">Skills covered:</p>
    <ul class="skills small dim" style="margin:0 0 12px;padding-left:18px">
      ${(d.skills || []).map((s) => `<li>${esc(s)}</li>`).join("")}</ul>
    <button class="btn-primary" id="g-genplan">Generate study plan ▸</button>
    <p class="muted small" style="margin:8px 0 0">Pre-fills the request and runs the real
      curator → plan → engagement → assessment pipeline.</p>`;
  $("g-genplan").addEventListener("click", () => {
    const req = { view: "learner", goal: `Help me prepare for ${d.label}` };
    if (selectedLearner) req.learner_id = selectedLearner;
    store.emit("run-request", req);
  });
}

/* Preset entry point: land on the tab with a role pre-selected. */
export async function preselectRole(role) {
  await activate();
  if ($("g-role")) { $("g-role").value = role; applyRole(role); }
}
