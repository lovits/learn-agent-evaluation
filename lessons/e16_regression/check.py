"""Apply critical gates to the saved actual integration evidence; no model calls."""

import argparse
import hashlib
import json
from pathlib import Path

from .code import critical_gate

PROJECT = Path(__file__).resolve().parents[2]


def check(evidence, contracts):
    files = {
        name: (evidence / name).read_bytes()
        for name in (
            "composed-evaluation.json",
            "denial-evaluation.json",
            "boundary-evaluation.json",
            "context-gate.json",
            "native-metrics-v2.json",
        )
    }
    rows = {name: json.loads(value) for name, value in files.items()}
    contract_bytes = contracts.read_bytes()
    capabilities = json.loads(contract_bytes)["contracts"]
    metrics = rows["native-metrics-v2.json"]
    degraded = next(
        r for r in metrics["tool_results"] if r["id"] == "injected_missing_checkout_read"
    )
    checks = {
        "independent_business_and_native_state": rows["composed-evaluation.json"]["passed"],
        "unapproved_command_rejected_and_files_preserved": rows["denial-evaluation.json"]["passed"],
        "outside_path_rejected_and_files_preserved": rows["boundary-evaluation.json"]["passed"],
        "all_17_declared_contracts_verified": (
            {c["id"] for c in capabilities} == {f"s{i:02}" for i in range(1, 18)}
            and all(c["verified"] is True for c in capabilities)
        ),
        "known_insufficient_review_context_still_rejected": rows["context-gate.json"]["all_passed"]
        is False,
        "native_metric_execution_coverage": (
            metrics["status"] == "returned"
            and metrics["metric_errors"] == 0
            and len(metrics["faithfulness_results"]) == 2
        ),
        "declared_exact_sequence_regression_detected": (
            degraded["scores"]["deep_exact"] == 0 and degraded["scores"]["ragas_strict"] == 0
        ),
    }
    return {
        "origin": "rules_on_saved_actual_evidence_not_a_new_agent_or_judge_run",
        "scope": "Declared teaching contracts and regression outcomes; diagnostic faithfulness scores are not a completion threshold",
        "checks": checks,
        **critical_gate(checks),
        "source_sha256": {name: hashlib.sha256(value).hexdigest() for name, value in files.items()},
        "contracts_sha256": hashlib.sha256(contract_bytes).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=PROJECT / "integrated_agent/evidence")
    parser.add_argument(
        "--contracts", type=Path, default=PROJECT / "references/e16-capability-contracts.json"
    )
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.evidence, args.contracts)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {"passed": result["passed"], "rejected": result["rejected"], "report": str(args.report)}
        )
    )
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
