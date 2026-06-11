// Minimal shared state + event bus between view modules.

export const store = {
  presets: [],
  health: null,
  graphData: null,      // /api/graph payload, fetched lazily, shared by views
  lastRequest: null,
  lastResult: null,

  _listeners: new Map(),
  on(evt, fn) {
    if (!this._listeners.has(evt)) this._listeners.set(evt, []);
    this._listeners.get(evt).push(fn);
  },
  emit(evt, data) {
    (this._listeners.get(evt) || []).forEach((fn) => {
      try { fn(data); } catch (e) { console.error(`listener for ${evt} failed`, e); }
    });
  },
};
