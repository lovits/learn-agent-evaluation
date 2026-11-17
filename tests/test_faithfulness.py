import pytest
from deepeval.test_case import LLMTestCase

from course.e08_faithfulness.eval import aggregate, judge_faithfulness
from eval_course.judge import JudgeModel


def test_borderline_policy_and_empty_denominator():
    labels = ["yes", "borderline", "no"]
    assert aggregate(labels) == pytest.approx(2 / 3)
    assert aggregate(labels, True) == pytest.approx(1 / 3)
    assert aggregate([]) is None
    assert aggregate(["no"], True) == 0
    with pytest.raises(ValueError):
        aggregate(["unknown"])


def controlled_model(monkeypatch, claims, verdicts):
    model = JudgeModel()

    def generate(prompt, schema=None):
        values = {
            "Truths": {"truths": ["supported fact"]},
            "Claims": {"claims": claims},
            "Verdicts": {"verdicts": verdicts},
        }
        return schema.model_validate(values[schema.__name__])

    monkeypatch.setattr(model, "generate", generate)
    return model


def test_native_default_policy_and_supported_fraction_share_verdicts(monkeypatch):
    model = controlled_model(
        monkeypatch,
        ["supported", "unmentioned"],
        [{"verdict": "yes"}, {"verdict": "borderline", "reason": "unmentioned"}],
    )
    sample = LLMTestCase(input="question", actual_output="answer", retrieval_context=["evidence"])
    result = judge_faithfulness(sample, model)
    assert result["status"] == "ok"
    assert result["score"] == result["sdk_score"] == 1
    assert result["support_score"] == 0.5
    assert result["claims"] == ["supported", "unmentioned"]


def test_empty_claims_and_missing_verdict_are_not_valid_perfect_scores(monkeypatch):
    sample = LLMTestCase(
        input="question", actual_output="I do not know", retrieval_context=["fact"]
    )
    result = judge_faithfulness(sample, controlled_model(monkeypatch, [], []))
    assert result["status"] == "not_applicable"
    assert result["sdk_score"] == 1
    assert result["score"] is result["passed"] is result["support_score"] is None
    result = judge_faithfulness(
        sample, controlled_model(monkeypatch, ["one", "two"], [{"verdict": "yes"}])
    )
    assert result["status"] == "error"
    assert result["score"] is result["support_score"] is None
