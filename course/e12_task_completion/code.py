"""The existing Agent repairs a small function; external checks inspect its delivery."""

import argparse
import json
import os
import uuid
from pathlib import Path

from course.e04_scoring.eval import score
from course.e11_tool_quality.code import run_case
from eval_course.judge import JudgeModel
from eval_course.knowledge import PROJECT
from eval_course.records import save

from .eval import DeliveryContract, evidence_sample, inspect_delivery, judge_completion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    cases = [
        json.loads(line)
        for line in Path(__file__).with_name("cases.jsonl").read_text().splitlines()
    ]
    if args.live:
        cases.append(
            {
                **cases[0],
                "id": "live_repair",
                "calls": [],
                "origin": "constructed task; live model decisions",
            }
        )
    report = {"run_id": uuid.uuid4().hex, "conditions": {}}
    model = JudgeModel()
    for case in cases:
        live = case["id"] == "live_repair"
        run = run_case(case, live=live)
        workspace = (
            Path(os.environ.get("WORKSPACES_DIR", PROJECT / "workspaces")) / run["workspace_id"]
        )
        evidence = inspect_delivery(workspace, case["files"]["policy.txt"])
        sample = evidence_sample(run, evidence)
        row = {
            "case": case,
            "run": run,
            "independent_observation": evidence,
            "sample": sample.model_dump(mode="json"),
            "contract": score(DeliveryContract(), sample),
        }
        report["conditions"][case["id"]] = row
        save(report, prefix="e12-suite")
        if args.judge:
            row["native_completion"] = judge_completion(run, model, evidence)
            if case["id"] in {"correct", "claim_only"}:
                row["native_without_observation"] = judge_completion(run, model)
        report["judge_calls"] = model.calls
        save(report, prefix="e12-suite")
    print(save(report, prefix="e12-suite"))
    return int(
        any(
            row["run"]["status"] != "finished"
            or row["contract"]["status"] == "error"
            or row.get("native_completion", {}).get("status") == "error"
            or row.get("native_without_observation", {}).get("status") == "error"
            for row in report["conditions"].values()
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
