"""Foundry evaluation SDK integration.

When ``azure-ai-evaluation`` and a judge model are configured, this exports the
gold cases as a JSONL of (query, context, response) rows and runs the managed
``GroundednessEvaluator`` / ``RelevanceEvaluator`` over the curator + assessment
outputs, optionally logging to the Foundry project. Otherwise it prints how to
enable it and points to the local scorecard.

Verified June 2026 against:
https://learn.microsoft.com/en-us/azure/foundry-classic/how-to/develop/evaluate-sdk
(package ``azure-ai-evaluation``; evaluators ``GroundednessEvaluator``,
``RelevanceEvaluator``; batch entry point ``evaluate(data=..., evaluators=...)``).
The local harness (run_evals.py) is the always-on CI gate; this adds the managed
evaluators when the cloud is available.
"""

from __future__ import annotations

import json
from pathlib import Path

from certmesh.config import load_config
from certmesh.orchestrator import get_orchestrator
from certmesh.schemas import LearningRequest

_HERE = Path(__file__).resolve().parent


def export_eval_rows(out_path: Path | None = None) -> Path:
    """Build a (query, context, response) JSONL for the managed evaluators from
    the curator + assessment grounded outputs."""
    out_path = out_path or (_HERE / "_foundry_eval_rows.jsonl")
    orch = get_orchestrator()
    cases = [json.loads(line) for line in
             (_HERE / "gold_cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for case in cases:
        if case["kind"] not in ("grounding", "assessment_grounding"):
            continue
        res = orch.run(LearningRequest(request_id=case["id"], **case["input"]))
        if case["kind"] == "grounding" and res.curated_path:
            ctx = " ".join(c.snippet for c in res.curated_path.citations)
            rows.append({"query": case["input"].get("goal", ""),
                         "context": ctx, "response": res.curated_path.summary})
        elif case["kind"] == "assessment_grounding" and res.assessment:
            for q in res.assessment.questions:
                rows.append({"query": q.stem, "context": q.citation.snippet,
                             "response": q.explanation})
    out_path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return out_path


def run_foundry_eval() -> dict | None:
    """Run managed Groundedness/Relevance evaluators if the SDK + judge model are
    available; return metrics or None (and print guidance) otherwise."""
    cfg = load_config()
    try:
        from azure.ai.evaluation import (  # type: ignore
            AzureOpenAIModelConfiguration,
            GroundednessEvaluator,
            RelevanceEvaluator,
            evaluate,
        )
    except Exception:
        print("azure-ai-evaluation not installed — run `pip install .[azure]` and set a judge "
              "model to use the managed Foundry evaluators. Local scorecard: evals/run_evals.py")
        return None
    if not cfg.foundry_configured:
        print("No AZURE_AI_PROJECT_ENDPOINT configured — skipping managed evaluation. "
              "Local scorecard remains the CI gate.")
        return None

    data_path = export_eval_rows()
    model_config = AzureOpenAIModelConfiguration(  # pragma: no cover - needs cloud
        azure_endpoint=cfg.project_endpoint,
        azure_deployment=cfg.model_deployment,
        api_key=cfg.api_key or None,
    )
    result = evaluate(  # pragma: no cover - needs cloud
        data=str(data_path),
        evaluators={
            "groundedness": GroundednessEvaluator(model_config),
            "relevance": RelevanceEvaluator(model_config),
        },
        evaluator_config={
            "groundedness": {"column_mapping": {
                "query": "${data.query}", "context": "${data.context}",
                "response": "${data.response}"}},
        },
    )
    print("Foundry evaluation metrics:", result.get("metrics"))
    return result.get("metrics")


if __name__ == "__main__":
    run_foundry_eval()
