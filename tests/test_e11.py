import asyncio
import json

import pytest
from deepeval.test_case import LLMTestCase

from lessons.e11_task_completion.code import GoalState, run_case
from lessons.e11_task_completion.eval import custom_scores
from lessons.e11_task_completion.metrics import ExternalCompletionMetric, composite, evidence_score
from lessons.e11_task_completion.verify import HERE, probe

CORRECT = """def shipping_fee(weight_grams, expedited=False):
    if type(weight_grams) is not int or type(expedited) is not bool:
        raise TypeError("invalid types")
    if weight_grams < 1 or weight_grams > 5000:
        raise ValueError("invalid weight")
    return 600 + ((weight_grams - 1) // 1000) * 200 + (300 if expedited else 0)
"""


def case():
    return json.loads((HERE / "cases.jsonl").read_text())


def prepare(tmp_path, source=CORRECT):
    for n, text in case()["files"].items():
        (tmp_path / n).write_text(text)
    (tmp_path / "shipping.py").write_text(source)
    return tmp_path


def test_executes_boundary_type_and_exception_checks(tmp_path):
    checks = [
        {
            "id": "started",
            "arguments": {"weight_grams": 1001},
            "expected": {"value": 800, "type": "int"},
        },
        {
            "id": "upper",
            "arguments": {"weight_grams": 5000, "expedited": True},
            "expected": {"value": 1700, "type": "int"},
        },
        {"id": "bool", "arguments": {"weight_grams": True}, "expected": {"exception": "TypeError"}},
        {"id": "range", "arguments": {"weight_grams": 0}, "expected": {"exception": "ValueError"}},
    ]
    result = probe(prepare(tmp_path), case(), checks)
    assert result["passed"] is True
    (tmp_path / "test_shipping.py").unlink()
    result = probe(tmp_path, case(), checks)
    assert result["passed"] is False
    assert all(r["passed"] for r in result["cases"])


def test_false_claim_and_partial_repair_are_distinct(tmp_path):
    c = case()
    public = json.loads((HERE / "public_cases.json").read_text())
    initial = c["files"]["shipping.py"]
    assert probe(prepare(tmp_path, initial), c, public)["passed"] is False
    partial = initial.replace("(weight_grams - 1000) // 1000", "(weight_grams - 1) // 1000")
    prepare(tmp_path, partial)
    assert probe(tmp_path, c, public)["passed"] is True
    private = [
        {
            "id": "negative",
            "arguments": {"weight_grams": -1},
            "expected": {"exception": "ValueError"},
        }
    ]
    assert probe(tmp_path, c, private)["passed"] is False


@pytest.mark.parametrize(
    "source",
    [
        "import math\n" + CORRECT,
        "def broken(:\n",
        CORRECT.replace("weight_grams, expedited=False", "weight, expedited=False"),
    ],
)
def test_unsupported_or_invalid_submission_is_unscored(tmp_path, source):
    result = probe(
        prepare(tmp_path, source), case(), json.loads((HERE / "public_cases.json").read_text())
    )
    assert result["status"] == "unscored" and result["passed"] is None
    assert custom_scores(result)["status"] == "unscored"


def test_limited_stop_review_does_not_claim_global_completion():
    goal = GoalState("Public tests only")
    assert goal.review({"status": "scored", "passed": False}, 2) == "blocked"
    assert goal.review({"status": "scored", "passed": False}, 2) == "limit"
    assert (
        GoalState("Public tests only").review({"status": "scored", "passed": True}, 2)
        == "ready_for_external_verification"
    )
    assert GoalState("Public tests only").review({"status": "unscored"}, 2) == "review_error"


def test_nonterminating_submission_is_unscored(tmp_path):
    source = "def shipping_fee(weight_grams, expedited=False):\n    while True:\n        pass\n"
    result = probe(
        prepare(tmp_path, source), case(), json.loads((HERE / "public_cases.json").read_text())
    )
    assert result["status"] == "unscored" and result["passed"] is None
    assert "error" in result


def test_declared_impossible_goal_does_not_call_model(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))

    def model(*args):
        pytest.fail("A declared contradictory contract must not call the model")

    c = {**case(), "constraints": {"retain_public_tests": True, "delete_all_tests": True}}
    row = run_case(c, model_fn=model)
    assert row["goal"]["status"] == "impossible"
    assert row["turns"] == [] and row["tool_snapshots"] == []


def test_continuation_sees_prior_actual_tool_results(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    requests = []

    def model(messages, tools):
        requests.append(messages.copy())
        if len(requests) == 1:
            reply = {"answer": "done", "tool_calls": []}
        elif len(requests) == 2:
            reply = {
                "answer": "repair",
                "tool_calls": [
                    {
                        "name": "write_file",
                        "arguments_json": json.dumps({"path": "shipping.py", "content": CORRECT}),
                    }
                ],
            }
        else:
            reply = {"answer": "repaired", "tool_calls": []}
        return {"reply": reply}

    row = run_case(case(), premature=True, model_fn=model)
    assert [t["goal_status"] for t in row["turns"]] == [
        "blocked",
        "ready_for_external_verification",
    ]
    assert requests[1][0]["role"] == "user"
    assert requests[1][1]["content"]["answer"] == "done"
    assert any(m["role"] == "tool" and m["content"][0]["status"] == "ok" for m in requests[2])


@pytest.mark.parametrize("checks, expected", [({"a": True}, 1.0), ({"a": False}, 0.0)])
def test_native_custom_sync_async_parity(checks, expected):
    scores = custom_scores({"status": "scored", "checks": checks})
    assert scores["parity"] and scores["deepeval_sync"] == expected


def test_metric_reset_after_error_and_composite_does_not_hide_failure():
    metric = ExternalCompletionMetric()
    bad = LLMTestCase(input="x", actual_output="y", additional_metadata={})
    with pytest.raises(ValueError):
        metric.measure(bad)
    assert metric.score is None and metric.is_successful() is False
    good = LLMTestCase(
        input="x",
        actual_output="y",
        additional_metadata={"external_evidence": {"status": "scored", "checks": {"x": True}}},
    )
    assert asyncio.run(metric.a_measure(good)) == 1
    assert metric.error is None and metric.is_successful() is True
    assert composite(0, 1)["score"] == 0
    assert composite(None, 1)["score"] is None
    with pytest.raises(ValueError):
        evidence_score({"status": "scored", "checks": {"x": "true"}})
    with pytest.raises(ValueError):
        composite(float("nan"), 1)
