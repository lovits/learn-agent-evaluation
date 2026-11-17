"""Inspect the native three-stage judgment before interpreting its aggregate."""

from deepeval.metrics import FaithfulnessMetric

from course.e04_scoring.eval import score


def aggregate(labels, penalize_ambiguous=False):
    if any(label not in {"yes", "no", "borderline"} for label in labels):
        raise ValueError("Expected yes, no or borderline")
    if not labels:
        return None
    passing = {"yes"} if penalize_ambiguous else {"yes", "borderline"}
    return sum(label in passing for label in labels) / len(labels)


def judge_faithfulness(sample, model):
    metric = FaithfulnessMetric(
        model=model, eval_mode="llm", async_mode=False, include_reason=False
    )
    result = score(metric, sample)
    sdk_score = result["score"]
    claims = getattr(metric, "claims", [])
    verdicts = [v.model_dump(mode="json") for v in getattr(metric, "verdicts", [])]
    if result["status"] == "ok":
        if not claims:
            result.update(
                status="not_applicable",
                score=None,
                passed=None,
                reason="No factual claims extracted; inspect the answer separately",
            )
        elif len(verdicts) != len(claims):
            result.update(
                status="error",
                score=None,
                passed=None,
                reason="Expected one verdict per extracted claim",
            )
    return {
        **result,
        "sdk_score": sdk_score,
        "truths": getattr(metric, "truths", []),
        "claims": claims,
        "verdicts": verdicts,
        "support_score": aggregate([v["verdict"] for v in verdicts], True)
        if result["status"] == "ok"
        else None,
    }
