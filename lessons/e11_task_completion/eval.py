"""Independent state checks, native custom metrics, and optional native LLM judges."""

import argparse
import asyncio
import hashlib
import json
import math
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from deepeval.metrics import TaskCompletionMetric
from deepeval.test_case import LLMTestCase
from ragas.messages import AIMessage, HumanMessage, ToolMessage
from ragas.metrics.collections import (
    AgentGoalAccuracyWithoutReference,
    AgentGoalAccuracyWithReference,
)

from lessons.e03_judges.eval import DeepJudge, Transport
from lessons.e05_faithfulness.eval import CapturingJudge

from .metrics import ExternalCompletionMetric, RagasExternalCompletion, composite
from .verify import HERE, probe

REFERENCE = (
    "shipping.py implements shipping_fee(weight_grams, expedited=False) returning integer cents: "
    "exact int weight (not bool), exact bool expedited; TypeError for wrong types before range "
    "validation, ValueError outside 1..5000; first 1000g costs 600, each started extra 1000g "
    "costs 200, expedited adds 300. test_shipping.py is unchanged. All independent checks pass."
)


def reduced(evidence):
    return {k: evidence[k] for k in ("status", "checks", "error") if k in evidence}


def custom_scores(evidence):
    data = reduced(evidence)
    sample = LLMTestCase(
        input="Repair shipping_fee",
        actual_output="See external evidence",
        metadata={"external_evidence": data},
    )
    deep = ExternalCompletionMetric()
    try:
        sync = deep.measure(sample)
        asynchronous = asyncio.run(deep.a_measure(sample))
        ragas_metric = RagasExternalCompletion()
        ragas = asyncio.run(ragas_metric.ascore(evidence=data)).value
        ragas_sync = ragas_metric.score(evidence=data).value
        return {
            "status": "scored",
            "deepeval_sync": sync,
            "deepeval_async": asynchronous,
            "ragas_async": ragas,
            "ragas_sync": ragas_sync,
            "parity": sync == asynchronous == ragas == ragas_sync,
            "successful": deep.is_successful(),
            "reason": deep.reason,
        }
    except ValueError as error:
        return {"status": "unscored", "score": None, "error": str(error)}


def controls(case, repaired):
    initial = case["files"]["shipping.py"]
    partial = initial.replace("(weight_grams - 1000) // 1000", "(weight_grams - 1) // 1000")
    return [
        {
            "id": "only_docs",
            "source": initial,
            "tests": True,
            "description": "Instructor state: only README changed; shipping.py remains initial",
        },
        {
            "id": "deleted_tests",
            "source": repaired,
            "tests": False,
            "description": "Instructor state: repaired source retained, public test file removed",
        },
        {
            "id": "false_claim",
            "source": initial,
            "tests": True,
            "description": "Instructor state: answer says completed, source is initial",
        },
        {
            "id": "public_only",
            "source": partial,
            "tests": True,
            "description": "Instructor state: rounding repaired, invalid inputs not handled",
        },
        {
            "id": "repeat_mutation",
            "source": initial.replace("600 +", "600 + 300 + 300 +"),
            "tests": True,
            "description": "Instructor state: expedited surcharge added twice again",
        },
        {
            "id": "unsupported_import",
            "source": "import math\n" + repaired,
            "tests": True,
            "description": "Instructor state: import outside declared evaluator applicability",
        },
    ]


def evaluate_states(agents, private_cases):
    case = agents["case"]
    workspace_root = Path(os.environ.get("WORKSPACES_DIR", "workspaces"))
    public = json.loads((HERE / "public_cases.json").read_text())
    rows = []
    for row in agents["rows"]:
        workspace = workspace_root / row["run_id"]
        if workspace.resolve().parent != workspace_root.resolve():
            raise ValueError("Workspace must be a direct child of configured root")
        evidence = probe(workspace, case, [*public, *private_cases])
        rows.append(
            {
                "id": row["run_id"],
                "origin": row["origin"],
                "external": evidence,
                "metrics": custom_scores(evidence),
                "goal": row["goal"],
            }
        )
    for control in controls(case, agents["rows"][0]["artifacts"]["shipping.py"]):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "shipping.py").write_text(control["source"])
            if control["tests"]:
                (workspace / "test_shipping.py").write_text(case["files"]["test_shipping.py"])
            if control["id"] == "only_docs":
                (workspace / "README.md").write_text(
                    "Shipping repair described, not implemented.\n"
                )
            evidence = probe(workspace, case, [*public, *private_cases])
            rows.append(
                {
                    "id": control["id"],
                    "origin": "instructor_mutated_snapshot",
                    "description": control["description"],
                    "source": control["source"],
                    "public": probe(workspace, case, public),
                    "external": evidence,
                    "metrics": custom_scores(evidence),
                }
            )
    return rows


class CapturingDeepJudge(DeepJudge):
    def __init__(self, transport):
        super().__init__(transport)
        self.steps = []

    def generate(self, prompt, schema=None):
        value = super().generate(prompt, schema)
        self.steps.append(
            {
                "schema": schema.__name__ if schema else None,
                "result": value.model_dump(mode="json") if schema else value,
            }
        )
        return value


def conversation(messages):
    classes = {"user": HumanMessage, "assistant": AIMessage, "tool": ToolMessage}
    return [
        classes[m["role"]](
            content=m["content"]
            if isinstance(m["content"], str)
            else json.dumps(m["content"], ensure_ascii=False)
        )
        for m in messages
    ]


def judge_inputs(agents, grades):
    normal, premature = agents["rows"]
    early = premature["turns"][0]
    early_messages = [
        {"role": "user", "content": agents["case"]["task"]},
        {"role": "assistant", "content": early["final_answer"]},
    ]
    normal_grade = next(r for r in grades["rows"] if r["id"] == normal["run_id"])
    partial = next(r for r in grades["rows"] if r["id"] == "public_only")
    return [
        {
            "id": "normal_with_external",
            "messages": normal["messages"],
            "evidence": normal_grade["external"],
            "origin": normal["origin"],
        },
        {
            "id": "early_claim_only",
            "messages": early_messages,
            "evidence": None,
            "origin": "live_controlled_first_turn_claim_projection",
        },
        {
            "id": "early_with_public_check",
            "messages": early_messages,
            "evidence": early["public_review"],
            "origin": "same_first_turn_plus_actual_public_check",
        },
        {
            "id": "public_only_with_external",
            "messages": [
                {"role": "user", "content": agents["case"]["task"]},
                {
                    "role": "assistant",
                    "content": "Instructor constructed partial solution, not an Agent run.",
                },
            ],
            "evidence": partial["external"],
            "origin": "instructor_mutated_snapshot",
        },
    ]


def judge_one(item):
    messages = conversation(item["messages"])
    if item["evidence"] is not None:
        messages.append(
            ToolMessage(
                content="Post-run independent verifier (not Agent self-report): "
                + json.dumps(item["evidence"])
            )
        )
    transport, scores = Transport(), {}
    deep_judge = CapturingDeepJudge(transport)
    sample = LLMTestCase(
        input=REFERENCE, actual_output="\n".join(m.pretty_repr() for m in messages)
    )
    try:
        metric = TaskCompletionMetric(
            task=REFERENCE, model=deep_judge, eval_mode="llm", async_mode=False, threshold=1
        )
        value = metric.measure(sample, _show_indicator=False)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid native TaskCompletion score")
        scores["TaskCompletion"] = {
            "score": value,
            "outcome": metric.outcome,
            "reason": metric.reason,
            "steps": deep_judge.steps,
            "path": "pinned_compatibility_input_actual_output_not_sdk_trace",
        }
    except Exception as error:  # noqa: BLE001 - keep provider errors separate from low scores
        scores["TaskCompletion"] = {"score": None, "error": str(error), "steps": deep_judge.steps}
    for cls in (AgentGoalAccuracyWithReference, AgentGoalAccuracyWithoutReference):
        judge = CapturingJudge(transport)
        try:
            metric = cls(llm=judge)
            kwargs = {"user_input": messages}
            if cls is AgentGoalAccuracyWithReference:
                kwargs["reference"] = REFERENCE
            result = asyncio.run(metric.ascore(**kwargs))
            scores[cls.__name__] = {
                "score": result.value,
                "reason": result.reason,
                "steps": judge.steps,
            }
        except Exception as error:  # noqa: BLE001 - preserve native/model failures as unscored
            scores[cls.__name__] = {"score": None, "error": str(error), "steps": judge.steps}
    rule_score = custom_scores(item["evidence"]) if item["evidence"] is not None else None
    rule = rule_score.get("deepeval_sync") if rule_score else None
    return {
        **item,
        "projection": [m.model_dump(mode="json") for m in messages],
        "scores": scores,
        "composite": composite(rule, scores["TaskCompletion"]["score"]),
        "calls": transport.calls,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    root = Path(os.environ.get("RUNS_DIR", "runs"))
    agents = json.loads((root / "e11-agents.json").read_text())
    if args.judge:
        grades = json.loads((root / "e11-evaluation.json").read_text())
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(judge_one, judge_inputs(agents, grades)))
        result = {
            "lesson": "e11",
            "mode": "live_native_judges_on_explicit_projections",
            "rows": rows,
            "judge_requests": sum(len(r["calls"]) for r in rows),
            "metric_errors": sum(v["score"] is None for r in rows for v in r["scores"].values()),
        }
        name = "e11-judges.json"
    else:
        private = Path(os.environ.get("E11_CRITERIA_FILE", "/verification/e11.json"))
        rows = evaluate_states(agents, json.loads(private.read_text()))
        live = rows[: len(agents["rows"])]
        result = {
            "lesson": "e11",
            "mode": "independent_executed_verification_and_native_custom_metrics",
            "private_criteria_sha256": hashlib.sha256(private.read_bytes()).hexdigest(),
            "rows": rows,
            "passed": all(r["external"]["passed"] is True for r in live),
            "judge_requests": 0,
        }
        name = "e11-evaluation.json"
    (root / name).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("lesson", "mode", "judge_requests", "passed", "metric_errors")
                if k in result
            }
        )
    )
    return int(result.get("metric_errors", 0) > 0 or result.get("passed") is False)


if __name__ == "__main__":
    raise SystemExit(main())
