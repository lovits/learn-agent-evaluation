import json

from course.e04_scoring.eval import score
from course.e11_tool_quality.code import run_case
from course.e12_task_completion.eval import DeliveryContract, evidence_sample, inspect_delivery
from eval_course.knowledge import PROJECT


def cases():
    return {
        c["id"]: c
        for c in (
            json.loads(line)
            for line in (PROJECT / "course/e12_task_completion/cases.jsonl")
            .read_text()
            .splitlines()
        )
    }


def test_same_claim_different_real_deliveries(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    rows = cases()
    observed = {}
    for key, case in rows.items():
        run = run_case(case)
        evidence = inspect_delivery(tmp_path / run["workspace_id"], case["files"]["policy.txt"])
        observed[key] = (run, evidence, score(DeliveryContract(), evidence_sample(run, evidence)))
    assert {v[0]["final_answer"] for v in observed.values()} == {"已完成。"}
    assert {k for k, v in observed.items() if v[2]["passed"]} == {"correct", "equivalent_loop"}
    assert observed["policy_changed"][1]["checks"]["business_behavior"]
    assert not observed["policy_changed"][1]["checks"]["policy_unchanged"]
    probes = observed["mutates_input"][1]["probes"]
    assert all(probes[f"value_{i}"] for i in range(4))
    assert not probes["input_unchanged_1"]
    assert observed["syntax_error"][1]["probes"]["loaded"] is False


def test_missing_and_outside_artifact_are_not_loaded(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    assert not inspect_delivery(work, "")["checks"]["target_inside_workspace"]
    outside = tmp_path / "outside.py"
    outside.write_text('raise RuntimeError("must not execute")')
    (work / "billing.py").symlink_to(outside)
    assert not inspect_delivery(work, "")["checks"]["target_inside_workspace"]


def test_unavailable_probe_is_a_scoring_error():
    from deepeval.test_case import LLMTestCase

    sample = LLMTestCase(
        input="repair",
        actual_output=json.dumps({"independent_observation": {"status": "error", "checks": {}}}),
    )
    result = score(DeliveryContract(), sample)
    assert result["status"] == "error"
    assert result["score"] is None


def test_empty_probe_cannot_pass_by_vacuous_truth(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from course.e12_task_completion import eval as checks

    (tmp_path / "billing.py").write_text("pass")
    (tmp_path / "policy.txt").write_text("policy")
    monkeypatch.setattr(
        checks.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="{}\n", stderr=""),
    )
    evidence = inspect_delivery(tmp_path, "policy")
    assert evidence["status"] == "error"
