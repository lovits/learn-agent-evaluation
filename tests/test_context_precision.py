import pytest
from deepeval.test_case import LLMTestCase

from course.e06_context_precision.eval import judge_precision, judge_relevancy, ranking
from eval_course.judge import JudgeModel


def test_same_relevant_count_has_different_order_scores():
    front, middle, last = [ranking(labels) for labels in [[1, 0, 0], [0, 1, 0], [0, 0, 1]]]
    assert front["precision"] == middle["precision"] == last["precision"] == 1 / 3
    assert front["list_ap"] == front["rr"] == front["ndcg"] == 1
    assert middle["list_ap"] == middle["rr"] == 0.5
    assert last["list_ap"] == last["rr"] == 1 / 3
    assert front["ndcg"] > middle["ndcg"] > last["ndcg"]
    assert ranking([1, 0, 0, 0])["list_ap"] == 1
    assert ranking([1, 0, 0, 0])["precision"] == 0.25
    assert ranking([1, 0, 1])["list_ap"] == pytest.approx((1 + 2 / 3) / 2)
    assert all(value is None for value in ranking([]).values())
    assert all(value == 0 for value in ranking([0, 0]).values())
    with pytest.raises(ValueError):
        ranking([1, 2])


def test_native_metrics_use_different_units_without_a_generated_answer(monkeypatch):
    model = JudgeModel()
    rows = [
        {"statement": "irrelevant", "verdict": "no", "reason": "Controlled fixture"},
        {"statement": "useful", "verdict": "yes", "reason": "Controlled fixture"},
    ]
    monkeypatch.setattr(
        model, "generate", lambda prompt, schema=None: schema.model_validate({"verdicts": rows})
    )
    sample = LLMTestCase(
        input="question", expected_output="reference", retrieval_context=["first", "second"]
    )
    assert sample.actual_output is None
    precision = judge_precision(sample, model)
    relevancy = judge_relevancy(sample, model)
    assert precision["status"] == relevancy["status"] == "ok"
    assert precision["score"] == relevancy["score"] == 0.5
    assert len(precision["verdicts"]) == 2
    assert sum(len(group["verdicts"]) for group in relevancy["statements_by_context"]) == 4


def test_missing_chunk_verdict_is_an_alignment_error(monkeypatch):
    model = JudgeModel()
    monkeypatch.setattr(
        model,
        "generate",
        lambda prompt, schema=None: schema.model_validate(
            {"verdicts": [{"verdict": "yes", "reason": "Controlled missing verdict"}]}
        ),
    )
    sample = LLMTestCase(
        input="question", expected_output="reference", retrieval_context=["first", "second"]
    )
    result = judge_precision(sample, model)
    assert result["status"] == "error"
    assert result["score"] is result["passed"] is None
