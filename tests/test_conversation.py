import json

from deepeval.metrics import ConversationCompletenessMetric, KnowledgeRetentionMetric
from deepeval.metrics.conversation_completeness.schema import ConversationCompletenessVerdict
from deepeval.metrics.knowledge_retention.schema import KnowledgeRetentionVerdict

from course.e13_conversation.code import run_case
from course.e13_conversation.eval import active_requirements, check_delivery
from eval_course.judge import JudgeModel
from eval_course.knowledge import PROJECT


def data():
    folder = PROJECT / "course/e13_conversation"
    return json.loads((folder / "scenario.json").read_text()), [
        json.loads(line) for line in (folder / "cases.jsonl").read_text().splitlines()
    ]


def test_user_updates_replace_and_cancel_without_losing_other_constraints():
    scenario, _ = data()
    state = active_requirements(scenario["history"])
    assert state["active"]["path"] == "summary.md"
    assert state["sources"]["path"] == "u2"
    assert state["sources"]["preserve"] == "u1"
    assert state["active"]["language"] == "zh"
    assert "max_chars" not in state["active"]
    assert any(x["key"] == "max_chars" and x["value"] == 40 for x in state["superseded"])
    assert len(state["active"]["body"]) > 40


def test_real_artifacts_and_actual_contexts_distinguish_controlled_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    scenario, cases = data()
    result = {}
    for case in cases:
        run, workspace = run_case(scenario, case)
        result[case["id"]] = check_delivery(run, workspace, scenario)
    assert {k for k, v in result.items() if v["passed"]} == {
        "full_correct",
        "current_memory",
        "archive_recovery",
    }
    assert result["full_old"]["expected_path_in_first_input"]
    assert not result["stale_memory"]["expected_path_in_first_input"]
    assert not result["tail_only"]["expected_path_in_first_input"]
    assert result["archive_recovery"]["archive_read"]


def test_archive_recovery_uses_real_tool_result_without_reference_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    scenario, cases = data()
    case = next(c for c in cases if c["id"] == "archive_recovery")
    run, workspace = run_case(scenario, case)
    archive = json.loads((workspace / "conversation.json").read_text())
    assert all(set(t) == {"id", "role", "content"} for t in archive)
    assert "summary.md" not in json.dumps(run["model_inputs"][0], ensure_ascii=False)
    assert "summary.md" in json.dumps(run["model_inputs"][1], ensure_ascii=False)
    (workspace / "policy.txt").unlink()
    assert not check_delivery(run, workspace, scenario)["checks"]["policy_unchanged"]


def test_native_conversational_polarities_are_opposite():
    model = JudgeModel()
    retention = KnowledgeRetentionMetric(model=model, eval_mode="llm", async_mode=False)
    retention.verdicts = [
        KnowledgeRetentionVerdict(verdict="yes"),
        KnowledgeRetentionVerdict(verdict="no"),
    ]
    completeness = ConversationCompletenessMetric(model=model, eval_mode="llm", async_mode=False)
    completeness.verdicts = [
        ConversationCompletenessVerdict(verdict="yes"),
        ConversationCompletenessVerdict(verdict="yes"),
    ]
    assert retention._calculate_score() == 0.5
    assert completeness._calculate_score() == 1
    assert model.calls == []


def test_missing_verdicts_and_empty_intentions_do_not_become_perfect_scores(monkeypatch):
    from deepeval.metrics.knowledge_retention.schema import Knowledge

    from course.e13_conversation.eval import conversation_sample, conversational_scores

    scenario, _ = data()
    sample = conversation_sample({"final_answer": "summary.md"}, scenario)

    def missing(metric, test_case, **kwargs):
        metric.knowledges = [Knowledge(data={"path": "report.md"})] + [None] * 5
        metric.verdicts = [None, None, None]
        return 1.0

    def empty(metric, test_case, **kwargs):
        metric.user_intentions = []
        metric.verdicts = []
        return 1.0

    monkeypatch.setattr(KnowledgeRetentionMetric, "measure", missing)
    monkeypatch.setattr(ConversationCompletenessMetric, "measure", empty)
    model = JudgeModel()
    result = conversational_scores(sample, model)
    assert result["retention"]["status"] == "error"
    assert result["retention"]["score"] is None
    assert result["retention"]["sdk_score"] == 1
    assert result["completeness"]["status"] == "not_applicable"
    assert result["completeness"]["score"] is None
    assert model.calls == []
