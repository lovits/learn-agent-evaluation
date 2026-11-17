"""One observed run, three real SDK views. Conversion does not score the run."""

import json

from deepeval.test_case import LLMTestCase, ToolCall
from ragas.dataset_schema import MultiTurnSample, SingleTurnSample
from ragas.messages import AIMessage, HumanMessage, ToolMessage
from ragas.messages import ToolCall as RagasToolCall


def to_deepeval(run):
    return LLMTestCase(
        input=run["task"],
        actual_output=run["final_answer"] or "",
        tools_called=[
            ToolCall(name=e["name"], input_parameters=e["arguments"], output=e["result"])
            for e in run["events"]
        ],
    )


def to_ragas_single(run):
    return SingleTurnSample(user_input=run["task"], response=run["final_answer"] or "")


def to_ragas_multi(run):
    messages = []
    for message in run["messages"]:
        content = message["content"]
        if message["role"] == "user":
            messages.append(HumanMessage(content=content))
        elif message["role"] == "assistant":
            calls = [
                RagasToolCall(name=c["name"], args=json.loads(c["arguments_json"]))
                for c in content["tool_calls"]
            ]
            messages.append(AIMessage(content=content["answer"], tool_calls=calls or None))
        else:
            messages.append(ToolMessage(content=json.dumps(content, ensure_ascii=False)))
    return MultiTurnSample(user_input=messages)


def export(run):
    return {
        "run_id": run["run_id"],
        "run_status": run["status"],
        "deepeval": to_deepeval(run).model_dump(mode="json"),
        "ragas_single": to_ragas_single(run).model_dump(mode="json"),
        "ragas_multi": to_ragas_multi(run).model_dump(mode="json"),
    }
