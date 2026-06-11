// Capacity calendar (Feature B): a simulated Outlook-style week rendered from
// synthetic Work IQ signals — meetings muted, focus time soft green, the
// Engagement Agent's proposed study slots as first-class accented events.
// Includes a client-side .ics export ([SYNTHETIC DEMO]) and an L-1012 vs L-1005
// contrast mode.

import { api } from "./api.js";
import { store } from "./state.js";
import { $, download, emptyState, errorState, esc, pct } from "./util.js";

const HOUR_PX = 46;
let activated = false;
let mode = { kind: "single", ids: ["L-1012"] };
const cache = new Map();

store.on("calendar-show", (id) => { mode = { kind: "single", ids: [id] }; renderMode(); });

export async function activate() {
  if (activated) return;        // keep current mode when revisiting the tab
  activated = true;
  await renderMode();
}

export async function showCompare(ids) {
  mode = { kind: "compare", ids };
  activated = true;
  await renderMode();
}

async function fetchCal(id) {
  if (!cache.has(id)) cache.set(id, await api.calendar(id));
  return cache.get(id);
}

async function renderMode() {
  const root = $("calendar-root");
  root.innerHTML = `<div class="muted small">Simulating week…</div>`;
  try {
    const learners = (store.graphData || (store.graphData = await api.graph())).learners;
    const cals = await Promise.all(mode.ids.map(fetchCal));
    root.innerHTML = `
      <div class="cal-toolbar">
        <div class="field"><label for="cal-learner">Learner</label>
          <select id="cal-learner">${learners.map((l) =>
            `<option value="${esc(l.learner_id)}" ${mode.kind === "single" && l.learner_id === mode.ids[0] ? "selected" : ""}>${esc(l.learner_id)} · ${esc(l.role)}</option>`).join("")}</select></div>
        <button class="btn-secondary btn-sm" id="cal-compare-btn" aria-pressed="${mode.kind === "compare"}">
          ${mode.kind === "compare" ? "✓ " : ""}Contrast: L-1012 vs L-1005</button>
        <span class="muted small">meetings <span class="pill" style="background:var(--cal-meeting)">&nbsp;&nbsp;</span>
          · focus <span class="pill" style="background:var(--cal-focus)">&nbsp;&nbsp;</span>
          · proposed study <span class="pill" style="background:var(--cal-study);border-color:var(--cal-study-line)">&nbsp;&nbsp;</span></span>
      </div>
      ${mode.kind === "compare"
        ? `<div class="cal-compare">${cals.map((c) => pane(c, true)).join("")}</div>`
        : `<div class="cal-single">${pane(cals[0], false)}<div class="cal-stats">${stats(cals[0])}</div></div>`}`;
    bind();
  } catch (e) {
    root.innerHTML = errorState(`Could not simulate the calendar: ${e.message}`);
    activated = false;
  }
}

function bind() {
  $("cal-learner")?.addEventListener("change", (e) => {
    mode = { kind: "single", ids: [e.target.value] };
    renderMode();
  });
  $("cal-compare-btn")?.addEventListener("click", () => {
    mode = mode.kind === "compare" ? { kind: "single", ids: ["L-1012"] } : { kind: "compare", ids: ["L-1012", "L-1005"] };
    renderMode();
  });
  document.querySelectorAll("[data-ics]").forEach((b) =>
    b.addEventListener("click", () => exportIcs(cache.get(b.dataset.ics))));
}

/* ── one week grid ──────────────────────────────────────────────────────── */

const toMin = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };

function pane(cal, compact) {
  const startH = 8;
  const endH = Math.max(18, ...cal.blocks.map((b) => Math.ceil(toMin(b.end) / 60)));
  const colH = (endH - startH) * HOUR_PX;
  const gutter = Array.from({ length: endH - startH + 1 }, (_, i) =>
    `<span class="hr" style="top:${i * HOUR_PX}px">${String(startH + i).padStart(2, "0")}:00</span>`).join("");

  const cols = cal.days.map((d) => {
    const blocks = cal.blocks.filter((b) => b.day === d).map((b) => {
      const top = ((toMin(b.start) - startH * 60) / 60) * HOUR_PX;
      const h = ((toMin(b.end) - toMin(b.start)) / 60) * HOUR_PX;
      const why = b.kind === "study"
        ? `Why this slot: ${b.rationale || "fits the learner's preferred rhythm"} · ${cal.engagement.capacity_note}`
        : b.label;
      return `<div class="cal-block ${esc(b.kind)}" style="top:${top}px;height:${Math.max(h - 2, 14)}px"
        title="${esc(why)}">${b.kind === "study" ? esc(b.label) : `<span class="t">${esc(b.label)}</span>`}
        ${h >= 34 ? `<div class="t">${esc(b.start)}–${esc(b.end)}</div>` : ""}</div>`;
    }).join("");
    return `<div class="cal-daycol" style="height:${colH}px;--hour-px:${HOUR_PX}px">${blocks}</div>`;
  }).join("");

  const sig = cal.signal;
  return `<div>
    <div class="cal-head">
      <span class="who mono">${esc(cal.learner_id)}</span>
      <span class="pill">${esc(cal.role)}</span>
      ${cal.certification ? `<span class="pill mono">${esc(cal.certification)}</span>` : ""}
      <span class="pill" title="aggregate Work IQ signal">${sig.meeting_hours_per_week}h meetings · ${sig.focus_hours_per_week}h focus</span>
      <button class="btn-secondary btn-sm" data-ics="${esc(cal.learner_id)}" title="Download the proposed study slots as an iCalendar file">⤓ .ics</button>
    </div>
    ${compact ? `<p class="muted small" style="margin:0 0 8px">${esc(cal.engagement.cadence)}</p>` : ""}
    <div class="cal-grid" style="--hour-px:${HOUR_PX}px">
      <div class="corner"></div>${cal.days.map((d) => `<div class="dayhead">${esc(d)}</div>`).join("")}
      <div class="cal-gutter" style="height:${colH}px">${gutter}</div>
      ${cols}
    </div>
  </div>`;
}

function stats(cal) {
  const e = cal.engagement;
  return `
    <div class="subpanel">
      <h3 style="margin-bottom:8px">Why these slots?</h3>
      <p class="dim small">${esc(e.capacity_note)}</p>
      <p class="dim small">${esc(e.weekly_windows[0]?.rationale || "")}.</p>
      <p class="muted small" style="margin-bottom:0">${esc(e.privacy_note)}</p>
    </div>
    <div class="subpanel">
      <h3 style="margin-bottom:8px">Plan fit</h3>
      <div class="kpis">
        <div class="kpi"><div class="k">cadence</div><div class="v" style="font-size:13px">${esc(e.cadence)}</div></div>
        ${cal.study_plan ? `
          <div class="kpi"><div class="k">plan length</div><div class="v">${cal.study_plan.total_weeks} wks</div></div>
          <div class="kpi"><div class="k">utilisation</div><div class="v">${pct(cal.study_plan.utilisation)}</div></div>` : ""}
      </div>
      <p class="muted small" style="margin:8px 0 0">${esc(e.next_reminder)}</p>
    </div>
    ${emptyStateNote()}`;
}

function emptyStateNote() {
  return `<p class="muted small" style="margin:0">Simulated week generated deterministically from the
    synthetic Work IQ signal — block totals match the aggregate hours; no real tenant, no meeting content.</p>`;
}

/* ── .ics export (client-side, standards-compliant) ─────────────────────── */

const DAY_IDX = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4 };

function nextMonday() {
  const d = new Date();
  d.setDate(d.getDate() + ((8 - d.getDay()) % 7 || 7));
  return d;
}

const icsDate = (d, hhmm) =>
  `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}T${hhmm.replace(":", "")}00`;

// DTSTAMP must be UTC (RFC 5545 §3.8.7.2)
const icsStampUtc = (d) => `${d.toISOString().replace(/[-:]/g, "").slice(0, 15)}Z`;

export function buildIcs(cal) {
  const monday = nextMonday();
  const stamp = icsStampUtc(new Date());
  const events = cal.blocks.filter((b) => b.kind === "study").map((b, i) => {
    const d = new Date(monday);
    d.setDate(d.getDate() + (DAY_IDX[b.day] ?? 0));
    return [
      "BEGIN:VEVENT",
      `UID:certmesh-${cal.learner_id}-${i}@synthetic.demo`,
      `DTSTAMP:${stamp}`,
      `DTSTART:${icsDate(d, b.start)}`,
      `DTEND:${icsDate(d, b.end)}`,
      `SUMMARY:[SYNTHETIC DEMO] ${b.label.replace(/[,;\\]/g, " ")}`,
      `DESCRIPTION:${(b.rationale || "Proposed study slot").replace(/[,;\\]/g, " ")} — generated by CertMesh from synthetic Work IQ signals.`,
      "END:VEVENT",
    ].join("\r\n");
  });
  return ["BEGIN:VCALENDAR", "VERSION:2.0",
    "PRODID:-//CertMesh//Synthetic Demo//EN", "CALSCALE:GREGORIAN",
    ...events, "END:VCALENDAR", ""].join("\r\n");
}

function exportIcs(cal) {
  if (!cal) return;
  download(`certmesh-study-slots-${cal.learner_id}.ics`, buildIcs(cal), "text/calendar");
}
