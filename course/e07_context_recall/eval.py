"""Keep authored evidence coverage separate from native semantic attribution."""

from deepeval.metrics import ContextualRecallMetric

from course.e04_scoring.eval import score


def coverage(required, found):
    required, found = set(required), set(found)
    return len(required & found) / len(required) if required else None


def judge_recall(sample, model):
    if not sample.expected_output or not sample.expected_output.strip():
        return {
            "status": "error",
            "score": None,
            "passed": None,
            "reason": "Reference must contain facts",
            "verdicts": [],
        }
    metric = ContextualRecallMetric(
        model=model, eval_mode="llm", async_mode=False, include_reason=False
    )
    result = score(metric, sample)
    verdicts = [v.model_dump(mode="json") for v in getattr(metric, "verdicts", [])]
    if result["status"] == "ok" and not verdicts:
        result.update(
            status="error",
            score=None,
            passed=None,
            reason="Judge returned no attribution decisions",
        )
    return {**result, "verdicts": verdicts}
