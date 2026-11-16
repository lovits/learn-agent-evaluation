"""Run pinned native metrics on explicit traces, preserving each input projection."""

import asyncio
import json
import warnings
from pathlib import Path

from deepeval.metrics import ArgumentCorrectnessMetric, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall, ToolCallParams
from ragas.messages import AIMessage, HumanMessage
from ragas.messages import ToolCall as RagasCall
from ragas.metrics.collections import ToolCallAccuracy, ToolCallF1

from lessons.e03_judges.eval import DeepJudge, Transport

HERE = Path(__file__).parent


class NoJudge:
    def ask(self, prompt):
        raise AssertionError("This rule-only metric configuration must not call a model")


class RuleInterface(DeepJudge):
    def get_model_name(self):
        return "unused_interface_for_deterministic_tool_matching"


def native_case(row):
    return LLMTestCase(
        input=row["task"],
        actual_output="Tool trace projection; see origin and original report.",
        tools_called=[
            ToolCall(name=c["name"], input_parameters=c["args"]) for c in row["predicted"]
        ],
        expected_tools=[
            ToolCall(name=c["name"], input_parameters=c["args"]) for c in row["expected"]
        ],
        metadata={"origin": row["origin"], "case_id": row["id"]},
    )


async def ragas_scores(row):
    messages = [
        HumanMessage(content=row["task"]),
        AIMessage(
            content="Explicit trajectory projection",
            tool_calls=[RagasCall(name=c["name"], args=c["args"]) for c in row["predicted"]],
        ),
    ]
    reference = [RagasCall(name=c["name"], args=c["args"]) for c in row["expected"]]
    result = {}
    for name, metric in [
        ("ragas_strict", ToolCallAccuracy()),
        ("ragas_flexible", ToolCallAccuracy(strict_order=False)),
        ("ragas_f1", ToolCallF1()),
    ]:
        result[name] = (
            await metric.ascore(user_input=messages, reference_tool_calls=reference)
        ).value
    return result


def score_rules(row):
    model = RuleInterface(NoJudge())
    sample, scores = native_case(row), {}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for name, options in [
            ("deep_names", {}),
            ("deep_parameters", {"evaluation_params": [ToolCallParams.INPUT_PARAMETERS]}),
            (
                "deep_ordered",
                {
                    "evaluation_params": [ToolCallParams.INPUT_PARAMETERS],
                    "should_consider_ordering": True,
                },
            ),
            (
                "deep_exact",
                {
                    "evaluation_params": [ToolCallParams.INPUT_PARAMETERS],
                    "should_exact_match": True,
                },
            ),
        ]:
            metric = ToolCorrectnessMetric(
                model=model, eval_mode="llm", async_mode=False, **options
            )
            scores[name] = metric.measure(sample, _show_indicator=False)
        scores.update(asyncio.run(ragas_scores(row)))
    return {
        **row,
        "scores": scores,
        "warnings": [str(w.message) for w in caught],
        "native_deepeval_sample": sample.model_dump(mode="json"),
        "judge_requests": 0,
    }


def live_projection(row, reference):
    selected = []
    for event in row["events"]:
        if event["type"] != "tool":
            continue
        call = event["call"]
        args = json.loads(call["arguments_json"])
        if call["name"] == "read_file" and args.get("path") == "result.txt":
            continue
        if call["name"] in {"read_file", "edit_file", "write_file", "bash"}:
            selected.append({"name": call["name"], "args": args, "source_span": event["span_id"]})
    return {
        "id": "live-" + ("mcp" if row["mcp_enabled"] else "builtin"),
        "origin": "live_core_projection_not_a_whole_task_score",
        "source_run_id": row["run_id"],
        "task": row["task"],
        "predicted": selected,
        "expected": reference,
        "projection": "retain read/edit/write/bash attempts; omit documentation lookup and final result.txt readback; full events retained separately",
    }


def judge_metrics(rows):
    transport, output = Transport(), []
    model = DeepJudge(transport)
    available = [
        ToolCall(name="read_file", description="Read a workspace file."),
        ToolCall(name="edit_file", description="Replace one occurrence in a workspace file."),
        ToolCall(name="bash", description="Execute a workspace command."),
        ToolCall(name="glob", description="List matching workspace paths without reading content."),
    ]
    for row in rows:
        sample = native_case(row)
        if row["id"] in {"perfect", "wrong_path", "no_calls"} or row["id"].startswith("live-"):
            start = len(transport.calls)
            metric = ArgumentCorrectnessMetric(
                model=model, eval_mode="llm", async_mode=False, include_reason=False
            )
            score = metric.measure(sample, _show_indicator=False)
            output.append(
                {
                    "case_id": row["id"],
                    "metric": "ArgumentCorrectness",
                    "score": score,
                    "verdicts": [v.model_dump(mode="json") for v in metric.verdicts],
                    "judge_requests": len(transport.calls) - start,
                }
            )
        if row["id"] in {"perfect", "wrong_tool"}:
            start = len(transport.calls)
            metric = ToolCorrectnessMetric(
                model=model, eval_mode="llm", async_mode=False, available_tools=available
            )
            score = metric.measure(sample, _show_indicator=False)
            output.append(
                {
                    "case_id": row["id"],
                    "metric": "ToolCorrectness_with_available_tools",
                    "score": score,
                    "reason": metric.reason,
                    "judge_requests": len(transport.calls) - start,
                }
            )
    return {
        "results": output,
        "calls": transport.calls,
        "scope": "native automatic judgments, not independent file facts or human labels",
    }
