"""Convert a checked raw trace to native SDK samples, without inventing retrieval."""

import json


def trace_errors(report):
    errors, pending, model_ids, tools = [], [], set(), []
    for event in report["events"]:
        if event["type"] == "model":
            if pending:
                errors.append("missing_tool_result")
            model_id = event["span_id"]
            if model_id in model_ids or event["parent_id"] != "agent":
                errors.append("invalid_model_parent_or_duplicate")
            model_ids.add(model_id)
            pending = [
                (f"{model_id}:tool-{i}", model_id, c)
                for i, c in enumerate(event["reply"]["tool_calls"])
            ]
        elif event["type"] == "tool":
            tools.append(event)
            actual = (event["span_id"], event["parent_id"], event["call"])
            if not pending or actual != pending.pop(0):
                errors.append("tool_result_order_or_owner")
        else:
            errors.append("unknown_event")
    if pending:
        errors.append("missing_tool_result")
    expected = [{"phase": "UserPromptSubmit", "span_id": "agent"}]
    for event in tools:
        expected.extend(
            [
                {"phase": "PreToolUse", "span_id": event["span_id"]},
                {
                    "phase": "PostToolUse",
                    "span_id": event["span_id"],
                    "status": event["result"]["status"],
                },
            ]
        )
    expected.append({"phase": "Stop", "span_id": "agent", "status": report["status"]})
    if expected != report["hooks"]:
        errors.append("hook_coverage")
    return errors


def arguments(call):
    try:
        value = json.loads(call["arguments_json"])
        return value if isinstance(value, dict) else {"_raw_arguments_json": call["arguments_json"]}
    except ValueError:
        return {"_raw_arguments_json": call["arguments_json"]}


def native_samples(report, reference=None):
    from deepeval.test_case import ConversationalTestCase, LLMTestCase, ToolCall, Turn
    from ragas import MultiTurnSample, SingleTurnSample
    from ragas.messages import AIMessage, HumanMessage, ToolMessage
    from ragas.messages import ToolCall as RagasCall

    if trace_errors(report):
        raise ValueError("Trace ownership/order/hook validation failed")
    if report["status"] != "finished" or not isinstance(report["final_answer"], str):
        raise ValueError("Unfinished run has no completed response sample")
    metadata = {key: report[key] for key in ("run_id", "schema_version", "dataset_sha256", "split")}
    tools = [e for e in report["events"] if e["type"] == "tool"]
    metadata["tool_statuses"] = {e["span_id"]: e["result"]["status"] for e in tools}
    deep_tools = {
        e["span_id"]: ToolCall(
            name=e["call"]["name"], input_parameters=arguments(e["call"]), output=e["result"]
        )
        for e in tools
    }
    turns = [Turn(role="user", content=report["task"])]
    messages = [HumanMessage(content=report["task"])]
    for event in report["events"]:
        if event["type"] == "model":
            calls = event["reply"]["tool_calls"]
            ids = [f"{event['span_id']}:tool-{i}" for i in range(len(calls))]
            turns.append(
                Turn(
                    role="assistant",
                    content=event["reply"]["answer"],
                    tools_called=[deep_tools[i] for i in ids],
                    metadata={"span_id": event["span_id"]},
                )
            )
            messages.append(
                AIMessage(
                    content=event["reply"]["answer"],
                    tool_calls=[RagasCall(name=c["name"], args=arguments(c)) for c in calls],
                    metadata={"span_id": event["span_id"], "call_ids": ids},
                )
            )
        else:
            messages.append(
                ToolMessage(
                    content=json.dumps(event["result"], ensure_ascii=False),
                    metadata={"call_id": event["span_id"], "parent_id": event["parent_id"]},
                )
            )
    return {
        "metadata": metadata,
        "deepeval_single": LLMTestCase(
            input=report["task"],
            actual_output=report["final_answer"],
            expected_output=reference,
            tools_called=list(deep_tools.values()),
            metadata=metadata,
        ),
        "deepeval_conversation": ConversationalTestCase(turns=turns, metadata=metadata),
        "ragas_single": SingleTurnSample(
            user_input=report["task"], response=report["final_answer"], reference=reference
        ),
        "ragas_multi": MultiTurnSample(user_input=messages, reference=reference),
    }


def export_samples(report, reference=None):
    samples = native_samples(report, reference)
    return {
        k: v.model_dump(mode="json") if hasattr(v, "model_dump") else v for k, v in samples.items()
    }


def restore_samples(payload):
    """DeepEval's before-validator expects ToolCall objects, even after JSON loading."""
    from deepeval.test_case import ConversationalTestCase, LLMTestCase, ToolCall, Turn
    from ragas import MultiTurnSample, SingleTurnSample

    single = dict(payload["deepeval_single"])
    single["tools_called"] = [ToolCall.model_validate(c) for c in single["tools_called"]]
    turns = []
    for raw in payload["deepeval_conversation"]["turns"]:
        turn = dict(raw)
        turn["tools_called"] = [ToolCall.model_validate(c) for c in (turn["tools_called"] or [])]
        turns.append(Turn(**turn))
    conversation = dict(payload["deepeval_conversation"], turns=turns)
    return {
        "metadata": payload["metadata"],
        "deepeval_single": LLMTestCase(**single),
        "deepeval_conversation": ConversationalTestCase(**conversation),
        "ragas_single": SingleTurnSample.model_validate(payload["ragas_single"]),
        "ragas_multi": MultiTurnSample.model_validate(payload["ragas_multi"]),
    }
