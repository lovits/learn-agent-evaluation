"""Offline independent verification: task state, trace contract and SDK construction."""

import argparse
import json
import os
from pathlib import Path

from eval_course.records import report_path, save

from .samples import export_samples, restore_samples, trace_errors


def evaluate(report, criteria, workspace):
    checks = {
        "finished": report["status"] == "finished",
        "trace_contract": not trace_errors(report),
    }
    tools = [e for e in report["events"] if e["type"] == "tool"]
    for index, rule in enumerate(criteria["tools"]):
        checks[f"tool_{index}"] = any(
            e["call"]["name"] == rule["name"]
            and e["result"]["status"] == rule["status"]
            and all(e["result"].get(k) == v for k, v in rule.get("result", {}).items())
            for e in tools
        )
    for name, expected in criteria.get("files", {}).items():
        path = (Path(workspace) / name).resolve()
        checks["file:" + name] = (
            path.is_relative_to(Path(workspace).resolve())
            and path.is_file()
            and path.read_text() == expected
        )
    if criteria.get("tool_count") is not None:
        checks["tool_count"] = len(tools) == criteria["tool_count"]
    samples, error = None, None
    try:
        samples = export_samples(report, criteria.get("reference"))
        restore_samples(json.loads(json.dumps(samples)))
        checks["native_sdk_samples"] = True
    except (ValueError, TypeError, KeyError) as exc:
        checks["native_sdk_samples"], error = False, str(exc)
    return {
        "run_id": report["run_id"],
        "case_id": report["case_id"],
        "passed": all(checks.values()),
        "checks": checks,
        "trace_errors": trace_errors(report),
        "samples": samples,
        "adapter_error": error,
        "not_scored": ["最终回答语义质量", "工具选择最优性"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    path = report_path(f"e02-{args.run_id}.json")
    report = json.loads(path.read_text())
    if report["run_id"] != args.run_id:
        raise ValueError("Run ID mismatch")
    criteria_path = Path(os.environ.get("E02_CRITERIA_FILE", "/verification/e02.json"))
    criteria = json.loads(criteria_path.read_text())[report["case_id"]]
    workspace = Path(os.environ["WORKSPACES_DIR"]) / args.run_id
    grade = evaluate(report, criteria, workspace)
    save(grade, prefix="grade-e02")
    print(json.dumps({"run_id": args.run_id, "passed": grade["passed"], "checks": grade["checks"]}))
    return 0 if grade["passed"] else 1
