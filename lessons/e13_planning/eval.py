"""Grade scheduling and artifacts separately from native plan judges."""

import argparse
import asyncio
import copy
import json
import math
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from deepeval.metrics import PlanAdherenceMetric, PlanQualityMetric
from deepeval.test_case import LLMTestCase
from ragas.metrics.collections import DomainSpecificRubrics

from lessons.e03_judges.eval import Transport
from lessons.e05_faithfulness.eval import CapturingJudge
from lessons.e11_task_completion.eval import CapturingDeepJudge

from .state import TaskStore
from .verify import files_at, verify

QUALITY = {
    "score1_description": "The explicit plan is absent, irrelevant, or would violate the task's protected interface/tests.",
    "score2_description": "The explicit plan omits a major required component or prerequisite.",
    "score3_description": "The plan covers both components but misses a constraint or an integration check.",
    "score4_description": "The plan is executable, ordered by dependencies, and covers almost all requirements.",
    "score5_description": "The explicit plan covers both API repairs, dependencies, preserved signatures/tests and actual integrated verification with clear necessary steps.",
}
ADHERENCE = {
    "score1_description": "No explicit plan exists, or the observed actions contradict nearly all planned steps.",
    "score2_description": "Only a small part of the stated plan is supported by observed actions.",
    "score3_description": "Several planned steps were executed, but a material step or prerequisite was missed.",
    "score4_description": "The recorded execution follows the plan with a small omission or justified change.",
    "score5_description": "Observed execution supports all stated steps and prerequisite order. This evaluates adherence even when the stated plan itself is bad; it does not certify task completion.",
}


def graph_evidence(events):
    states, claims, valid = {}, 0, True
    initial_graph_ready = False
    for event in events:
        task = event["task"]
        if event["action"] == "claim":
            if claims == 0:
                initial_graph_ready = len(states) >= 2 and any(
                    t["blocked_by"] for t in states.values()
                )
            claims += 1
            valid = valid and all(
                states.get(d, {}).get("status") == "completed" for d in task["blocked_by"]
            )
        states[task["id"]] = task
    return {
        "all_claims_after_dependency_completion": valid,
        "claims_observed": claims,
        "initial_graph_before_first_claim": initial_graph_ready,
        "final_event_states": states,
    }


def evaluate(report, criteria):
    row, case = report["row"], report["case"]
    if not re.fullmatch(r"[a-f0-9]{32}", row["run_id"]):
        raise ValueError("Invalid run ID")
    root = Path(os.environ.get("WORKSPACES_DIR", "workspaces")).resolve()
    workspace = root / row["run_id"]
    if workspace.resolve().parent != root:
        raise ValueError("Run workspace escapes root")
    actual = files_at(workspace, case["files"])
    artifacts = verify(workspace, case, criteria)
    tasks = TaskStore(workspace).list()
    graph = graph_evidence(row["task_events"])
    children = row["children"]
    latest_children = {c["result"]["task_id"]: c for c in children}
    failed_attempts = [
        {
            "actor": c["result"]["actor"],
            "task_id": c["result"]["task_id"],
            "status": c["result"]["status"],
        }
        for c in children
        if c["result"]["status"] != "finished"
    ]
    lead_tools = [e for e in row["lead"]["events"] if e["type"] == "tool"]
    first_plan = next(
        (
            i
            for i, e in enumerate(lead_tools)
            if e["call"]["name"] == "todo_write" and e["result"]["status"] == "ok"
        ),
        None,
    )
    first_mutation = next(
        (
            i
            for i, e in enumerate(lead_tools)
            if e["call"]["name"] in {"task", "write_file", "edit_file"}
        ),
        len(lead_tools),
    )
    checks = {
        "actual_artifacts_match_report": actual == row["artifacts"],
        "both_apis_and_original_tests": artifacts["passed"] is True,
        "persistent_tasks_match_report": tasks == row["tasks"],
        "persistent_tasks_match_event_states": {t["id"]: t for t in tasks}
        == graph["final_event_states"],
        "nonempty_task_graph_with_dependency": bool(tasks) and any(t["blocked_by"] for t in tasks),
        "all_tasks_claimed_complete": bool(tasks)
        and all(t["status"] == "completed" for t in tasks),
        "dependency_claim_order": graph["all_claims_after_dependency_completion"],
        "graph_created_before_delegation": graph["initial_graph_before_first_claim"],
        "lead_finished": row["lead"]["status"] == "finished",
        "separate_components_delegated": len(children) >= 2
        and any(c["assigned_files"] == ["shipping.py"] for c in children)
        and any(c["assigned_files"] == ["checkout.py"] for c in children),
        "latest_task_handoffs_finished": bool(latest_children)
        and all(c["result"]["status"] == "finished" for c in latest_children.values()),
        "explicit_plan_recorded": bool(row["lead"]["todos"]),
        "explicit_plan_before_delegation_or_edits": first_plan is not None
        and first_plan < first_mutation,
        "fresh_child_contexts": bool(children)
        and all(
            c["result"]["model_inputs"]
            and c["result"]["model_inputs"][0]["messages"]
            == [{"role": "user", "content": c["result"]["initial_request"]}]
            for c in children
        ),
        "native_sdk_trace_recorded": bool(row.get("native_deepeval_trace", {}).get("root_spans")),
    }
    return {
        "lesson": "e13",
        "mode": "actual_files_and_task_events_independent_reexecution",
        "checks": checks,
        "passed": all(checks.values()),
        "artifacts": artifacts,
        "graph": graph,
        "child_attempt_errors": failed_attempts,
        "completed_after_child_retries": all(checks.values()) and bool(failed_attempts),
        "judge_requests": 0,
    }


def trace_projection(trace):
    """Keep actual calls and outputs, omitting repeated full request histories from LLM nodes."""

    def span(node):
        kind = node.get("type")
        output = node.get("output")
        if kind == "llm" and isinstance(output, dict):
            output = {"reply": output.get("reply")}
        return {
            "uuid": node.get("uuid"),
            "parent_uuid": node.get("parent_uuid"),
            "name": node.get("name"),
            "type": kind,
            "input": node.get("input")
            if kind != "llm"
            else {"request_history": "omitted duplicate; original retained"},
            "output": output,
            "metadata": node.get("metadata"),
            "children": [span(c) for c in node.get("children", [])],
        }

    return {
        **span(trace),
        "projection_scope": "official nested-span conversion of actual SDK evidence; repeated LLM input histories omitted",
    }


def explicit_plan(row):
    for event in row["lead"]["events"]:
        if (
            event["type"] == "tool"
            and event["call"]["name"] == "todo_write"
            and event["result"]["status"] == "ok"
        ):
            return json.loads(event["call"]["arguments_json"])["todos"]
    return []


def judge_cases(report):
    row, task = report["row"], report["case"]["task"]
    trace = row.get("native_metric_trace")
    if not trace or not trace.get("children"):
        raise ValueError("Native SDK collection is required for the live scoring case")
    cases = [
        {
            "id": "live_native_trace",
            "origin": "actual_sdk_collected_application_trace_projection",
            "task": task,
            "trace": trace_projection(trace),
            "first_explicit_plan": explicit_plan(row),
        }
    ]
    sound = [
        "Inspect the v3 project rules and preserve both signatures and original tests",
        "Repair the core rounding first",
        "Repair quote argument forwarding after the core task",
        "Run both components and integrated tests",
    ]
    bad = ["Delete the original tests", "Only write a README saying done", "Declare success"]
    fixtures = [
        (
            "sound_plan_not_followed",
            sound,
            ["Repaired only shipping.py", "quote still omits expedited; no integration check"],
        ),
        (
            "bad_plan_followed",
            bad,
            ["Deleted original tests", "Wrote README only", "Declared success"],
        ),
        ("no_explicit_plan", [], ["Read files", "Edited implementations", "Ran tests"]),
    ]
    for name, plan, actions in fixtures:
        cases.append(
            {
                "id": name,
                "origin": "instructor_constructed_trace_not_agent_execution",
                "task": task,
                "first_explicit_plan": [{"content": p, "status": "pending"} for p in plan],
                "trace": {
                    "input": task,
                    "root_spans": [
                        {
                            "name": "constructed_agent",
                            "type": "agent",
                            "input": task,
                            "output": "Instructor fixture actions only",
                            "children": (
                                [
                                    {
                                        "type": "llm",
                                        "output": {"answer": "Explicit plan: " + json.dumps(plan)},
                                    }
                                ]
                                if plan
                                else []
                            )
                            + [
                                {"type": "tool", "name": "instructor_action", "output": action}
                                for action in actions
                            ],
                        }
                    ],
                },
            }
        )
    return cases


def judge_one(case):
    sample = LLMTestCase(
        input=case["task"], actual_output=json.dumps(case["trace"], ensure_ascii=False)
    )
    # Pinned low-level metric binding. Collection above uses real @observe spans;
    # official dataset/observe evaluation normally supplies this private attribute.
    sample._trace_dict = copy.deepcopy(case["trace"])
    transport, scores = Transport(), {}
    for cls in (PlanQualityMetric, PlanAdherenceMetric):
        model = CapturingDeepJudge(transport)
        try:
            metric = cls(model=model, eval_mode="llm", async_mode=False, threshold=0.7)
            value = metric.measure(sample, _show_indicator=False)
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Native plan score outside [0,1]")
            plans = [s["result"]["plan"] for s in model.steps if s["schema"] == "AgentPlan"]
            scores[cls.__name__] = {
                "score": value,
                "reason": metric.reason,
                "steps": model.steps,
                "extracted_plans": plans,
                "empty_plan_default": bool(plans) and plans[-1] == [],
            }
        except Exception as error:  # noqa: BLE001 - model/SDK failures are not zero scores
            scores[cls.__name__] = {"score": None, "error": str(error), "steps": model.steps}
    for name, rubric in (
        ("RagasPlanQualityRubric", QUALITY),
        ("RagasPlanAdherenceRubric", ADHERENCE),
    ):
        model = CapturingJudge(transport)
        try:
            metric = DomainSpecificRubrics(llm=model, rubrics=rubric)
            response = {"first_explicit_plan": case["first_explicit_plan"]}
            if name == "RagasPlanAdherenceRubric":
                response["execution_trace"] = case["trace"]
            result = asyncio.run(
                metric.ascore(
                    user_input=case["task"], response=json.dumps(response, ensure_ascii=False)
                )
            )
            if not math.isfinite(result.value) or result.value not in {1, 2, 3, 4, 5}:
                raise ValueError("Rubric score outside declared integer levels")
            scores[name] = {
                "score": result.value,
                "reason": result.reason,
                "steps": model.steps,
                "rubric": rubric,
                "scale": "1..5, custom criteria; not a same-named native Plan metric",
            }
        except Exception as error:  # noqa: BLE001 - preserve unscored errors
            scores[name] = {"score": None, "error": str(error), "steps": model.steps}
    return {
        **case,
        "scores": scores,
        "calls": transport.calls,
        "trace_binding": "fixed-version low-level _trace_dict binding of SDK-collected or labeled constructed input",
    }


def state_controls(report, criteria):
    case, repaired = report["case"], report["row"]["artifacts"]
    rows = []
    for name in ("lost_forwarding", "deleted_tests"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename, text in repaired.items():
                (root / filename).write_text(text or "")
            if name == "lost_forwarding":
                (root / "checkout.py").write_text(case["files"]["checkout.py"])
            else:
                (root / "test_checkout.py").unlink()
            result = verify(root, case, criteria)
            rows.append(
                {
                    "id": name,
                    "origin": "instructor_constructed_artifact_state_reexecuted",
                    "verification": result,
                    "expected_failure_observed": result["passed"] is False,
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    root = Path(os.environ.get("RUNS_DIR", "runs"))
    report = json.loads((root / "e13-agent.json").read_text())
    if args.judge:
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(judge_one, judge_cases(report)))
        result = {
            "lesson": "e13",
            "mode": "native_plan_and_custom_ragas_rubric_judges",
            "rows": rows,
            "successful_judge_responses": sum(len(r["calls"]) for r in rows),
            "metric_errors": sum(s["score"] is None for r in rows for s in r["scores"].values()),
        }
        filename = "e13-judges.json"
    else:
        criteria = json.loads(
            Path(os.environ.get("E13_CRITERIA_FILE", "/verification/e13.json")).read_text()
        )
        result = evaluate(report, criteria)
        result["state_controls"] = state_controls(report, criteria)
        controls = json.loads((root / "e13-controls.json").read_text())
        result["protocol_controls"] = controls["checks"]
        result["passed"] = (
            result["passed"]
            and controls["passed"]
            and all(r["expected_failure_observed"] for r in result["state_controls"])
        )
        filename = "e13-evaluation.json"
    (root / filename).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("passed", "successful_judge_responses", "metric_errors")
                if k in result
            }
        )
    )
    return int(result.get("passed") is False or result.get("metric_errors", 0) > 0)


if __name__ == "__main__":
    raise SystemExit(main())
