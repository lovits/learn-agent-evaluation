"""Execute controlled tool traces and the existing live Agent without new tools."""

import argparse
import copy
import json
import uuid
from pathlib import Path

from course.e02_samples.code import agent_loop
from course.e02_samples.tools import TOOLS
from eval_course.judge import JudgeModel
from eval_course.records import save
from eval_course.runtime import call_model, prepare_workspace

from .eval import judge_arguments, sample_for, tool_scores


def run_case(case, live=False):
    workspace_id = uuid.uuid4().hex
    workspace = prepare_workspace({"files": case["files"]}, workspace_id)
    if case.get("target_is_directory"):
        (workspace / "delivery.txt").mkdir()
    scripted = iter(
        [
            {
                "reply": {
                    "answer": "" if case["calls"] else "已完成。",
                    "tool_calls": [
                        {"name": c["name"], "arguments_json": json.dumps(c["arguments"])}
                        for c in case["calls"]
                    ],
                }
            },
            {"reply": {"answer": "已完成。", "tool_calls": []}},
        ]
    )
    inputs, responses = [], []

    def next_response(messages):
        response = call_model(messages, tools=TOOLS) if live else next(scripted)
        inputs.append(copy.deepcopy(messages))
        responses.append(response)
        return response

    run = agent_loop(case["task"], workspace, model=next_response)
    target = workspace / case["target"]
    run.update(
        task=case["task"],
        workspace_id=workspace_id,
        origin="live_model" if live else "scripted_decisions_real_tool_execution",
        model_inputs=inputs,
        responses=responses,
        artifact={
            "path": case["target"],
            "is_file": target.is_file(),
            "content": target.read_text() if target.is_file() else None,
        },
    )
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    cases = [
        json.loads(line)
        for line in Path(__file__).with_name("cases.jsonl").read_text().splitlines()
    ]
    report = {"run_id": uuid.uuid4().hex, "conditions": {}}
    model = JudgeModel()
    for case in cases + (
        [
            {**cases[0], "id": "live_copy"},
            {**next(c for c in cases if c["id"] == "permission_recovery"), "id": "live_permission"},
        ]
        if args.live
        else []
    ):
        if case["id"].startswith("live_"):
            case = {
                **case,
                "calls": [],
                "origin": "constructed task template; live model decisions",
            }
        run = run_case(case, live=case["id"].startswith("live_"))
        sample = sample_for(run, case["expected_calls"])
        row = {
            "case": case,
            "run": run,
            "sample": sample.model_dump(mode="json"),
            "native_tools": tool_scores(sample, model),
        }
        report["conditions"][case["id"]] = row
        save(report, prefix="e11-suite")
        if args.judge:
            row["native_arguments"] = judge_arguments(sample, model)
        report["judge_calls"] = model.calls
        save(report, prefix="e11-suite")
    print(save(report, prefix="e11-suite"))
    return int(
        any(
            row["run"]["status"] != "finished"
            or any(value["status"] == "error" for value in row["native_tools"].values())
            or row.get("native_arguments", {}).get("status") == "error"
            for row in report["conditions"].values()
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
