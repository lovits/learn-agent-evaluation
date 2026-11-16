import copy
import json

import pytest

from lessons.e02_tools_traces.code import agent_loop, dispatch
from lessons.e02_tools_traces.samples import (
    export_samples,
    native_samples,
    restore_samples,
    trace_errors,
)


def call(name, **args):
    return {"name": name, "arguments_json": json.dumps(args)}


def trace(tmp_path, calls):
    replies = iter([{"tool_calls": calls, "answer": ""}, {"tool_calls": [], "answer": "完成"}])
    report = agent_loop(
        "读取文件并检查结果", tmp_path, model=lambda messages: {"reply": next(replies)}
    )
    return {
        "run_id": "a" * 32,
        "schema_version": "e02.v1",
        "dataset_sha256": "test",
        "split": "development",
        "task": "读取文件并检查结果",
        **report,
    }


def test_tools_edit_once_and_keep_outputs_separate(tmp_path):
    dispatch(call("write_file", path="a.txt", content="old old"), tmp_path)
    _, result = dispatch(call("edit_file", path="a.txt", old_text="old", new_text="new"), tmp_path)
    assert result["status"] == "ok"
    assert (tmp_path / "a.txt").read_text() == "new old"
    _, result = dispatch(
        call("edit_file", path="a.txt", old_text="missing", new_text="x"), tmp_path
    )
    assert result["status"] == "error"
    assert (tmp_path / "a.txt").read_text() == "new old"


@pytest.mark.parametrize(
    "name,args",
    [
        ("read_file", {}),
        ("write_file", {"path": "x"}),
        ("read_file", {"path": 42}),
        ("unknown", {}),
    ],
)
def test_invalid_arguments_never_execute(tmp_path, name, args):
    policy, result = dispatch(call(name, **args), tmp_path)
    assert policy["decision"] == "not_checked"
    assert result["status"] == "invalid_arguments"
    assert not list(tmp_path.iterdir())


def test_permissions_resolve_symlinks_and_keep_glob_inside(tmp_path):
    (tmp_path / "link").symlink_to(tmp_path.parent, target_is_directory=True)
    for name, args in [
        ("read_file", {"path": "link/x"}),
        ("write_file", {"path": "../x", "content": "bad"}),
        ("glob", {"pattern": "../*"}),
    ]:
        policy, result = dispatch(call(name, **args), tmp_path)
        assert policy["reason"] == "outside_workspace"
        assert result["status"] == "denied"
    _, result = dispatch(call("glob", pattern="*"), tmp_path)
    assert "link" not in result["output"]


def test_approval_and_deny_list_are_different(tmp_path):
    (tmp_path / "a").write_text("keep")
    policy, result = dispatch(call("bash", command="rm a"), tmp_path)
    assert policy["reason"] == "approval_required" and result["status"] == "denied"
    assert (tmp_path / "a").exists()
    _, result = dispatch(call("bash", command="rm a"), tmp_path, approve=lambda n, a: True)
    assert result["exit_code"] == 0 and not (tmp_path / "a").exists()
    policy, result = dispatch(
        call("bash", command="sudo true"), tmp_path, approve=lambda n, a: True
    )
    assert policy["reason"] == "deny_list" and result["status"] == "denied"


def test_trace_hooks_include_denial_error_and_ids(tmp_path):
    report = trace(tmp_path, [call("read_file", path="missing"), call("bash", command="rm a")])
    assert not trace_errors(report)
    tools = [e for e in report["events"] if e["type"] == "tool"]
    assert [e["result"]["status"] for e in tools] == ["error", "denied"]
    assert tools[0]["span_id"] != tools[1]["span_id"]
    corrupted = copy.deepcopy(report)
    corrupted["events"][1], corrupted["events"][2] = corrupted["events"][2], corrupted["events"][1]
    assert "tool_result_order_or_owner" in trace_errors(corrupted)
    corrupted = copy.deepcopy(report)
    corrupted["hooks"].pop(1)
    assert "hook_coverage" in trace_errors(corrupted)


def test_real_sdk_round_trip_keeps_errors_and_absent_retrieval(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
    monkeypatch.setenv("RAGAS_DO_NOT_TRACK", "true")

    report = trace(tmp_path, [call("read_file", path="a"), call("read_file")])
    samples = native_samples(report)
    restored = restore_samples(json.loads(json.dumps(export_samples(report))))
    deep, multi = restored["deepeval_single"], restored["ragas_multi"]
    assert len(restored["deepeval_conversation"].turns) == 3
    assert deep.retrieval_context is None and deep.expected_output is None
    assert len(deep.tools_called) == 2
    assert [t.output["status"] for t in deep.tools_called] == ["error", "invalid_arguments"]
    results = [m for m in multi.user_input if m.type == "tool"]
    assert len(results) == 2 and results[0].metadata["call_id"].endswith("tool-0")
    assert samples["ragas_single"].retrieved_contexts is None
    del report["task"]
    with pytest.raises(KeyError):
        native_samples(report)


def test_model_failure_and_budget_are_not_finished(tmp_path):
    def broken(messages):
        raise RuntimeError("unavailable")

    assert agent_loop("x", tmp_path, model=broken)["status"] == "model_error"
    model = lambda messages: {"reply": {"tool_calls": [call("read_file", path="x")], "answer": ""}}
    assert agent_loop("x", tmp_path, model=model, max_steps=1)["status"] == "step_limit"


def test_grader_rejects_missing_action_and_wrong_file(tmp_path):
    from lessons.e02_tools_traces.eval import evaluate

    report = trace(tmp_path, [])
    report.update(case_id="example")
    criteria = {"tools": [{"name": "write_file", "status": "ok"}], "files": {"result.txt": "48\n"}}
    grade = evaluate(report, criteria, tmp_path)
    assert not grade["passed"]
    assert not grade["checks"]["tool_0"] and not grade["checks"]["file:result.txt"]


def test_dataset_split_ids_do_not_overlap():
    from pathlib import Path

    from lessons.e02_tools_traces.code import load_cases

    path = Path(__file__).parents[1] / "lessons/e02_tools_traces/dataset_manifest.json"
    manifest = json.loads(path.read_text())
    groups = [
        manifest[k] for k in ("development", "calibration_ids", "holdout_ids")
    ]
    assert groups[0] == [case["id"] for case in load_cases()]
    ids = [item for group in groups for item in group]
    assert len(ids) == len(set(ids))
