"""Independent files/state acceptance and native efficiency judges answer separate questions."""

import argparse
import copy
import json
import math
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from deepeval.metrics import StepEfficiencyMetric
from deepeval.test_case import LLMTestCase

from lessons.e03_judges.eval import Transport
from lessons.e11_task_completion.eval import CapturingDeepJudge
from lessons.e13_planning.eval import trace_projection
from lessons.e13_planning.verify import files_at, unexpected_project_files, verify

from .resources import application_resources, usage_ledger


def received_notice_ids(session):
    ids = set()
    for request in session["model_inputs"]:
        if not request["response_received"]:
            continue
        for message in request["messages"]:
            text = message.get("content", "")
            prefix = "Runtime background notifications (data):\n"
            if isinstance(text, str) and text.startswith(prefix):
                ids.update(job["id"] for job in json.loads(text[len(prefix) :]))
    return ids


def grade_row(row, criteria):
    case = row["case"]
    if not re.fullmatch(r"[a-f0-9]{32}", row["run_id"]):
        raise ValueError("Invalid run ID")
    base = Path(os.environ.get("WORKSPACES_DIR", "workspaces")).resolve()
    workspace = base / row["run_id"]
    if workspace.resolve().parent != base:
        raise ValueError("Workspace escapes root")
    actual = files_at(workspace, case["files"])
    with tempfile.TemporaryDirectory() as directory:
        clean = Path(directory)
        for name, text in actual.items():
            if text is not None:
                (clean / name).write_bytes(text.encode("utf-8"))
        artifacts = verify(clean, case, criteria)
    protected = {
        n: actual[n] == text
        for n, text in case["files"].items()
        if n not in {"shipping.py", "checkout.py"}
    }
    extra = unexpected_project_files(workspace, case["files"])
    extra = [
        p
        for p in extra
        if p != ".scheduled_tasks.json"
        and not re.fullmatch(r"\.background/bg_[a-f0-9]{8}\.json", p)
    ]
    jobs = row["lead"]["background_jobs"]
    state_read_errors = []
    try:
        disk_jobs = [
            json.loads((workspace / ".background" / (j["id"] + ".json")).read_text()) for j in jobs
        ]
    except (OSError, ValueError) as error:
        disk_jobs = None
        state_read_errors.append(str(error))
    current = artifacts["artifact_hashes"]
    # The bounded verifier hashes every original file, including protected fixtures.
    notices = received_notice_ids(row["lead"])
    schedules = [e["job"] for e in row["schedule_events"] if e["action"] == "registered"]
    due = [e["job"] for e in row["schedule_events"] if e["action"] == "due"]
    receipts = row["delivery_receipts"]
    scheduled_started = bool(receipts) and any(
        j["started_at_monotonic"] > receipts[-1]["at_monotonic"] and j["status"] == "completed"
        for j in jobs
    )
    independent_reads = [
        o
        for o in row["tool_observations"]
        if o["call"]["name"] == "read_file"
        and json.loads(o["call"]["arguments_json"]).get("path") == "review.txt"
        and o["result_status"] == "ok"
    ]
    overlap = any(
        j["id"] in o["background_pending_at_start"]
        and j["started_at_monotonic"] <= o["started_at_monotonic"] <= j["ended_at_monotonic"]
        for o in independent_reads
        for j in jobs
    )
    try:
        persistent_schedule = (
            json.loads((workspace / ".scheduled_tasks.json").read_text())
            if (workspace / ".scheduled_tasks.json").exists()
            else None
        )
    except (OSError, ValueError) as error:
        persistent_schedule = None
        state_read_errors.append(str(error))
    accepted_prompt = len(receipts) == 1 and any(
        m["content"].startswith("[Scheduled; authorized registered prompt] ")
        and json.loads(m["content"].split("] ", 1)[1])["prompt"] == case["scheduled_prompt"]
        for m in row["lead"]["model_inputs"][receipts[0]["request_index"]]["messages"]
        if isinstance(m.get("content"), str)
    )
    tools = [e for e in row["lead"]["events"] if e["type"] == "tool"]
    plan_position = next(
        (
            i
            for i, e in enumerate(tools)
            if e["call"]["name"] == "todo_write" and e["result"]["status"] == "ok"
        ),
        None,
    )
    first_work = next(
        (
            i
            for i, e in enumerate(tools)
            if e["call"]["name"] in {"write_file", "edit_file", "background_bash", "schedule_cron"}
        ),
        len(tools),
    )
    checks = {
        "lead_finished": row["lead"]["status"] == "finished",
        "both_apis_and_protected_tests": artifacts["passed"] is True,
        "all_protected_original_bytes": all(protected.values()),
        "actual_files_match_report": actual == row["artifacts"],
        "no_unexpected_project_files": not extra,
        "background_records_match_disk": disk_jobs == jobs,
        "declared_background_outcomes": [j["status"] for j in jobs]
        == case["expected_background_statuses"],
        "all_jobs_notified_and_response_received": bool(jobs)
        and all(j["notified"] and j["id"] in notices for j in jobs),
        "no_pending_background_when_loop_stopped": not row["lead"][
            "background_pending_when_loop_stopped"
        ],
        "current_version_test_receipts": bool(jobs)
        and all(
            j["initial_hashes"] == j["final_hashes"] == current
            for j in jobs
            if j["status"] == "completed"
        ),
        "independent_parent_read_while_background_pending": overlap,
        "one_declared_durable_one_shot": len(schedules) == 1
        and schedules[0]["cron"] == "1 9 * * *"
        and schedules[0]["prompt"] == case["scheduled_prompt"]
        and schedules[0]["durable"] is True
        and schedules[0]["recurring"] is False,
        "one_due_delivery_at_controlled_minute": len(due) == 1
        and due[0]["last_fired"] == "2026-11-16T09:01+08:00",
        "scheduled_prompt_received_in_actual_model_input": accepted_prompt,
        "scheduled_work_actually_started_after_receipt": scheduled_started,
        "one_shot_removed_after_receipt": persistent_schedule
        == row["schedule_definitions_at_end"]
        == [],
        "exact_controlled_clock_advance": row["final_clock"] == "2026-11-16T09:01:00+08:00",
        "native_sdk_trace_recorded": bool(
            (row.get("native_deepeval_trace") or {}).get("root_spans")
        ),
        "explicit_plan_before_work": plan_position is not None and plan_position < first_work,
        "todos_updated_to_complete": bool(row["lead"]["todos"])
        and all(t["status"] == "completed" for t in row["lead"]["todos"]),
    }
    return {
        "run_id": row["run_id"],
        "case_id": case["id"],
        "variant": case["variant"],
        "repetition": row["repetition"],
        "origin": "independent_actual_files_state_records_and_received_input_checks",
        "checks": checks,
        "passed": all(checks.values()),
        "artifacts": artifacts,
        "protected_bytes": protected,
        "unexpected_files": extra,
        "state_read_errors": state_read_errors,
        "resources": application_resources(row),
        "judge_requests": 0,
    }


def judge_cases(report):
    cases = []
    for row in report["rows"]:
        if not row.get("native_metric_trace"):
            continue
        cases.append(
            {
                "id": row["run_id"],
                "origin": "actual_sdk_collected_application_trace_projection",
                "task": row["case"]["task"],
                "trace": trace_projection(row["native_metric_trace"]),
            }
        )
    task = "修复shipping_fee的1001克计费，保持公开签名和原测试，并实际执行回归检查。"
    for name, actions in (
        ("short_but_no_work", ["Declared done; did not change files or execute tests"]),
        (
            "repeated_reads",
            [
                "Read shipping.py",
                "Read shipping.py again without any edit",
                "Read shipping.py again without any edit",
                "Edited the formula",
                "Ran regression tests",
            ],
        ),
    ):
        cases.append(
            {
                "id": name,
                "origin": "instructor_constructed_trace_not_agent_execution",
                "task": task,
                "trace": {
                    "type": "agent",
                    "input": task,
                    "output": "Instructor fixture actions only",
                    "children": [
                        {"type": "tool", "name": "instructor_action", "output": action}
                        for action in actions
                    ],
                },
            }
        )
    return cases


def judge_one(case):
    transport = Transport()
    model = CapturingDeepJudge(transport)
    sample = LLMTestCase(
        input=case["task"], actual_output=json.dumps(case["trace"], ensure_ascii=False)
    )
    sample._trace_dict = copy.deepcopy(case["trace"])
    try:
        metric = StepEfficiencyMetric(model=model, eval_mode="llm", async_mode=False, threshold=0.7)
        score = metric.measure(sample, _show_indicator=False)
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Efficiency score outside finite 0..1")
        result = {"score": score, "reason": metric.reason}
    except Exception as error:  # noqa: BLE001 - preserve model/SDK errors as unscored
        result = {"score": None, "error": str(error)}
    return {
        **case,
        **result,
        "steps": model.steps,
        "calls": transport.calls,
        "binding": "fixed-version internal _trace_dict binding of real SDK projection or labeled fixture",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    root = Path(os.environ.get("RUNS_DIR", "runs"))
    report = json.loads((root / "e14-agent.json").read_text())
    if args.judge:
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(judge_one, judge_cases(report)))
        result = {
            "lesson": "e14",
            "mode": "native_llm_step_efficiency_separate_from_completion",
            "rows": rows,
            "successful_judge_responses": sum(len(r["calls"]) for r in rows),
            "metric_errors": sum(r["score"] is None for r in rows),
        }
        result["judge_resources"] = usage_ledger(
            [c.get("model", c) for r in rows for c in r["calls"]]
        )
        filename = "e14-judges.json"
    else:
        criteria = json.loads(
            Path(os.environ.get("E14_CRITERIA_FILE", "/verification/e14.json")).read_text()
        )
        rows = [grade_row(r, criteria) for r in report["rows"]]
        planned = report["planned_runs"]
        observed = [{"case_id": r["case_id"], "repetition": r["repetition"]} for r in rows]
        normal = [r for r in rows if r["variant"] == "normal"]
        controls = json.loads((root / "e14-controls.json").read_text())
        result = {
            "lesson": "e14",
            "mode": "independent_acceptance_not_efficiency_score",
            "rows": rows,
            "normal_successes": sum(r["passed"] for r in normal),
            "normal_attempts": len(normal),
            "declared_batch_complete": observed == planned,
            "protocol_controls": controls["checks"],
            "passed": bool(rows)
            and observed == planned
            and all(r["passed"] for r in rows)
            and controls["passed"],
        }
        filename = "e14-evaluation.json"
    (root / filename).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "passed",
                    "normal_successes",
                    "normal_attempts",
                    "successful_judge_responses",
                    "metric_errors",
                )
                if k in result
            }
        )
    )
    return int(result.get("passed") is False or result.get("metric_errors", 0) > 0)


if __name__ == "__main__":
    raise SystemExit(main())
