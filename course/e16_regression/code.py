"""Compose the existing Agent, TinyRAG and independent evaluation into regression."""

import argparse
import copy
import hashlib
import json
import uuid
from pathlib import Path

from course.e05_knowledge_context.code import TOOLS, run_task
from course.e15_version_comparison.eval import usage_summary
from eval_course.judge import JudgeModel
from eval_course.knowledge import document
from eval_course.records import save
from eval_course.runtime import call_model, prepare_workspace

from .eval import evaluate_run, failure_candidates, gate

REPAIR = "\n最终回复须具体说明计算规则如何修复、空订单与输入保持的处理；准确区分实际检查与未检查，不要只回复已完成。"


def run_case(case, version, live=False, root=None):
    workspace_id = uuid.uuid4().hex
    workspace = prepare_workspace(case, workspace_id)
    responses, inputs = [], []
    prefix = REPAIR if version == "candidate" else ""
    scripted = iter(
        [
            {
                "reply": {
                    "answer": "",
                    "tool_calls": [
                        {
                            "name": "search_knowledge",
                            "arguments_json": json.dumps(
                                {"query": "Atlas billing total_cents unit_cents quantity policy"}
                            ),
                        },
                        {"name": "read_file", "arguments_json": json.dumps({"path": "billing.py"})},
                    ],
                }
            },
            {
                "reply": {
                    "answer": "",
                    "tool_calls": [
                        {
                            "name": "write_file",
                            "arguments_json": json.dumps(
                                {"path": "billing.py", "content": case["fixture_code"]}
                            ),
                        }
                    ],
                }
            },
            {"reply": {"answer": case["fixture_answers"][version], "tool_calls": []}},
        ]
    )

    def next_response(messages):
        visible = copy.deepcopy(messages)
        visible[0]["content"] += prefix
        inputs.append(visible)
        response = call_model(visible, tools=TOOLS) if live else next(scripted)
        responses.append(response)
        return response

    run = run_task(case, workspace, k=3, context_limit=3, root=root, model=next_response)
    run.update(
        workspace_id=workspace_id,
        responses=responses,
        model_inputs=inputs,
        origin="live_model" if live else "constructed_decisions_real_tools",
        version_instruction=prefix,
        task=case["task"],
    )
    return run, workspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--judge", action="store_true")
    parser.add_argument(
        "--gate", action="store_true", help="Return failure when the candidate cannot be accepted"
    )
    args = parser.parse_args()
    if args.live and not args.judge:
        parser.error("--live requires --judge; fixtures cannot judge fresh model outputs")
    path = Path(__file__).with_name("cases.jsonl")
    cases = [json.loads(line) for line in path.read_text().splitlines()]
    for case in cases:
        if document(case["source"]["path"])["sha256"] != case["source"]["sha256"]:
            raise ValueError("Knowledge changed; review the task and reference")
    model, rows = JudgeModel(), []
    report = {
        "run_id": uuid.uuid4().hex,
        "mode": {
            "agent": "live" if args.live else "constructed_decisions_real_tools",
            "semantic_scoring": "native_deepeval" if args.judge else "constructed_fixtures",
        },
        "cases_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "versions": {"baseline": "", "candidate": REPAIR},
        "rows": rows,
    }
    for case in cases:
        for version in ["baseline", "candidate"]:
            run, workspace = run_case(case, version, live=args.live)
            judged_case = {**case, "fixture_completion": 0.5 if version == "baseline" else 1}
            row = {
                "case_id": case["id"],
                "family": case["family"],
                "version": version,
                "run": run,
                "usage": usage_summary(run["responses"]),
            }
            rows.append(row)
            save(report, prefix="e16-suite")
            row["evaluation"] = evaluate_run(
                run, workspace, judged_case, model if args.judge else None
            )
            report["judge_calls"] = model.calls
            save(report, prefix="e16-suite")
    report["gate"] = gate(rows, [c["id"] for c in cases])
    report["failure_candidates"] = failure_candidates(rows)
    print(save(report, prefix="e16-suite"))
    unavailable = any(
        r["evaluation"]["accepted"] is None or r["run"]["status"] == "model_error" for r in rows
    )
    return int(unavailable or (args.gate and report["gate"]["decision"] in {"reject", "blocked"}))


if __name__ == "__main__":
    raise SystemExit(main())
