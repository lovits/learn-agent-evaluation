import hashlib
import json

import pytest

from eval_course.knowledge import PROJECT, document, search
from eval_course.records import report_path, save
from lessons.e01_agent_baseline.code import agent_loop, prepare_workspace, run_bash
from lessons.e01_agent_baseline.eval import check_rule, evaluate


def model_reply(commands=(), answer=""):
    return {
        "reply": {"tool_calls": [{"command": c} for c in commands], "answer": answer},
        "model": {"mode": "unit_scripted_not_model_measurement"},
    }


def test_loop_executes_bash_and_feeds_real_results_back(tmp_path):
    calls = []

    def scripted_model(messages):
        calls.append(len(messages))
        if len(calls) == 1:
            return model_reply(["printf 'unit-result' > result.txt", "cat result.txt"])
        assert messages[-1]["role"] == "tool"
        assert messages[-1]["content"][1]["stdout"] == "unit-result"
        return model_reply(answer="done")

    result = agent_loop("unit fixture", tmp_path, model=scripted_model)
    assert result["status"] == "finished"
    assert (tmp_path / "result.txt").read_text() == "unit-result"
    assert [e["type"] for e in result["events"]] == ["model", "bash", "bash", "model"]


def test_nonzero_exit_is_preserved(tmp_path):
    result = run_bash("printf 'failure' >&2; exit 7", tmp_path)
    assert result["exit_code"] == 7
    assert result["status"] == "error"
    assert result["stderr"] == "failure"


def test_timeout_stops_the_command_group(tmp_path):
    result = run_bash("sleep 10", tmp_path, timeout=0.1)
    assert result["status"] == "timeout"
    assert result["exit_code"] != 0


def test_initial_teaching_deny_list_is_retained(tmp_path):
    result = run_bash("sudo echo do-not-run", tmp_path)
    assert result["status"] == "blocked"
    assert result["exit_code"] is None


def test_budget_is_not_task_success(tmp_path):
    result = agent_loop("never stop", tmp_path, model=lambda _: model_reply(["true"]), max_steps=2)
    assert result["status"] == "step_limit"
    assert result["final_answer"] is None


def test_model_failure_keeps_the_partial_trace(tmp_path):
    def broken(_):
        raise OSError("model is unavailable")

    result = agent_loop("unit task", tmp_path, model=broken)
    assert result["status"] == "model_error"
    assert result["events"] == []


def test_false_completion_fails_independent_grading(tmp_path):
    report = {
        "run_id": "a" * 32,
        "mode": "unit_scripted",
        "case_id": "unit",
        "status": "finished",
        "final_answer": "already completed",
        "events": [],
    }
    criteria = {
        "checks": [{"name": "real_output", "kind": "successful_stdout_contains", "value": "unit"}]
    }
    grade = evaluate(report, criteria, tmp_path)
    assert not grade["passed"]
    assert grade["checks"][1]["passed"] is False


def test_nonzero_output_does_not_pass_success_check(tmp_path):
    tool = {"result": {"exit_code": 7, "stdout": "unit-value", "stderr": ""}}
    assert not check_rule(
        {"kind": "successful_stdout_contains", "value": "unit-value"}, [tool], tmp_path
    )


def test_completion_depends_on_real_output_and_the_current_artifact(tmp_path):
    replies = iter(
        [
            model_reply(["printf 'print(\"Hello, World!\")\\n' > hello.py", "python3 hello.py"]),
            model_reply(answer="done"),
        ]
    )
    run = agent_loop("create and run hello.py", tmp_path, model=lambda _: next(replies))
    report = {"run_id": "c" * 32, "mode": "controlled_example", "case_id": "hello", **run}
    criteria = {
        "checks": [
            {"name": "output", "kind": "successful_stdout_contains", "value": "Hello, World!"},
            {
                "name": "file",
                "kind": "python_ast",
                "path": "hello.py",
                "source": 'print("Hello, World!")',
            },
        ]
    }
    assert evaluate(report, criteria, tmp_path)["passed"]

    (tmp_path / "hello.py").write_text('print("Goodbye")\n')
    grade = evaluate(report, criteria, tmp_path)
    assert not grade["passed"]
    assert grade["checks"][-2]["passed"]  # Old stdout remains, but the file changed.
    assert not grade["checks"][-1]["passed"]


def test_ast_contract_accepts_quotes_and_rejects_extra_statements(tmp_path):
    path = tmp_path / "unit.py"
    rule = {"kind": "python_ast", "path": "unit.py", "source": 'print("unit")'}
    path.write_text("print('unit') # same program\n")
    assert check_rule(rule, [], tmp_path)
    path.write_text("import os\nprint('unit')\n")
    assert not check_rule(rule, [], tmp_path)


def test_verifier_rejects_symlink_escape(tmp_path):
    (tmp_path / "escape.py").symlink_to(PROJECT / "lessons/e01_agent_baseline/code.py")
    assert not check_rule(
        {"kind": "python_ast", "path": "escape.py", "source": "pass"}, [], tmp_path
    )


def test_fixture_cannot_escape_workspace(tmp_path):
    with pytest.raises(ValueError, match="越出"):
        prepare_workspace({"files": {"../escape.txt": "no"}}, "a" * 32, tmp_path)


def test_report_names_and_json_are_safe(tmp_path):
    with pytest.raises(ValueError):
        report_path("../../.env", tmp_path)
    report = {"run_id": "b" * 32, "status": "finished"}
    assert json.loads(save(report, folder=tmp_path).read_text()) == report


def test_knowledge_is_current_and_contained(tmp_path):
    (tmp_path / "api.md").write_text("Python API 接口资料")
    assert search("Python", root=tmp_path)[0]["path"] == "api.md"
    with pytest.raises(ValueError):
        document("../outside.md", tmp_path)


def test_preserved_framework_sources_match_manifest():
    for item in json.loads((PROJECT / "references/sources.json").read_text()):
        assert hashlib.sha256((PROJECT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
