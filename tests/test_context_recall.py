import pytest
from deepeval.test_case import LLMTestCase

from course.e07_context_recall.code import summarize
from course.e07_context_recall.eval import coverage, judge_recall
from eval_course.judge import JudgeModel


def test_document_and_fact_denominators_and_incomplete_reference():
    facts = [
        {"id": "a", "text": "command", "source": "release"},
        {"id": "b", "text": "condition", "source": "release"},
        {"id": "c", "text": "retention", "source": "logs"},
    ]
    result = summarize([{"path": "release"}], facts)
    assert result["precision"] == 1
    assert result["document_recall"] == 0.5
    assert result["fact_recall"] == pytest.approx(2 / 3)
    assert result["missing"] == ["retention"]
    assert summarize([{"path": "release"}], facts[:2])["fact_recall"] == 1
    assert coverage([], ["release"]) is None
    assert coverage(["release"], []) == 0
    assert coverage(["release"], ["release", "release"]) == 1


def test_native_attribution_and_empty_judgment_are_distinct(monkeypatch):
    model = JudgeModel()
    sample = LLMTestCase(input="question", expected_output="a. b. c.", retrieval_context=["a. b."])
    rows = [{"verdict": v, "reason": "Controlled fixture"} for v in ["yes", "yes", "no"]]
    monkeypatch.setattr(
        model, "generate", lambda prompt, schema=None: schema.model_validate({"verdicts": rows})
    )
    result = judge_recall(sample, model)
    assert sample.actual_output is None
    assert result["status"] == "ok"
    assert result["score"] == pytest.approx(2 / 3)
    rows.clear()
    result = judge_recall(sample, model)
    assert result["status"] == "error"
    assert result["score"] is result["passed"] is None
    sample.expected_output = "   "
    assert judge_recall(sample, model)["status"] == "error"
