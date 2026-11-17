import pytest
from deepeval.test_case import LLMTestCase

from course.e09_answer_quality.eval import fact_scores, judge_relevance, task_metric
from eval_course.judge import JudgeModel


def test_fact_precision_recall_and_beta_keep_distinct_denominators():
    result = fact_scores(["command"], ["command", "gate", "fix"])
    assert (result["tp"], result["fp"], result["fn"]) == (1, 0, 2)
    assert result["precision"] == 1
    assert result["recall"] == pytest.approx(1 / 3)
    assert result["fbeta"] == 0.5
    assert (
        fact_scores(["command"], ["command", "gate"], 2)["fbeta"]
        < fact_scores(["command"], ["command", "gate"], 0.5)["fbeta"]
    )
    assert fact_scores([], ["command"])["precision"] is None
    assert fact_scores([], ["command"])["fbeta"] == 0
    assert fact_scores([], [])["fbeta"] is None
    assert fact_scores(["command", "command"], ["command"])["fbeta"] == 1
    with pytest.raises(ValueError):
        fact_scores([], [], 0)


def test_native_relevance_cannot_check_factual_correctness(monkeypatch):
    model = JudgeModel()

    def generate(prompt, schema=None):
        data = {
            "Statements": {"statements": ["wrong but on-topic"]},
            "Verdicts": {"verdicts": [{"verdict": "yes"}]},
        }
        return schema.model_validate(data[schema.__name__])

    monkeypatch.setattr(model, "generate", generate)
    sample = LLMTestCase(
        input="Which command?", actual_output="Wrong command", expected_output="Correct command"
    )
    result = judge_relevance(sample, model)
    assert result["status"] == "ok" and result["score"] == 1
    monkeypatch.setattr(
        model,
        "generate",
        lambda prompt, schema=None: schema.model_validate({"statements": [], "verdicts": []}),
    )
    assert judge_relevance(sample, model)["status"] == "not_applicable"


def test_quality_rubric_receives_agent_evidence_and_reference():
    from deepeval.test_case import SingleTurnParams

    metric = task_metric(JudgeModel())
    assert SingleTurnParams.RETRIEVAL_CONTEXT in metric.evaluation_params
    assert SingleTurnParams.EXPECTED_OUTPUT in metric.evaluation_params
    assert metric.threshold == 1


def test_live_quality_uses_four_fields_and_keeps_the_full_tool_trace(monkeypatch, tmp_path):
    import json

    from deepeval.test_case import ToolCall

    from course.e09_answer_quality import code

    sample = LLMTestCase(
        input="Which command?",
        actual_output="pytest",
        expected_output="pytest",
        retrieval_context=["pytest"],
        tools_called=[ToolCall(name="search_knowledge")],
    )
    serialized = sample.model_dump(mode="json")
    monkeypatch.setattr("sys.argv", ["lesson", "--live", "--judge"])
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setattr(
        code,
        "prepare",
        lambda: (
            {"query": "question", "reference": "pytest", "sources": {"atlas/release.md": "hash"}},
            [],
            {},
        ),
    )
    monkeypatch.setattr(code, "prepare_workspace", lambda *args: tmp_path)
    monkeypatch.setattr(
        code, "run_task", lambda *args, **kwargs: {"status": "finished", "sample": serialized}
    )
    monkeypatch.setattr(code, "judge_relevance", lambda sample, model: {"status": "ok"})
    monkeypatch.setattr(code, "score", lambda metric, sample: {"status": "ok"})
    assert code.main() == 0
    report = json.loads(next(tmp_path.glob("e09-suite-*.json")).read_text())
    assert (
        report["conditions"]["live_agent"]["sample"]["tools_called"][0]["name"]
        == "search_knowledge"
    )
