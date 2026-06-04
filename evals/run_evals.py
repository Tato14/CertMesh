"""Evaluation scorecard runner + CI gate.

Runs every gold case through the orchestrator, scores it with the local
evaluators, prints a scorecard and writes ``evals/_last_scorecard.json``. Exits
non-zero (failing CI) if any hard gate is violated:

  * citation grounding rate (curator + assessment)  == 1.0
  * manager-insight PII-leak total                   == 0
  * agent-routing accuracy                           >= 0.90
  * plan capacity-fit pass rate                      == 1.0
  * abstention correctness                           == 1.0

Usage:  python -m evals.run_evals  [path/to/gold_cases.jsonl]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from certmesh.orchestrator import get_orchestrator
from certmesh.schemas import LearningRequest

from .evaluators import EVALUATORS

_HERE = Path(__file__).resolve().parent


def load_cases(path: Path) -> list[dict]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def run(cases: list[dict]) -> dict:
    orch = get_orchestrator()
    rows = []
    for case in cases:
        req = LearningRequest(request_id=case["id"], **case["input"])
        res = orch.run(req)
        evaluator = EVALUATORS[case["kind"]]
        detail = evaluator(res, case.get("expect", {}))
        rows.append({"id": case["id"], "kind": case["kind"],
                     "pass": detail["pass"], "detail": detail,
                     "confidence": res.confidence, "abstained": res.abstained})
    return aggregate(rows)


def aggregate(rows: list[dict]) -> dict:
    by_kind: dict[str, list[dict]] = {}
    for r in rows:
        by_kind.setdefault(r["kind"], []).append(r)

    def rate(kind: str) -> float:
        rs = by_kind.get(kind, [])
        return sum(1 for r in rs if r["pass"]) / len(rs) if rs else 1.0

    # citation grounding: pooled supported/checked across grounding + assessment
    g_checked = g_supported = 0
    for kind in ("grounding", "assessment_grounding"):
        for r in by_kind.get(kind, []):
            g_checked += r["detail"].get("checked", 0)
            g_supported += r["detail"].get("supported", 0)
    citation_grounding = (g_supported / g_checked) if g_checked else 1.0

    pii_total = sum(r["detail"].get("pii_leak", 0) for r in by_kind.get("pii", []))

    # calibration: high-confidence answers should be grounded; low-confidence abstains.
    high = [r for r in rows if r["confidence"] >= 0.5]
    low = [r for r in rows if r["confidence"] < 0.5]
    high_correct = sum(1 for r in high if r["pass"]) / len(high) if high else 1.0
    low_abstained = sum(1 for r in low if r["abstained"]) / len(low) if low else 1.0

    metrics = {
        "total_cases": len(rows),
        "overall_pass_rate": round(sum(1 for r in rows if r["pass"]) / len(rows), 4),
        "agent_routing_accuracy": round(rate("routing"), 4),
        "citation_grounding_rate": round(citation_grounding, 4),
        "assessment_grounding_pass_rate": round(rate("assessment_grounding"), 4),
        "manager_pii_leak_total": pii_total,
        "manager_pii_leak_rate": round(pii_total / max(len(by_kind.get("pii", [])), 1), 4),
        "capacity_fit_pass_rate": round(rate("capacity"), 4),
        "assessment_scoring_accuracy": round(rate("readiness"), 4),
        "abstention_correctness": round(rate("abstain"), 4),
        "language_accuracy": round(rate("language"), 4),
        "calibration_high_conf_correct": round(high_correct, 4),
        "calibration_low_conf_abstained": round(low_abstained, 4),
    }
    gates = {
        "citation_grounding==1.0": citation_grounding >= 1.0,
        "manager_pii_leak==0": pii_total == 0,
        "routing>=0.90": metrics["agent_routing_accuracy"] >= 0.90,
        "capacity_fit==1.0": metrics["capacity_fit_pass_rate"] >= 1.0,
        "abstention==1.0": metrics["abstention_correctness"] >= 1.0,
    }
    return {"metrics": metrics, "gates": gates, "rows": rows}


def print_scorecard(report: dict) -> None:
    m = report["metrics"]
    print("\n" + "=" * 66)
    print("  CertMesh — Evaluation Scorecard")
    print("=" * 66)
    order = [
        ("Total cases", "total_cases", "{}"),
        ("Overall pass rate", "overall_pass_rate", "{:.1%}"),
        ("Agent-routing accuracy", "agent_routing_accuracy", "{:.1%}"),
        ("Citation grounding rate", "citation_grounding_rate", "{:.1%}"),
        ("Assessment grounding pass", "assessment_grounding_pass_rate", "{:.1%}"),
        ("Manager PII-leak total", "manager_pii_leak_total", "{}"),
        ("Capacity-fit pass rate", "capacity_fit_pass_rate", "{:.1%}"),
        ("Assessment scoring accuracy", "assessment_scoring_accuracy", "{:.1%}"),
        ("Abstention correctness", "abstention_correctness", "{:.1%}"),
        ("Language accuracy", "language_accuracy", "{:.1%}"),
        ("Calibration (hi-conf correct)", "calibration_high_conf_correct", "{:.1%}"),
        ("Calibration (lo-conf abstain)", "calibration_low_conf_abstained", "{:.1%}"),
    ]
    for label, key, fmt in order:
        print(f"  {label:<32} {fmt.format(m[key])}")
    print("-" * 66)
    for gate, ok in report["gates"].items():
        print(f"  [{'PASS' if ok else 'FAIL'}]  {gate}")
    print("=" * 66)
    fails = [r for r in report["rows"] if not r["pass"]]
    if fails:
        print(f"  {len(fails)} failing case(s):")
        for r in fails[:20]:
            print(f"    - {r['id']} ({r['kind']}): {r['detail']}")
    print()


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    path = Path(argv[0]) if argv else _HERE / "gold_cases.jsonl"
    report = run(load_cases(path))
    print_scorecard(report)
    (_HERE / "_last_scorecard.json").write_text(
        json.dumps(report["metrics"], indent=2), encoding="utf-8")
    passed = all(report["gates"].values())
    print("RESULT:", "ALL GATES PASSED ✅" if passed else "GATE FAILURE ❌")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
