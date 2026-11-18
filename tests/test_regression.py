import json

import pytest

from course.e16_regression.code import REPAIR, run_case
from course.e16_regression.eval import evaluate_run, gate
from eval_course.knowledge import PROJECT


def test_gate_requires_every_pair_and_separates_rejection_from_missing_evidence():
    def row(case, version, accepted):
        return {"case_id": case, "version": version, "evaluation": {"accepted": accepted}}

    rows = [
        row("new", "baseline", False),
        row("new", "candidate", True),
        row("guard", "baseline", True),
        row("guard", "candidate", True),
    ]
    assert gate(rows, ["new", "guard"])["decision"] == "accept_in_scope"
    assert gate(rows[:-1], ["new", "guard"])["decision"] == "blocked"
    assert (
        gate(rows[:-1] + [row("guard", "candidate", None)], ["new", "guard"])["decision"]
        == "blocked"
    )
    assert (
        gate(rows[:-1] + [row("guard", "candidate", False)], ["new", "guard"])["decision"]
        == "reject"
    )
    assert (
        gate([row("guard", "baseline", True), row("guard", "candidate", True)], ["guard"])[
            "decision"
        ]
        == "no_regression_observed"
    )
    with pytest.raises(ValueError, match="Duplicate"):
        gate(rows + rows[:1], ["new", "guard"])


def test_integrated_fixture_runs_real_tools_and_external_checks(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    case = json.loads((PROJECT / "course/e16_regression/cases.jsonl").read_text().splitlines()[0])
    run, workspace = run_case(case, "candidate", root=PROJECT / "knowledge_base")
    result = evaluate_run(run, workspace, {**case, "fixture_completion": 1})
    assert result["accepted"] is True and result["contract"]["score"] == 1
    assert run["model_inputs"][0][0]["content"].endswith(REPAIR)
    assert run["responses"] and all("model" not in r for r in run["responses"])
    assert any("billing.md" in c for c in run["sample"]["retrieval_context"])
    (workspace / "policy.txt").write_text("changed")
    assert evaluate_run(run, workspace, {**case, "fixture_completion": 1})["accepted"] is False
