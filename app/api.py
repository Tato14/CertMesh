"""FastAPI gateway.

Serves the single-page dashboard and exposes the orchestrator over HTTP. The
orchestrator is the same one used by the CLI and evals, so the UI shows exactly
what the agents produce — including the full orchestration trace and citations.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from certmesh.config import load_config
from certmesh.i18n import t
from certmesh.orchestrator import get_orchestrator
from certmesh.schemas import LearningRequest, OrchestrationResult

app = FastAPI(title="CertMesh", version="0.1.0",
              description="Multi-agent certification-management system (Microsoft Agent Framework + Foundry).")

_UI = Path(__file__).parent / "ui"

PRESETS = [
    {"label": "AZ-204 learner (English)", "view": "learner",
     "description": "Full fan-out: curate → plan → engage → assess, all cited.",
     "request": {"view": "learner", "goal": "Help me prepare for AZ-204",
                 "role": "Cloud Platform Engineer"}},
    {"label": "Over-capacity clinician (L-1012)", "view": "learner",
     "description": "Capacity-aware: only 3 focus h/week → schedule spread over more weeks.",
     "request": {"view": "learner", "learner_id": "L-1012",
                 "goal": "I need to pass CLIN-SAFE-2"}},
    {"label": "Strong learner (L-1005)", "view": "learner",
     "description": "Contrast: 14 focus h/week → a much shorter schedule for the same cert family.",
     "request": {"view": "learner", "learner_id": "L-1005", "goal": "AZ-204 readiness"}},
    {"label": "Out-of-corpus (AWS)", "view": "learner",
     "description": "Safety: certification outside the approved KB → grounded abstain.",
     "request": {"view": "learner", "goal": "I want the AWS Solutions Architect certification"}},
    {"label": "Catalan input", "view": "learner",
     "description": "Responds in the learner's language (ca) while citing English sources.",
     "request": {"view": "learner", "goal": "Vull preparar el certificat AZ-204, què necessito?"}},
    {"label": "Manager view (all teams)", "view": "manager",
     "description": "Aggregate, PII-safe readiness heatmap + risk flags; small groups suppressed.",
     "request": {"view": "manager", "goal": "How are my teams progressing?"}},
]


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (_UI / "index.html").read_text(encoding="utf-8")


@app.post("/api/run", response_model=OrchestrationResult)
def run(req: LearningRequest) -> OrchestrationResult:
    return get_orchestrator().run(req)


@app.get("/api/presets")
def presets() -> dict:
    lang = "en"
    return {"presets": PRESETS, "disclosure": t("ai_disclosure", lang)}


@app.get("/healthz")
def healthz() -> dict:
    orch = get_orchestrator()
    cfg = load_config()
    return {
        "status": "ok",
        "model_backend": orch.model.name,
        "retrieval_backend": orch.foundry.backend,
        "mcp_enabled": cfg.mcp_enabled,
        "foundry_configured": cfg.foundry_configured,
        "search_configured": cfg.search_configured,
    }
