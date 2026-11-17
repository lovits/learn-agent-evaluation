"""Freeze candidates, inspect judge errors, then check equivalent variants and order."""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

from course.e04_scoring.eval import score
from eval_course.judge import JudgeModel
from eval_course.records import save

from .eval import development_examples, metric_for, pair_metric, reconcile, sample_for, summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    path = Path(__file__).with_name("cases.jsonl")
    cases = [json.loads(line) for line in path.read_text().splitlines()]
    groups = {
        split: {c["family"] for c in cases if c["split"] == split} for split in ["dev", "holdout"]
    }
    if groups["dev"] & groups["holdout"]:
        raise ValueError("Task families must not cross development and holdout")
    examples = development_examples(cases)
    model = JudgeModel()
    report = {
        "run_id": uuid.uuid4().hex,
        "mode": "native_judge" if args.judge else "constructed_score_fixture",
        "cases_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "annotation_demo": {
            "origin": "constructed label pairs, not a human annotation study",
            "agreement": reconcile(True, True),
            "unresolved": reconcile(True, False),
            "adjudicated": reconcile(True, False, False),
        },
        "examples": examples,
        "prompt_specs": {},
        "versions": {},
    }
    versions = ["baseline", "revised"] if args.judge else ["fixture"]
    for version in versions:
        rows = []
        report["versions"][version] = {"rows": rows}
        metric = metric_for(version, model, examples) if args.judge else None
        if metric:
            report["prompt_specs"][version] = {
                "evaluation_steps": metric.evaluation_steps,
                "rubric": [r.model_dump(mode="json") for r in metric.rubric],
                "threshold": metric.threshold,
            }
        for case in cases:
            sample = sample_for(case)
            value = case["fixture_score"]
            result = (
                score(metric, sample)
                if metric
                else {
                    "status": "ok" if value is not None else "error",
                    "score": value,
                    "passed": value >= 1.0 if value is not None else None,
                    "reason": "Constructed score for aggregation practice; not a model verdict",
                }
            )
            rows.append({"case": case, "sample": sample.model_dump(mode="json"), "result": result})
            report["judge_calls"] = model.calls
            save(report, prefix="e14-suite")
        report["versions"][version]["summary"] = {
            split: summarize([r for r in rows if r["case"]["split"] == split])
            for split in ["dev", "holdout"]
        }
    if args.judge:
        good = next(c for c in cases if c["id"] == "boreal_short")
        bad = next(c for c in cases if c["id"] == "boreal_bad_gate")
        report["position_pairs"] = []
        for a, b in [(good, bad), (bad, good)]:
            sample = sample_for(a)
            sample.actual_output = (
                "Candidate A:\n" + a["actual_output"] + "\nCandidate B:\n" + b["actual_output"]
            )
            result = score(pair_metric(model), sample)
            winner = (
                (a if result["score"] == 1 else b)["id"]
                if result["status"] == "ok" and result["score"] in (0, 1)
                else None
            )
            report["position_pairs"].append(
                {
                    "A": a["id"],
                    "B": b["id"],
                    "sample": sample.model_dump(mode="json"),
                    "result": result,
                    "winner": winner,
                }
            )
            report["judge_calls"] = model.calls
            save(report, prefix="e14-suite")
    print(save(report, prefix="e14-suite"))
    return int(
        args.judge
        and (
            any(
                r["result"]["status"] == "error"
                for v in report["versions"].values()
                for r in v["rows"]
            )
            or any(p["winner"] is None for p in report["position_pairs"])
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
