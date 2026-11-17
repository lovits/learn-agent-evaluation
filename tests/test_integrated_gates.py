import json

from integrated_agent.gates import review_context_gate
from integrated_agent.runtime import PROJECT


def test_actual_workflow_context_bad_case_remains_blocked_in_ci():
    case = json.loads((PROJECT / "integrated_agent/cases/regression.jsonl").read_text())
    report = json.loads((PROJECT / case["source_report"]).read_text())
    assert report["result"]["task"]["status"] == "completed"
    gate = review_context_gate(case["visible_files"], case["known_project_files"])
    assert not gate["passed"] and gate["status"] == case["expected_gate"]
    assert gate["missing_known_test_files"] == ["test_checkout.py", "test_shipping.py"]
    assert gate["semantic_correctness"] is None


def test_complete_test_context_only_makes_review_eligible_not_correct():
    files = ["shipping.py", "checkout.py", "test_shipping.py", "test_checkout.py"]
    result = review_context_gate(files, files)
    assert result["passed"] and result["status"] == "eligible_for_semantic_review"
    assert result["semantic_correctness"] is None
