// Thin fetch layer over the FastAPI gateway.

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const detail = await r.json().then((d) => d.detail).catch(() => r.statusText);
    throw new Error(`${detail || r.statusText} (${r.status})`);
  }
  return r.json();
}

export const api = {
  presets: () => getJSON("/api/presets"),
  health: () => getJSON("/healthz"),
  graph: () => getJSON("/api/graph"),
  calendar: (id) => getJSON(`/api/calendar/${encodeURIComponent(id)}`),
  progress: (id) => getJSON(`/api/progress/${encodeURIComponent(id)}`),
  teamProgress: (id) => getJSON(`/api/progress/team/${encodeURIComponent(id)}`),
  async run(req) {
    const r = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!r.ok) {
      const detail = await r.json().then((d) => JSON.stringify(d.detail)).catch(() => r.statusText);
      throw new Error(`${detail || r.statusText} (${r.status})`);
    }
    return r.json();
  },
};
