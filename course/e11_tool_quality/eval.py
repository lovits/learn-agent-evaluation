"""Compare the native reference match modes, then inspect semantic arguments."""

from deepeval.metrics import ArgumentCorrectnessMetric, ToolCorrectnessMetric
from deepeval.test_case import ToolCall, ToolCallParams

from course.e02_samples.samples import to_deepeval
from course.e04_scoring.eval import score


def sample_for(run, expected):
    sample = to_deepeval(run)
    sample.expected_tools = [
        ToolCall(name=c["name"], input_parameters=c["arguments"], output=c["result"])
        for c in expected
    ]
    return sample


def tool_scores(sample, model):
    params = [ToolCallParams.INPUT_PARAMETERS]
    modes = {
        "names": {},
        "arguments": {"evaluation_params": params},
        "ordered_arguments": {"evaluation_params": params, "should_consider_ordering": True},
        "exact_arguments": {"evaluation_params": params, "should_exact_match": True},
        "exact_outputs": {
            "evaluation_params": params + [ToolCallParams.OUTPUT],
            "should_exact_match": True,
        },
    }
    return {
        name: score(
            ToolCorrectnessMetric(model=model, eval_mode="llm", async_mode=False, **options), sample
        )
        for name, options in modes.items()
    }


def judge_arguments(sample, model):
    metric = ArgumentCorrectnessMetric(
        model=model, eval_mode="llm", async_mode=False, include_reason=False
    )
    result = score(metric, sample)
    sdk_score = result["score"]
    verdicts = [v.model_dump(mode="json") for v in getattr(metric, "verdicts", [])]
    if result["status"] == "ok":
        if not sample.tools_called:
            result.update(
                status="not_applicable",
                score=None,
                passed=None,
                reason="No arguments were observed; check required calls separately",
            )
        elif len(verdicts) != len(sample.tools_called):
            result.update(
                status="error",
                score=None,
                passed=None,
                reason="Expected one verdict per observed call",
            )
    return {**result, "sdk_score": sdk_score, "verdicts": verdicts}
