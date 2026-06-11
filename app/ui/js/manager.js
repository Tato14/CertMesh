// Manager view (Feature D upgrade): a real teams × tracks readiness heatmap
// with k-anonymity-suppressed cells rendered honestly (lock + "n < k"), risk
// flags as designed severity cards, and an aggregate team trend line from
// /api/progress/team. The PII-safe behaviour stays visually explicit.

import { api } from "./api.js";
import { store } from "./state.js";
import { trendChart } from "./progress.js";
import { $, badge, emptyState, errorState, esc, pct, skeletonCard } from "./util.js";

const TRACK_ORDER = ["technical", "clinical", "compliance", "security"];
let lastInsights = null;

export function init() {
  $("manager-root").innerHTML = `<div class="card">${emptyState("▦", "Aggregate team readiness",
    "The Manager Insights Agent reports by team and track only — individuals are never identified, and groups under the k-anonymity threshold are suppressed by the critic.",
    `<button class="btn-primary" id="mgr-run">Run manager view</button>`)}</div>`;
  $("mgr-run")?.addEventListener("click", () =>
    store.emit("run-request", { view: "manager", goal: "How are my teams progressing?" }));
}

export function showLoading() {
  $("manager-root").innerHTML = skeletonCard("Manager Insights — aggregating…", 5);
}

export function showError(msg) {
  $("manager-root").innerHTML = `<div class="card">${errorState(msg)}</div>`;
}

export function render(result) {
  const mi = result.manager_insights;
  if (!mi) { init(); return; }
  lastInsights = mi;

  const cells = new Map();           // "team|track" -> summary
  const teams = new Set();
  const seenTracks = new Set();
  for (const s of mi.summaries) {
    const [team, track] = s.scope.split(" · ");
    teams.add(team); seenTracks.add(track); cells.set(`${team}|${track}`, s);
  }
  const suppressed = new Set(mi.suppressed_groups.map((g) => g.replace(" · ", "|")));
  for (const key of suppressed) {
    teams.add(key.split("|")[0]); seenTracks.add(key.split("|")[1]);
  }
  const teamList = [...teams].sort();
  const TRACKS = TRACK_ORDER.filter((t) => seenTracks.has(t));

  const grid = [`<div class="hd"></div>`, ...TRACKS.map((t) => `<div class="hd">${t}</div>`)];
  for (const team of teamList) {
    grid.push(`<div class="hd mono">${esc(team)}</div>`);
    for (const track of TRACKS) {
      const s = cells.get(`${team}|${track}`);
      if (s) {
        grid.push(`<div class="cell band-${s.readiness_band}" title="${esc(team)} · ${track}: avg practice ${pct(s.avg_practice_score)}, ${pct(s.pct_on_track)} on track">
          <span class="v">${pct(s.avg_practice_score)}</span>
          <span class="n">n=${s.n_learners} · ${pct(s.pct_on_track)} on track</span></div>`);
      } else if (suppressed.has(`${team}|${track}`)) {
        grid.push(`<div class="cell suppressed" title="Group below the k-anonymity threshold — never reported">
          🔒 n &lt; ${mi.min_group_size}<br>suppressed</div>`);
      } else {
        grid.push(`<div class="cell absent">—</div>`);
      }
    }
  }

  const risks = mi.risks.map((r) => `
    <div class="risk-card ${esc(r.severity)}">
      <div class="top"><span class="kind">${esc(r.kind).toUpperCase()}</span>
        <span class="mono small">${esc(r.scope)}</span>
        <span class="pill">${esc(r.severity)}</span></div>
      <div class="dim small">${esc(r.detail)}</div>
    </div>`).join("");

  $("manager-root").innerHTML = `
    <div class="card fade-up">
      <div class="card-title spread">
        <span>Manager Insights <span class="badge ready">PII-safe · aggregate only</span></span>
        <span class="pill">scope: ${esc(mi.generated_for)}</span>
      </div>
      <p class="muted small">${esc(mi.notes)}</p>
      ${result.abstained ? `<div class="error-state" style="margin-bottom:12px">⚠ ${esc(result.messages.join(" "))}</div>` : ""}
      <div class="mgr-layout">
        <div>
          <h3 style="margin-bottom:8px">Readiness heatmap <span class="muted small">teams × tracks · colour = avg readiness band</span></h3>
          <div class="heatmap" style="grid-template-columns: 86px repeat(${TRACKS.length}, 1fr)">${grid.join("")}</div>
          <div class="wrap" style="margin-top:8px">
            ${badge("ready")} ${badge("borderline")} ${badge("not_ready")}
            <span class="pill">🔒 suppressed = group under ${mi.min_group_size} learners</span>
          </div>
          <div style="margin-top:16px">
            <div class="spread"><h3>Team trend <span class="muted small">aggregate practice score per week</span></h3>
              <select id="mgr-trend-team" style="width:auto">${teamList.map((t) =>
                `<option value="${esc(t)}">${esc(t)}</option>`).join("")}</select></div>
            <div id="mgr-trend" style="margin-top:8px"><div class="skeleton" style="height:110px"></div></div>
          </div>
        </div>
        <div>
          <h3 style="margin-bottom:8px">Risk flags <span class="muted small">${mi.risks.length}</span></h3>
          ${risks || `<p class="muted small">No risks flagged.</p>`}
        </div>
      </div>
    </div>`;

  $("mgr-trend-team").addEventListener("change", (e) => loadTrend(e.target.value));
  loadTrend(teamList[0]);
}

async function loadTrend(team) {
  const box = $("mgr-trend");
  if (!team) { box.innerHTML = ""; return; }
  box.innerHTML = `<div class="skeleton" style="height:110px"></div>`;
  try {
    const d = await api.teamProgress(team);
    // a later selection wins: drop responses for teams no longer selected
    if ($("mgr-trend-team") && $("mgr-trend-team").value !== team) return;
    if (d.suppressed) {
      box.innerHTML = `<p class="muted small">🔒 ${esc(d.note)}</p>`;
      return;
    }
    const trackNote = (d.suppressed_tracks || []).length
      ? `<span class="pill">🔒 ${d.suppressed_tracks.map(esc).join(", ")}: n &lt; ${d.min_group_size} suppressed</span>` : "";
    box.innerHTML = `${trendChart(d.weeks)}
      <div class="wrap" style="margin-top:6px">
        <span class="pill">n=${d.n_learners} learners</span>
        ${(d.by_track || []).filter((t) => !t.suppressed).map((t) =>
          `<span class="pill">${esc(t.track)} n=${t.n}</span>`).join("")}
        ${trackNote}
      </div>`;
  } catch (e) {
    box.innerHTML = errorState(`Team trend unavailable: ${e.message}`);
  }
}
