"""Offline acceptance of a candidate-data pipeline, not an Agent performance score."""

import json
import os
from collections import Counter
from pathlib import Path

from .dataset import FAMILY_SPLITS, audit, digest, question_key


def evaluate(report):
    documents = {d["id"]: d for d in report["documents"]}
    candidates = report["candidates"]
    verdicts = {r["id"]: r["automated_review"] for r in candidates}
    recomputed = audit(candidates, documents, verdicts)
    eligible = [r for r in recomputed if r["eligible_for_human_review"]]
    by_id = {r["id"]: r for r in recomputed}
    checks = {
        "native_generation_and_review_no_errors": not report["errors"],
        "both_native_generators": bool(report["native"].get("DeepEval"))
        and len(report["native"].get("Ragas", {}).get("samples", [])) == 2,
        "generation_and_review_called_models": bool(report["generator_calls"])
        and bool(report["review_calls"]),
        "evidence_text_hashes": all(digest(d["text"]) == d["sha256"] for d in documents.values()),
        "duplicate_rejected": "duplicate_question" in by_id["injected-duplicate"]["errors"],
        "wrong_reference_rejected": "reference_not_supported"
        in by_id["injected-wrong-reference"]["errors"],
        "single_and_multi_hop_reviewed": {"single_hop", "multi_hop"}
        <= {r["query_type"] for r in eligible},
        "unanswerable_candidate": any(r["answerable"] is False for r in eligible),
        "programming_acceptance_contract": any(r.get("acceptance_contract") for r in eligible),
        "all_three_splits": {"development", "calibration", "holdout"}
        == {r["split"] for r in eligible},
        "no_normalized_duplicates_in_eligible": len({question_key(r["question"]) for r in eligible})
        == len(eligible),
        "families_not_crossing_splits": all(
            r["split"] == FAMILY_SPLITS[r["family"]] for r in eligible
        ),
        "no_invented_agent_run_or_human_approval": report["agent_new_execution"] is False
        and report["human_approved_count"] == report["agent_executed_candidate_count"] == 0
        and all(r.get("actual_output") is None for r in candidates)
        and all(r["review_state"] == "pending_human" for r in eligible),
        "reported_audit_matches_recomputed": [r["errors"] for r in candidates]
        == [r["errors"] for r in recomputed],
    }
    return {
        "lesson": "e08",
        "passed": all(checks.values()),
        "checks": checks,
        "candidate_count": len(candidates),
        "eligible_pending_human": len(eligible),
        "quarantined": len(candidates) - len(eligible),
        "eligible_by_split": dict(Counter(r["split"] for r in eligible)),
        "eligible_by_query_type": dict(Counter(r["query_type"] for r in eligible)),
        "human_approved": 0,
        "agent_benchmark_accuracy": None,
        "scope": "Small teaching dataset pipeline; automated support judgments need human review; public-seed splits are not blind evaluation.",
    }


def main():
    root = Path(os.environ.get("RUNS_DIR", "runs"))
    source = root / "e08-dataset.json"
    report = json.loads(source.read_text())
    grade = evaluate(report)
    grade["source_report_sha256"] = digest(source.read_text())
    target = root / "e08-dataset-grade.json"
    target.write_text(json.dumps(grade, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(grade, ensure_ascii=False, indent=2))
    return int(not grade["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
