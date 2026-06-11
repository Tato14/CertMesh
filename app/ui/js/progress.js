// Progress & feedback (Feature D): dependency-free inline-SVG charts.
// Used by the learner view (individual trend) and the manager view (team trend).

import { esc, pct } from "./util.js";

/* Practice-score line + threshold reference + milestone ticks + weekly-hours
   bars underneath. viewBox scales to the container. */
export function progressChart(weeks, threshold, { width = 560, height = 210 } = {}) {
  if (!weeks?.length) return "";
  const padL = 34, padR = 12, padT = 10;
  const lineH = 130, barTop = padT + lineH + 18, barH = 36;
  const scores = weeks.map((w) => w.practice_score);
  const lo = Math.min(...scores, threshold) - 0.06;
  const hi = Math.max(...scores, threshold) + 0.06;
  const x = (i) => padL + (i / (weeks.length - 1)) * (width - padL - padR);
  const y = (v) => padT + (1 - (v - lo) / (hi - lo)) * lineH;

  const pts = weeks.map((w, i) => `${x(i).toFixed(1)},${y(w.practice_score).toFixed(1)}`);
  const area = `M${pts[0]} L${pts.join(" L")} L${x(weeks.length - 1)},${padT + lineH} L${x(0)},${padT + lineH} Z`;

  // milestone ticks where the cumulative count increments
  const ticks = weeks.filter((w, i) => i > 0 && w.milestones_completed > weeks[i - 1].milestones_completed)
    .map((w) => `<circle class="milestone" cx="${x(weeks.indexOf(w)).toFixed(1)}" cy="${y(w.practice_score).toFixed(1)}" r="3.5">
       <title>milestone ${w.milestones_completed} completed (week ${w.week})</title></circle>`);

  // weekly hours (delta of the cumulative series)
  const deltas = weeks.map((w, i) => i === 0 ? w.hours_studied_cumulative
    : w.hours_studied_cumulative - weeks[i - 1].hours_studied_cumulative);
  const maxD = Math.max(...deltas, 1);
  const bw = Math.min(22, (width - padL - padR) / weeks.length - 6);
  const bars = weeks.map((w, i) => {
    const h = (deltas[i] / maxD) * barH;
    return `<rect class="bar" x="${(x(i) - bw / 2).toFixed(1)}" y="${(barTop + barH - h).toFixed(1)}"
      width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="2"><title>week ${w.week}: ${deltas[i].toFixed(1)}h studied</title></rect>`;
  });

  const thY = y(threshold).toFixed(1);
  const labels = weeks.map((w, i) => `<text class="tick-label" x="${x(i).toFixed(1)}" y="${height - 4}" text-anchor="middle">W${w.week}</text>`);

  return `<div class="chart"><svg viewBox="0 0 ${width} ${height}" role="img"
      aria-label="Practice score per week against the pass threshold, with hours studied bars">
    <line class="gridline" x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + lineH}"></line>
    <line class="threshold" x1="${padL}" y1="${thY}" x2="${width - padR}" y2="${thY}"></line>
    <text class="tick-label" x="${padL - 4}" y="${thY}" text-anchor="end" dominant-baseline="middle">${pct(threshold)}</text>
    <text class="tick-label" x="${padL - 4}" y="${y(scores[0]).toFixed(1)}" text-anchor="end" dominant-baseline="middle">${pct(scores[0])}</text>
    <path class="area" d="${area}"></path>
    <polyline class="line" points="${pts.join(" ")}"></polyline>
    ${weeks.map((w, i) => `<circle class="dot" cx="${x(i).toFixed(1)}" cy="${y(w.practice_score).toFixed(1)}" r="2.6">
       <title>week ${w.week}: ${pct(w.practice_score)} · ${w.hours_studied_cumulative}h total</title></circle>`).join("")}
    ${ticks.join("")}
    ${bars.join("")}
    ${labels.join("")}
  </svg></div>`;
}

/* Compact team trend (avg practice score per week). */
export function trendChart(weeks, { width = 460, height = 120, threshold = null } = {}) {
  if (!weeks?.length) return "";
  const padL = 34, padR = 10, padT = 8, padB = 18;
  const vals = weeks.map((w) => w.avg_practice_score);
  const lo = Math.min(...vals, threshold ?? 1) - 0.04;
  const hi = Math.max(...vals, threshold ?? 0) + 0.04;
  const x = (i) => padL + (i / (weeks.length - 1)) * (width - padL - padR);
  const y = (v) => padT + (1 - (v - lo) / (hi - lo)) * (height - padT - padB);
  const pts = weeks.map((w, i) => `${x(i).toFixed(1)},${y(w.avg_practice_score).toFixed(1)}`);
  const th = threshold != null
    ? `<line class="threshold" x1="${padL}" y1="${y(threshold).toFixed(1)}" x2="${width - padR}" y2="${y(threshold).toFixed(1)}"></line>
       <text class="tick-label" x="${padL - 4}" y="${y(threshold).toFixed(1)}" text-anchor="end" dominant-baseline="middle">${pct(threshold)}</text>`
    : "";
  return `<div class="chart"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Team average practice score per week">
    ${th}
    <polyline class="line" points="${pts.join(" ")}"></polyline>
    ${weeks.map((w, i) => `<circle class="dot" cx="${x(i).toFixed(1)}" cy="${y(w.avg_practice_score).toFixed(1)}" r="2.4">
      <title>week ${w.week}: avg ${pct(w.avg_practice_score)}</title></circle>`).join("")}
    <text class="tick-label" x="${x(0)}" y="${height - 4}" text-anchor="middle">W${weeks[0].week}</text>
    <text class="tick-label" x="${x(weeks.length - 1)}" y="${height - 4}" text-anchor="middle">W${weeks[weeks.length - 1].week}</text>
  </svg></div>`;
}

/* The learner-tab progress card body. */
export function individualCard(data) {
  const last = data.weeks[data.weeks.length - 1];
  return `
    <div class="kpis" style="margin-bottom:12px">
      <div class="kpi"><div class="k">practice score</div><div class="v">${pct(last.practice_score)}</div></div>
      <div class="kpi"><div class="k">pass threshold</div><div class="v">${pct(data.threshold)}</div></div>
      <div class="kpi"><div class="k">hours studied</div><div class="v">${last.hours_studied_cumulative}h</div></div>
      <div class="kpi"><div class="k">trend</div><div class="v">${data.trend_per_week >= 0 ? "+" : ""}${(data.trend_per_week * 100).toFixed(1)}<span class="muted small"> pts/wk</span></div></div>
    </div>
    ${progressChart(data.weeks, data.threshold)}
    <div class="subpanel" style="margin-top:10px">${esc(data.feedback)}</div>`;
}
