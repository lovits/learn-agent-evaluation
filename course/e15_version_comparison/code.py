"""Change only the number of contexts; keep paired runs and judge costs separate."""

import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path

from deepeval.test_case import LLMTestCase

from course.e04_scoring.eval import score
from course.e05_knowledge_context.code import TOOLS, run_task
from eval_course.judge import JudgeModel
from eval_course.knowledge import catalog
from eval_course.records import save
from eval_course.runtime import call_model, prepare_workspace

from .eval import compare, quality_metric, usage_summary


def run_version(case, version, live=False, root=None):
    responses, origins = [], []

    def next_response(messages):
        if len(messages) == 1:
            response = {
                "reply": {
                    "answer": "",
                    "tool_calls": [
                        {
                            "name": "search_knowledge",
                            "arguments_json": json.dumps({"query": case["query"]}),
                        }
                    ],
                }
            }
            origin = "controlled_first_retrieval"
        elif live:
            response, origin = call_model(messages, tools=TOOLS), "live_model"
        else:
            response = {"reply": {"answer": case["fixture_answers"][version], "tool_calls": []}}
            origin = "constructed_final_answer"
        responses.append(response)
        origins.append(origin)
        return response

    started = time.monotonic()
    run = run_task(
        case,
        prepare_workspace({"files": {}}, uuid.uuid4().hex),
        k=3,
        context_limit=1 if version == "baseline" else 3,
        root=root,
        model=next_response,
    )
    events = run["events"]
    contract = (
        run["status"] == "finished"
        and len(events) == 1
        and events[0]["name"] == "search_knowledge"
        and events[0]["result"]["status"] == "ok"
    )
    return {
        "run": run,
        "contract": contract,
        "responses": responses,
        "decision_origins": origins,
        "runtime": {
            "agent_elapsed_seconds": round(time.monotonic() - started, 3),
            **usage_summary(responses),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    if args.live and not args.judge:
        parser.error("--live requires --judge; fixture scores do not describe live answers")
    path = Path(__file__).with_name("cases.jsonl")
    cases = [json.loads(line) for line in path.read_text().splitlines()]
    documents = {d["path"]: d["sha256"] for d in catalog()}
    for case in cases:
        if any(documents.get(s["path"]) != s["sha256"] for s in case["sources"]):
            raise ValueError("A reference source changed; review cases before comparison")
    model, rows = JudgeModel(), []
    metric = quality_metric(model) if args.judge else None
    report = {
        "run_id": uuid.uuid4().hex,
        "mode": {
            "agent": "controlled_retrieval_live_continuation"
            if args.live
            else "constructed_decisions",
            "scoring": "native_deepeval" if args.judge else "constructed_score_fixture",
        },
        "cases_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "changed_factor": {"context_limit": {"baseline": 1, "candidate": 3}},
        "fixed": {
            "retrieval_k": 3,
            "repeats": 2,
            "query": "per case",
            "model_selector": "same bridge default, checkpoint not verified",
            "threshold": 1.0,
        },
        "judge_steps": metric.evaluation_steps if metric else None,
        "rows": rows,
    }
    for repeat in range(2):
        for case in cases:
            order = ["baseline", "candidate"] if repeat == 0 else ["candidate", "baseline"]
            for version in order:
                row = {
                    "case_id": case["id"],
                    "repeat": repeat,
                    "version": version,
                    **run_version(case, version, args.live),
                }
                sample = LLMTestCase(
                    **{
                        k: row["run"]["sample"][k]
                        for k in ["input", "actual_output", "expected_output", "retrieval_context"]
                    }
                )
                before, started = len(model.calls), time.monotonic()
                result = (
                    score(metric, sample)
                    if metric
                    else {
                        "status": "ok",
                        "score": case["fixture_scores"][version],
                        "passed": case["fixture_scores"][version] == 1,
                        "reason": "Constructed score for aggregation practice, not a model verdict",
                    }
                )
                row.update(
                    result=result,
                    quality=(result["score"] if row["contract"] else 0)
                    if result["status"] == "ok"
                    else None,
                    judge_elapsed_seconds=round(time.monotonic() - started, 3),
                    judge_calls=model.calls[before:],
                )
                rows.append(row)
                save(report, prefix="e15-suite")
    report["comparison"] = compare(rows, cases)
    print(save(report, prefix="e15-suite"))
    return int(
        any(r["result"]["status"] != "ok" or r["run"]["status"] == "model_error" for r in rows)
    )


if __name__ == "__main__":
    raise SystemExit(main())
