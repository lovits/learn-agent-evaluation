"""Separate binary ranking arithmetic from native DeepEval model judgments."""

import math

from deepeval.metrics import ContextualPrecisionMetric, ContextualRelevancyMetric

from course.e04_scoring.eval import score


def ranking(labels):
    if any(type(label) is not int or label not in {0, 1} for label in labels):
        raise ValueError("Ranking labels must be integer 0 or 1")
    if not labels:
        return dict.fromkeys(["precision", "list_ap", "rr", "ndcg"])
    relevant = sum(labels)
    cumulative, weighted = 0, 0.0
    for position, label in enumerate(labels, 1):
        cumulative += label
        weighted += label * cumulative / position
    dcg = sum(label / math.log2(i + 1) for i, label in enumerate(labels, 1))
    ideal = sum(1 / math.log2(i + 1) for i in range(1, relevant + 1))
    return {
        "precision": relevant / len(labels),
        "list_ap": weighted / relevant if relevant else 0.0,
        "rr": next((1 / i for i, label in enumerate(labels, 1) if label), 0.0),
        "ndcg": dcg / ideal if ideal else 0.0,
    }


def judge_precision(sample, model):
    metric = ContextualPrecisionMetric(
        model=model, eval_mode="llm", async_mode=False, include_reason=False
    )
    result = score(metric, sample)
    verdicts = getattr(metric, "verdicts", [])
    if result["status"] == "ok" and len(verdicts) != len(sample.retrieval_context):
        result.update(
            status="error",
            score=None,
            passed=None,
            reason="Expected one verdict per string context",
        )
    return {**result, "verdicts": [v.model_dump(mode="json") for v in verdicts]}


def judge_relevancy(sample, model):
    metric = ContextualRelevancyMetric(
        model=model, eval_mode="llm", async_mode=False, include_reason=False
    )
    result = score(metric, sample)
    return {
        **result,
        "statements_by_context": [
            v.model_dump(mode="json") for v in getattr(metric, "verdicts_list", [])
        ],
    }
