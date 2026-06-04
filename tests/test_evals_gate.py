"""The evaluation gates are part of the test suite, so CI fails if grounding or
PII regress — not only when the standalone scorecard is run."""

from pathlib import Path

from evals.run_evals import load_cases, run

GOLD = Path(__file__).resolve().parents[1] / "evals" / "gold_cases.jsonl"


def test_at_least_40_gold_cases():
    assert len(load_cases(GOLD)) >= 40


def test_all_eval_gates_pass():
    report = run(load_cases(GOLD))
    m = report["metrics"]
    assert m["citation_grounding_rate"] == 1.0, m
    assert m["manager_pii_leak_total"] == 0, m
    assert m["agent_routing_accuracy"] >= 0.90, m
    assert m["capacity_fit_pass_rate"] == 1.0, m
    assert m["abstention_correctness"] == 1.0, m
    assert all(report["gates"].values()), report["gates"]
