"""Keep original history separate from the context actually sent to the Agent."""

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

from .eval import check_delivery, conversation_sample, conversational_scores


def context_for(scenario, mode):
    if mode == "full":
        return [{"role": t["role"], "content": t["content"]} for t in scenario["history"]]
    if mode == "tail":
        return []
    return [
        {
            "role": "user",
            "content": "Conversation summary (reference only):\n" + scenario["summaries"][mode],
        }
    ]


def run_case(scenario, case, live=False):
    workspace_id = uuid.uuid4().hex
    workspace = prepare_workspace(
        {
            "files": {
                "policy.txt": scenario["policy"],
                "conversation.json": json.dumps(
                    [{k: t[k] for k in ("id", "role", "content")} for t in scenario["history"]],
                    ensure_ascii=False,
                    indent=2,
                ),
            }
        },
        workspace_id,
    )
    prefix = context_for(scenario, case["context"])
    scripted = iter(
        [
            {
                "reply": {
                    "answer": "",
                    "tool_calls": [
                        {"name": c["name"], "arguments_json": json.dumps(c["arguments"])}
                        for c in batch
                    ],
                }
            }
            for batch in case["steps"]
        ]
        + [{"reply": {"answer": case["final_answer"], "tool_calls": []}}]
    )
    inputs, responses = [], []

    def next_response(messages):
        visible = copy.deepcopy(prefix + messages)
        inputs.append(visible)
        response = call_model(visible, tools=TOOLS) if live else next(scripted)
        responses.append(response)
        return response

    run = agent_loop(scenario["current"], workspace, model=next_response)
    run.update(
        task=scenario["current"],
        workspace_id=workspace_id,
        model_inputs=inputs,
        responses=responses,
        context_mode=case["context"],
        origin="live_model" if live else "scripted_decisions_real_tool_execution",
    )
    return run, workspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    folder = Path(__file__).parent
    scenario = json.loads((folder / "scenario.json").read_text())
    cases = [json.loads(line) for line in (folder / "cases.jsonl").read_text().splitlines()]
    if args.live:
        cases += [
            {
                "id": "live_" + mode,
                "context": mode,
                "steps": [],
                "final_answer": "",
                "judge": mode == "archive",
                "origin": "constructed history; live final execution",
            }
            for mode in ["full", "tail", "archive"]
        ]
    model = JudgeModel()
    report = {"run_id": uuid.uuid4().hex, "scenario": scenario, "conditions": {}}
    for case in cases:
        run, workspace = run_case(scenario, case, live=case["id"].startswith("live_"))
        sample = conversation_sample(run, scenario)
        row = {
            "case": case,
            "run": run,
            "delivery": check_delivery(run, workspace, scenario),
            "sample": sample.model_dump(mode="json"),
        }
        report["conditions"][case["id"]] = row
        save(report, prefix="e13-suite")
        if args.judge and case["judge"]:
            row["native_conversation"] = conversational_scores(sample, model)
        report["judge_calls"] = model.calls
        save(report, prefix="e13-suite")
    print(save(report, prefix="e13-suite"))
    return int(
        any(
            row["run"]["status"] != "finished"
            or any(v["status"] == "error" for v in row.get("native_conversation", {}).values())
            for row in report["conditions"].values()
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
