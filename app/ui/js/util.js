// Shared helpers: escaping, formatting, citation chips, motion, downloads.

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));

export const pct = (x) => `${Math.round((x ?? 0) * 100)}%`;

export const reducedMotion = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export const sleep = (ms) => new Promise((r) => setTimeout(r, reducedMotion() ? 0 : ms));

export function badge(band, label) {
  return `<span class="badge ${esc(band)}">${esc(label ?? String(band).replace("_", " "))}</span>`;
}

/* Citation registry: numbers chips consistently within one render pass and
   feeds the Sources card. */
export function citeCollector() {
  const cites = [];
  function chip(c) {
    if (!c) return "";
    let i = cites.findIndex((x) => x.source_id === c.source_id && x.snippet === c.snippet);
    if (i < 0) { cites.push(c); i = cites.length - 1; }
    const cls = c.kind === "ms_learn" ? "cite learn" : "cite";
    const tip = `${c.title}\n“${c.snippet}”\n— ${c.locator}`;
    const inner = `<span class="n">[${i + 1}]</span> ${esc(c.title)}`;
    if (c.url) {
      return `<a class="${cls}" href="${esc(c.url)}" target="_blank" rel="noopener" title="${esc(tip)}">${inner} ↗</a>`;
    }
    // Foundry IQ chips open the evidence inspector (verbatim source + highlight).
    return `<button type="button" class="cite" data-source-id="${esc(c.source_id)}"
      data-snippet="${esc(c.snippet)}" title="${esc(tip)}\n(click to inspect the verbatim source)">${inner} ⌕</button>`;
  }
  return { chip, list: () => cites };
}

/* Highlight `snippet` inside `text`, tolerant of whitespace/case differences —
   the same normalisation the critic's supports() check applies. */
export function highlightSnippet(text, snippet) {
  if (!snippet) return esc(text);
  const pattern = snippet.trim().split(/\s+/).map((w) =>
    w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("\\s+");
  try {
    const m = text.match(new RegExp(pattern, "i"));
    if (!m) return esc(text);
    const start = m.index, end = m.index + m[0].length;
    return `${esc(text.slice(0, start))}<mark>${esc(text.slice(start, end))}</mark>${esc(text.slice(end))}`;
  } catch { return esc(text); }
}

export function sourcesCard(cites) {
  if (!cites.length) return "";
  const items = cites.map((c, i) => `
    <div class="resource">
      <div class="top"><b><span class="mono">[${i + 1}]</span> ${esc(c.title)}</b>
        <span class="pill">${c.kind === "ms_learn" ? "Microsoft Learn" : "Foundry IQ"}</span></div>
      <div class="muted small">“${esc(c.snippet)}”</div>
      <div class="muted small mono">${esc(c.locator)}${c.url ? ` · <a href="${esc(c.url)}" target="_blank" rel="noopener">open ↗</a>` : ""}</div>
    </div>`).join("");
  return `<div class="card fade-up"><div class="card-title">Sources — grounded citations</div>${items}</div>`;
}

export function emptyState(glyph, title, body, actionsHtml = "") {
  return `<div class="empty-state"><div class="glyph">${glyph}</div>
    <h3>${esc(title)}</h3><p>${body}</p>${actionsHtml}</div>`;
}

export function errorState(msg) {
  return `<div class="error-state"><b>Something went wrong.</b> ${esc(msg)}</div>`;
}

export function skeletonCard(titleText, lines = 3) {
  const rows = Array.from({ length: lines }, (_, i) =>
    `<div class="skeleton" style="height:13px;margin-top:10px;width:${88 - i * 14}%"></div>`).join("");
  return `<div class="card"><div class="card-title">${esc(titleText)}</div>
    <div class="skeleton" style="height:15px;width:55%"></div>${rows}</div>`;
}

export function download(filename, text, mime = "text/plain") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: mime }));
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 250);
}

export const trackColor = (track) => ({
  technical: "var(--track-technical)",
  clinical: "var(--track-clinical)",
  compliance: "var(--track-compliance)",
  security: "var(--track-security)",
}[track] || "var(--muted)");

export const $ = (id) => document.getElementById(id);
