import json

import pytest

from course.e11_tool_quality.code import run_case
from course.e11_tool_quality.eval import judge_arguments, sample_for, tool_scores
from eval_course.judge import JudgeModel
from eval_course.knowledge import PROJECT


def cases():
    return {
        c["id"]: c
        for c in (
            json.loads(line)
            for line in (PROJECT / "course/e11_tool_quality/cases.jsonl").read_text().splitlines()
        )
    }


def test_native_match_modes_distinguish_parameters_order_and_extra_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    model, rows = JudgeModel(), cases()
    results = {}
    for name in ["baseline", "wrong_path", "reordered", "extra_read", "missing_readback"]:
        case = rows[name]
        results[name] = tool_scores(sample_for(run_case(case), case["expected_calls"]), model)
    assert all(v["score"] == 1 for v in results["baseline"].values())
    assert results["wrong_path"]["names"]["score"] == 1
    assert results["wrong_path"]["arguments"]["score"] == 0.5
    assert results["reordered"]["arguments"]["score"] == 1
    assert results["reordered"]["ordered_arguments"]["score"] == pytest.approx(2 / 3)
    assert results["extra_read"]["ordered_arguments"]["score"] == 1
    assert results["extra_read"]["exact_arguments"]["score"] == 0
    assert results["missing_readback"]["names"]["score"] == pytest.approx(2 / 3)
    assert model.calls == []


def test_correct_arguments_can_fail_and_legal_alternatives_can_differ(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    rows, model = cases(), JudgeModel()
    blocked = rows["tool_failed"]
    run = run_case(blocked)
    scores = tool_scores(sample_for(run, blocked["expected_calls"]), model)
    assert scores["exact_arguments"]["score"] == 1
    assert scores["exact_outputs"]["score"] == 0
    assert run["events"][1]["result"]["status"] == "error"
    alternative = run_case(rows["bash_alternative"])
    assert alternative["artifact"]["content"] == rows["baseline"]["files"]["source.txt"]
    assert (
        tool_scores(sample_for(alternative, rows["baseline"]["expected_calls"]), model)["names"][
            "score"
        ]
        == 0
    )
    recovery = run_case(rows["permission_recovery"])
    assert recovery["events"][0]["result"]["status"] == "denied"
    assert recovery["artifact"]["content"] == "blocked"
    assert all(e["name"] != "bash" for e in recovery["events"])


def test_no_calls_are_not_evidence_of_correct_arguments(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    case = cases()["no_calls"]
    model = JudgeModel()
    result = judge_arguments(sample_for(run_case(case), case["expected_calls"]), model)
    assert result["sdk_score"] == 1
    assert result["status"] == "not_applicable"
    assert result["score"] is None
