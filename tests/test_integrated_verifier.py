import json

import pytest

from integrated_agent.runtime import PROJECT
from integrated_agent.verify import grade_foundation


@pytest.fixture
def repaired(tmp_path):
    case = json.loads((PROJECT / "integrated_agent/cases/foundation.json").read_text())
    criteria = json.loads((PROJECT / "evaluation_private/e16-foundation.json").read_text())
    for name, text in case["files"].items():
        (tmp_path / name).write_text(text)
    path = tmp_path / "shipping.py"
    path.write_text(
        path.read_text().replace("(weight_grams - 1000) // 1000", "(weight_grams - 1) // 1000")
    )
    path = tmp_path / "checkout.py"
    path.write_text(
        path.read_text().replace(
            "shipping_fee(weight_grams)", "shipping_fee(weight_grams, expedited)"
        )
    )
    return tmp_path, case, criteria


def add_memory(workspace):
    root = workspace / ".memory"
    root.mkdir()
    (root / "pricing.md").write_text(
        "---\nname: Pricing\ndescription: Shipping contract\ntype: project\n---\n1001 grams costs 800 cents.\n"
    )
    (root / "MEMORY.md").write_text("- [Pricing](pricing.md) - Shipping contract\n")


def test_actual_business_execution_accepts_valid_native_memory_separately(repaired):
    workspace, case, criteria = repaired
    add_memory(workspace)
    result = grade_foundation(workspace, case, criteria)
    assert result["passed"] and result["memory_state"]["index_matches_records"]
    assert len(result["behavior"]["core"]["cases"]) == 22
    assert len(result["behavior"]["quote_via_bound_core"]["cases"]) == 22
    assert result["full_17_mechanism_acceptance"] is False


def test_memory_scope_does_not_allow_executable_files_or_stale_index(repaired):
    workspace, case, criteria = repaired
    add_memory(workspace)
    (workspace / ".memory/hidden.py").write_text("print('not a memory record')")
    assert not grade_foundation(workspace, case, criteria)["passed"]
    (workspace / ".memory/hidden.py").unlink()
    (workspace / ".memory/MEMORY.md").write_text("wrong index")
    result = grade_foundation(workspace, case, criteria)
    assert not result["passed"] and not result["memory_state"]["index_matches_records"]


def test_protected_test_deletion_and_extra_project_files_still_fail(repaired):
    workspace, case, criteria = repaired
    (workspace / "test_checkout.py").unlink()
    assert not grade_foundation(workspace, case, criteria)["passed"]
    (workspace / "test_checkout.py").write_text(case["files"]["test_checkout.py"])
    (workspace / "cheat.py").write_text("pass")
    result = grade_foundation(workspace, case, criteria)
    assert not result["passed"] and result["unexpected_files"] == ["cheat.py"]


def test_symlinked_business_file_is_rejected_without_reading_its_target(repaired, tmp_path):
    workspace, case, criteria = repaired
    outside = tmp_path.parent / (tmp_path.name + "-outside.py")
    outside.write_text("outside private content")
    (workspace / "shipping.py").unlink()
    (workspace / "shipping.py").symlink_to(outside)
    result = grade_foundation(workspace, case, criteria)
    assert not result["passed"] and result["behavior"] is None
    assert "outside private content" not in json.dumps(result)
