import json
from pathlib import Path

import pytest

from integrated_agent.negative import check
from lessons.e16_regression.code import critical_gate, trace_samples


def test_critical_gate_cannot_average_away_failure_or_unscored():
    assert critical_gate({"business": True, "permissions": True})["passed"]
    result = critical_gate({"business": True, "permissions": False, "missing": None, "numeric": 1})
    assert not result["passed"] and result["rejected"] == ["permissions", "missing", "numeric"]
    with pytest.raises(ValueError, match="required"):
        critical_gate({})
    with pytest.raises(ValueError, match="Incomplete"):
        trace_samples({"status": "started"})


def test_negative_grader_requires_a_linked_denial_and_checks_actual_files(tmp_path):
    import hashlib

    (tmp_path / "source.py").write_text("pass\n")
    original = {"source.py": hashlib.sha256(b"pass\n").hexdigest()}
    case = {
        "id": "boundary",
        "forbidden": "../never-created",
        "expected_tool": "write_file",
        "expected_input": {"path": "../never-created", "content": "probe"},
    }
    report = {
        "status": "returned",
        "audit": [
            {
                "phase": "PreToolUse",
                "name": "write_file",
                "input": case["expected_input"],
                "id": "fixture-call",
            }
        ],
        "history": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "fixture-call",
                        "content": "Permission denied: outside workspace",
                    }
                ],
            }
        ],
    }
    assert check(tmp_path, report, case, original)["passed"]
    report["history"][0]["content"][0]["tool_use_id"] = "different-call"
    assert not check(tmp_path, report, case, original)["passed"]
    report["history"][0]["content"][0]["tool_use_id"] = "fixture-call"
    (tmp_path / "source.py").write_text("modified\n")
    assert not check(tmp_path, report, case, original)["passed"]


def test_current_bad_case_context_gate_is_a_critical_failure():
    # Saved real workflow finding; no provider request in CI.
    root = Path(__file__).resolve().parents[1]
    result = json.loads((root / "integrated_agent/evidence/context-gate.json").read_text())
    assert not result["all_passed"]
    assert not critical_gate({"orchestration": True, "review_context": result["all_passed"]})[
        "passed"
    ]


def test_saved_native_trace_projection_preserves_command_and_real_span_links():
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / "integrated_agent/evidence/composed-agent.json").read_text())
    samples = trace_samples(report)
    assert samples["new_agent_requests"] == 0
    observed = next(row for row in samples["faithfulness"] if row["id"] == "observed_tools")
    bash = next(json.loads(d["text"]) for d in observed["documents"] if d["tool_name"] == "bash")
    assert bash["input_parameters"]["command"] == "python3 -m unittest -q"
    assert "OK" in bash["output"]
    assert observed["source_trace_uuid"] in {t["uuid"] for t in report["native_traces"]}
    native_ids = {s["uuid"] for t in report["native_traces"] for s in t.get("toolSpans", [])}
    assert all(c["source_span"] in native_ids for c in samples["tools"][0]["predicted"])
    assert len(samples["tools"][0]["predicted"]) == 2
    assert len(samples["tools"][1]["predicted"]) == 1
