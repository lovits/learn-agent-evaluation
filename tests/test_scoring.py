import json
from io import StringIO

from deepeval.test_case import LLMTestCase

from course.e04_scoring.eval import UploadContract, explanation_metric, score, set_scores
from eval_course.judge import JudgeModel


def test_rules_do_not_pretend_to_understand_explanation():
    value = {
        "required_header": "X-Project-Token",
        "max_bytes": 1048576,
        "explanation": "A deliberately wrong explanation",
    }
    sample = LLMTestCase(input="Return upload policy", actual_output=json.dumps(value))
    assert score(UploadContract(), sample)["score"] == 1
    value["max_bytes"] = "1048576"
    sample.actual_output = json.dumps(value)
    assert score(UploadContract(), sample)["score"] == 0
    sample.actual_output = "not JSON"
    assert score(UploadContract(), sample)["status"] == "ok"


def test_failed_judge_is_not_an_answer_score(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("Controlled transport failure")

    monkeypatch.setattr("eval_course.judge.urlopen", unavailable)
    sample = LLMTestCase(input="task", actual_output="answer", expected_output="reference")
    result = score(explanation_metric(JudgeModel()), sample)
    assert result["status"] == "error"
    assert result["score"] is result["passed"] is None


def test_malformed_judge_payload_is_not_a_zero(monkeypatch):
    sample = LLMTestCase(input="task", actual_output="answer", expected_output="reference")
    for payload in [{"text": '{"score":"wrong","reason":"x"}'}, {"text": None}]:
        monkeypatch.setattr(
            "eval_course.judge.urlopen",
            lambda *args, payload=payload, **kwargs: StringIO(json.dumps(payload)),
        )
        result = score(explanation_metric(JudgeModel()), sample)
        assert result["status"] == "error" and result["score"] is None


def test_set_units_and_empty_denominators():
    assert set_scores(["a", "a", "extra"], ["a", "b", "c"]) == {
        "precision": 0.5,
        "recall": 1 / 3,
        "f1": 0.4,
    }
    assert set_scores([], ["a"]) == {"precision": None, "recall": 0, "f1": 0}
    assert set_scores([], []) == {"precision": None, "recall": None, "f1": None}
