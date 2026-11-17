"""One observed run, one DeepEval sample. Conversion does not score the run."""

from deepeval.test_case import LLMTestCase, ToolCall


def to_deepeval(run):
    return LLMTestCase(
        input=run["task"],
        actual_output=run["final_answer"] or "",
        tools_called=[
            ToolCall(name=e["name"], input_parameters=e["arguments"], output=e["result"])
            for e in run["events"]
        ],
    )


def export(run):
    return {
        "run_id": run["run_id"],
        "run_status": run["status"],
        "deepeval": to_deepeval(run).model_dump(mode="json"),
    }
