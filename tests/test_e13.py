import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from lessons.e13_planning.code import Runtime
from lessons.e13_planning.state import MessageBus, TaskStore, TodoManager
from lessons.e13_planning.tools import PlanningPool


def tool(name, **args):
    return {"name": name, "arguments_json": json.dumps(args)}


def test_dependency_validation_is_atomic_and_survives_new_store(tmp_path):
    store = TaskStore(tmp_path)
    a, b = store.create("core"), store.create("entry")
    store.add_dependencies(b["id"], [a["id"]])
    before = store.list()
    with pytest.raises(ValueError, match="cycle"):
        store.add_dependencies(a["id"], [b["id"]])
    assert store.list() == before
    with pytest.raises(ValueError, match="incomplete"):
        store.claim(b["id"], "worker-b")
    store.claim(a["id"], "worker-a")
    with pytest.raises(ValueError, match="owner"):
        store.complete(a["id"], "worker-b")
    store.complete(a["id"], "worker-a")
    restored = TaskStore(tmp_path)
    assert restored.claim(b["id"], "worker-b")["owner"] == "worker-b"


def test_only_one_concurrent_claim_wins(tmp_path):
    store = TaskStore(tmp_path)
    task = store.create("one assignment")
    barrier = threading.Barrier(2)

    def claim(owner):
        barrier.wait()
        try:
            return store.claim(task["id"], owner)["owner"]
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ["worker-a", "worker-b"]))
    assert sum(r is not None for r in results) == 1
    assert store.load(task["id"])["owner"] in results


def test_todos_are_validated_before_replacing_plan_and_reminder_counts_rounds():
    todo = TodoManager()
    original = [{"content": "inspect", "status": "in_progress"}]
    todo.update(original)
    with pytest.raises(ValueError):
        todo.update(original * 2)
    assert todo.items == original
    assert todo.reminder(["read_file", "glob"]) is None
    assert todo.reminder(["read_file"]) is None
    assert "Plan reminder" in todo.reminder(["read_file"])
    assert todo.reminder(["todo_write"]) is None


def test_worker_permissions_and_stale_concurrent_edit(tmp_path):
    (tmp_path / "shipping.py").write_text("old\n")
    (tmp_path / "checkout.py").write_text("other\n")
    runtime = Runtime(tmp_path)
    ta, tb = runtime.store.create("editor a"), runtime.store.create("editor b")
    runtime.store.claim(ta["id"], "worker-a")
    runtime.store.claim(tb["id"], "worker-b")
    a = PlanningPool(runtime, "worker-a", ta["id"], ["shipping.py"])
    b = PlanningPool(runtime, "worker-b", tb["id"], ["shipping.py"])
    first = tool("edit_file", path="shipping.py", old_text="old", new_text="first")
    assert a.dispatch(first, tmp_path)[1]["status"] == "ok"
    second = tool("edit_file", path="shipping.py", old_text="old", new_text="second")
    assert b.dispatch(second, tmp_path)[1]["status"] == "denied"
    assert "first" in (tmp_path / "shipping.py").read_text()
    assert (
        a.dispatch(tool("write_file", path="checkout.py", content="wrong"), tmp_path)[1]["status"]
        == "denied"
    )
    assert (
        a.dispatch(tool("bash", command="python3 -c 'print(1)'"), tmp_path)[1]["status"] == "denied"
    )
    assert (
        a.dispatch(tool("task", task_id="x", prompt="recurse", files="[]"), tmp_path)[1]["status"]
        == "denied"
    )


def test_mailbox_is_consumed_once_and_cannot_escape_workspace(tmp_path):
    bus = MessageBus(tmp_path)
    sent = bus.send("worker-a", "lead", "task_11111111", "actual summary", "completed_claim")
    assert bus.consume("lead") == [sent]
    assert bus.consume("lead") == []
    with pytest.raises(ValueError):
        bus.consume("../outside")
    outside = tmp_path / "outside"
    outside.mkdir()
    bus.path("lead").symlink_to(outside / "fake")
    with pytest.raises(ValueError):
        bus.consume("lead")


def test_subagent_has_fresh_context_and_cannot_complete_another_task(tmp_path):
    (tmp_path / "shipping.py").write_text("fixture source\n")
    observed = []

    def model(messages, tools, actor):
        observed.append((actor, messages))
        assert "PRIVATE_PARENT_MARKER" not in json.dumps(messages)
        assert "task" not in {t["name"] for t in tools}
        return {
            "reply": {"answer": "Only a fixture summary, not a real model run", "tool_calls": []}
        }

    runtime = Runtime(tmp_path, model=model)
    task = runtime.store.create("inspect", "Review shipping API")
    result = runtime.run_child(task["id"], "Read only the assigned source", ["shipping.py"])
    assert result["status"] == "incomplete"
    assert len(observed) == 1 and observed[0][0] == "worker-1"
    assert "Review shipping API" in observed[0][1][0]["content"]
    assert runtime.children[0]["result"]["status"] == "finished"
    # A final answer alone does not change the task's persistent status.
    assert runtime.store.load(task["id"])["status"] == "in_progress"
    other = runtime.store.create("other")
    worker = PlanningPool(runtime, "worker-1", task["id"], ["shipping.py"])
    assert (
        worker.dispatch(tool("task_complete", task_id=other["id"]), tmp_path)[1]["status"]
        == "error"
    )


def test_task_paths_and_later_symlink_replacement_are_rejected(tmp_path):
    store = TaskStore(tmp_path)
    with pytest.raises(ValueError):
        store.load("../outside")
    outside = tmp_path / "outside"
    outside.mkdir()
    store.root.rmdir()
    store.root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        store.create("escape")


def test_cross_file_checks_catch_lost_expedited_handoff_and_protect_tests(tmp_path):
    from lessons.e13_planning.verify import verify

    root = Path(__file__).parents[1]
    case = json.loads((root / "lessons/e13_planning/cases.jsonl").read_text())
    for name, content in case["files"].items():
        (tmp_path / name).write_text(content)
    source = case["files"]["shipping.py"].replace(
        "max(0, (weight_grams - 1000) // 1000)", "(weight_grams - 1) // 1000"
    )
    (tmp_path / "shipping.py").write_text(source)
    criteria = json.loads((root / "evaluation_private/e13.json").read_text())
    failed = verify(tmp_path, case, criteria)
    assert failed["core"]["passed"] is True
    assert failed["passed"] is False
    assert failed["checks"]["quote_behavior"] is False
    (tmp_path / "checkout.py").write_text(
        "from shipping import shipping_fee\n\ndef quote(weight_grams, expedited=False):\n"
        "    return shipping_fee(weight_grams, expedited)\n"
    )
    assert verify(tmp_path, case, criteria)["passed"] is True
    (tmp_path / "unrequested.py").write_text("# functional behavior still passes")
    assert verify(tmp_path, case, criteria)["checks"]["no_unexpected_project_files"] is False
    (tmp_path / "unrequested.py").unlink()
    (tmp_path / "test_checkout.py").write_text("# deleted assertions\n")
    assert verify(tmp_path, case, criteria)["passed"] is False


def test_protocol_controls_execute_state_and_file_failures_without_models():
    from lessons.e13_planning.controls import run

    report = run()
    assert report["passed"] is True
    assert report["model_requests"] == 0
    assert len(report["checks"]) == 7


def test_changed_quote_signature_is_failure_unsupported_import_is_unscored(tmp_path):
    from lessons.e13_planning.verify import verify

    root = Path(__file__).parents[1]
    case = json.loads((root / "lessons/e13_planning/cases.jsonl").read_text())
    for name, content in case["files"].items():
        (tmp_path / name).write_text(content)
    (tmp_path / "checkout.py").write_text(
        "from shipping import shipping_fee\ndef quote(weight):\n    return shipping_fee(weight)\n"
    )
    result = verify(tmp_path, case, [])
    assert result["status"] == "scored" and result["passed"] is False
    (tmp_path / "checkout.py").write_text(
        "import os\ndef quote(weight_grams, expedited=False):\n    return 0\n"
    )
    result = verify(tmp_path, case, [])
    assert result["status"] == "unscored" and result["passed"] is None


def test_workspace_alias_uses_canonical_permission_boundary(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "shipping.py").write_text("before\n")
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    runtime = Runtime(alias)
    task = runtime.store.create("edit through alias")
    runtime.store.claim(task["id"], "worker-a")
    pool = PlanningPool(runtime, "worker-a", task["id"], ["shipping.py"])
    result = pool.dispatch(
        tool("edit_file", path="shipping.py", old_text="before", new_text="after"), alias
    )
    assert result[1]["status"] == "ok"
    assert pool.dispatch(tool("read_file", path="shipping.py"), tmp_path)[1]["status"] == "denied"


def test_native_sdk_collects_closed_role_model_and_tool_spans(tmp_path, monkeypatch):
    from lessons.e13_planning.code import run_case

    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    count = 0

    def fixture_model(messages, tools, actor):
        nonlocal count
        from deepeval.test_case import ToolCall
        from deepeval.tracing import update_current_span

        count += 1
        update_current_span(tools_called=[ToolCall(name="fixture_declared_tool")])
        calls = [tool("read_file", path="shipping.py")] if count == 1 else []
        return {"reply": {"answer": "explicit fixture, no actual model", "tool_calls": calls}}

    case = {"files": {"shipping.py": "fixture source\n"}, "task": "Read the fixture file"}
    row = run_case(case, model=fixture_model)
    json.dumps(row)
    trace = row["native_deepeval_trace"]
    json.dumps(trace)
    assert trace["input"] == case["task"]
    assert trace["end_time"] is not None
    root = trace["root_spans"][0]
    assert root["name"] == "lead" and root["input"] == case["task"]
    names = {c["name"] for c in root["children"]}
    assert {"role_model_request", "read_file"} <= names
    assert all(c["parent_uuid"] == root["uuid"] for c in root["children"])


def test_native_plan_metrics_empty_plan_is_default_one_not_completion():
    from deepeval.metrics import PlanAdherenceMetric, PlanQualityMetric
    from deepeval.test_case import LLMTestCase

    from lessons.e11_task_completion.eval import CapturingDeepJudge

    class FixtureTransport:
        def __init__(self):
            self.calls = []

        def ask(self, prompt):
            self.calls.append(prompt)
            return json.dumps({"task": "fixture task"} if len(self.calls) == 1 else {"plan": []})

    for cls in (PlanQualityMetric, PlanAdherenceMetric):
        transport = FixtureTransport()
        metric = cls(model=CapturingDeepJudge(transport), eval_mode="llm", async_mode=False)
        sample = LLMTestCase(input="fixture", actual_output="No work done")
        sample._trace_dict = {"input": "fixture", "root_spans": []}
        assert metric.measure(sample, _show_indicator=False) == 1
        assert len(transport.calls) == 2
        assert "no plans" in metric.reason.lower()


def test_trace_projection_keeps_real_plan_calls_but_removes_repeated_histories():
    from lessons.e13_planning.eval import trace_projection

    source = {
        "name": "lead",
        "type": "agent",
        "input": "actual task",
        "children": [
            {
                "name": "model",
                "type": "llm",
                "input": {"messages": ["repeated history"]},
                "output": {
                    "reply": {"answer": "Explicit plan", "tool_calls": []},
                    "model": {"usage": []},
                },
            },
            {
                "name": "todo_write",
                "type": "tool",
                "input": {"todos": "actual plan"},
                "output": {"status": "ok"},
            },
        ],
    }
    projected = trace_projection(source)
    assert projected["input"] == "actual task"
    assert projected["children"][1]["input"] == {"todos": "actual plan"}
    assert projected["children"][0]["output"]["reply"]["answer"] == "Explicit plan"
    assert "repeated history" not in json.dumps(projected)
    assert "repeated history" in json.dumps(source)


def test_protected_test_newline_bytes_cannot_be_normalized_away(tmp_path):
    from lessons.e13_planning.verify import files_at

    (tmp_path / "test_checkout.py").write_bytes(b"first\r\nsecond\r\n")
    actual = files_at(tmp_path, ["test_checkout.py"])
    assert actual["test_checkout.py"] == "first\r\nsecond\r\n"
    assert actual["test_checkout.py"] != "first\nsecond\n"


def test_planning_arrays_are_typed_and_old_nested_strings_are_rejected(tmp_path):
    pool = PlanningPool(Runtime(tmp_path))
    items = [{"content": "Inspect both APIs", "status": "in_progress"}]
    assert pool.dispatch(tool("todo_write", todos=items), tmp_path)[1]["status"] == "ok"
    assert (
        pool.dispatch(tool("todo_write", todos=json.dumps(items)), tmp_path)[1]["status"] == "error"
    )
    definitions = {t["name"]: t for t in pool.assemble()}
    assert definitions["todo_write"]["input_schema"]["properties"]["todos"]["type"] == "array"


def test_typed_wire_format_normalizes_once_without_losing_arrays(tmp_path, monkeypatch):

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "tools"))
    from model_bridge import e10_contract, e13_contract, normalize_e13_reply

    pool = PlanningPool(Runtime(tmp_path))
    instruction, schema = e13_contract(pool.assemble())
    assert "All tool argument values must be strings." not in instruction
    choices = schema["properties"]["tool_calls"]["items"]["anyOf"]
    branch = next(c for c in choices if c["properties"]["name"]["enum"] == ["todo_write"])
    assert branch["properties"]["arguments"]["properties"]["todos"]["type"] == "array"
    items = [{"content": 'Quotes " and a backslash \\ stay ordinary text', "status": "pending"}]
    wire = {"answer": "", "tool_calls": [{"name": "todo_write", "arguments": {"todos": items}}]}
    normalized = normalize_e13_reply(wire)
    assert json.loads(normalized["tool_calls"][0]["arguments_json"])["todos"] == items
    assert pool.dispatch(normalized["tool_calls"][0], tmp_path)[1]["status"] == "ok"
    read = normalize_e13_reply(
        {
            "answer": "",
            "tool_calls": [
                {
                    "name": "read_file",
                    "arguments": {"path": "shipping.py", "offset": None, "limit": None},
                }
            ],
        }
    )
    assert json.loads(read["tool_calls"][0]["arguments_json"]) == {"path": "shipping.py"}
    with pytest.raises(ValueError):
        e10_contract(pool.assemble())


def test_official_native_span_conversion_preserves_types_for_scoring_projection(
    tmp_path, monkeypatch
):
    from lessons.e13_planning.code import run_case
    from lessons.e13_planning.eval import trace_projection

    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    row = run_case(
        {"files": {"shipping.py": "fixture"}, "task": "fixture task"},
        model=lambda messages, tools, actor: {"reply": {"answer": "fixture", "tool_calls": []}},
    )
    canonical = row["native_metric_trace"]
    model = next(s for s in canonical["children"] if s["name"] == "role_model_request")
    assert model["type"] == "llm"
    projected = trace_projection(canonical)
    model = next(s for s in projected["children"] if s["name"] == "role_model_request")
    assert "messages" not in model["input"]
    assert model["output"]["reply"]["answer"] == "fixture"


def test_core_public_stop_can_pass_while_dependent_entry_still_fails(tmp_path):
    from lessons.e13_planning.verify import scoped_public_review, verify

    root = Path(__file__).parents[1]
    case = json.loads((root / "lessons/e13_planning/cases.jsonl").read_text())
    for name, content in case["files"].items():
        (tmp_path / name).write_text(content)
    runtime = Runtime(tmp_path)
    task = runtime.store.create("core only")
    runtime.store.claim(task["id"], "worker-a")
    pool = PlanningPool(runtime, "worker-a", task["id"], ["shipping.py"])
    assert (
        pool.dispatch(tool("task_complete", task_id=task["id"]), tmp_path)[1]["status"] == "error"
    )
    assert runtime.store.load(task["id"])["status"] == "in_progress"
    repaired = case["files"]["shipping.py"].replace(
        "max(0, (weight_grams - 1000) // 1000)", "(weight_grams - 1) // 1000"
    )
    (tmp_path / "shipping.py").write_text(repaired)
    assert scoped_public_review(tmp_path, ["shipping.py"])["passed"] is True
    completed = pool.dispatch(tool("task_complete", task_id=task["id"]), tmp_path)[1]
    assert completed["status"] == "ok"
    summary = json.loads(completed["output"])["scoped_public_review"]
    assert summary["whole_project_assessment"] == "not_assessed"
    for name in ("test_shipping.py", "test_checkout.py"):
        assert summary["artifact_hashes"][name] == summary["original_test_hashes"][name]
    assert runtime.store.load(task["id"])["status"] == "completed"
    criteria = json.loads((root / "evaluation_private/e13.json").read_text())
    assert verify(tmp_path, case, criteria)["passed"] is False


def test_planning_profile_preserves_normal_history_but_archives_long_history(tmp_path):
    from lessons.e12_conversation.context import check_pairs
    from lessons.e13_planning.code import PlanningContext

    compactor = PlanningContext(tmp_path, None, limit=30000)
    messages = [{"role": "user", "content": "keep constraints"}]
    for _ in range(20):
        messages.extend(
            [
                {"role": "assistant", "content": {"tool_calls": [{"name": "read_file"}]}},
                {"role": "tool", "content": [{"output": "actual data"}]},
            ]
        )
    assert compactor.snip(messages) == messages
    assert not compactor.events
    messages.extend([{"role": "user", "content": "reference data"}] * 10)
    result = compactor.snip(messages)
    check_pairs(result)
    assert result[0] == messages[0]
    assert json.loads((tmp_path / compactor.events[-1]["path"]).read_text()) == messages


def test_recovered_child_history_is_retained_but_latest_failed_handoff_still_rejects(
    tmp_path, monkeypatch
):
    import copy

    from lessons.e13_planning import eval as evaluation

    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    run_id = "a" * 32
    workspace = tmp_path / run_id
    workspace.mkdir()
    store = TaskStore(workspace)
    a, b = store.create("core"), store.create("entry")
    store.add_dependencies(b["id"], [a["id"]])
    for task, owner in ((a, "worker-a"), (b, "worker-b")):
        store.claim(task["id"], owner)
        store.complete(task["id"], owner)
    children = []
    for task, owner, files in ((a, "worker-a", ["shipping.py"]), (b, "worker-b", ["checkout.py"])):
        children.append(
            {
                "assigned_files": files,
                "result": {
                    "task_id": task["id"],
                    "actor": owner,
                    "status": "finished",
                    "initial_request": "scoped fixture",
                    "model_inputs": [{"messages": [{"role": "user", "content": "scoped fixture"}]}],
                },
            }
        )
    failed = copy.deepcopy(children[0])
    failed["result"]["status"] = "model_error"
    report = {
        "case": {"files": {}},
        "row": {
            "run_id": run_id,
            "artifacts": {},
            "tasks": store.list(),
            "task_events": store.events,
            "children": [failed, *children],
            "lead": {
                "status": "finished",
                "todos": [{"content": "fixture plan", "status": "completed"}],
                "events": [
                    {"type": "tool", "call": {"name": "todo_write"}, "result": {"status": "ok"}},
                    {"type": "tool", "call": {"name": "task"}, "result": {"status": "ok"}},
                ],
            },
            "native_deepeval_trace": {"root_spans": [{"fixture": True}]},
        },
    }
    # Only isolate scheduling classification here; real artifact execution has separate tests.
    monkeypatch.setattr(evaluation, "files_at", lambda *a: {})
    monkeypatch.setattr(evaluation, "verify", lambda *a: {"passed": True})
    grade = evaluation.evaluate(report, [])
    assert grade["passed"] and grade["completed_after_child_retries"]
    assert grade["child_attempt_errors"] == [
        {"actor": "worker-a", "task_id": a["id"], "status": "model_error"}
    ]
    report["row"]["children"][-1]["result"]["status"] = "model_error"
    assert evaluation.evaluate(report, [])["passed"] is False


def test_completed_component_cannot_be_silently_changed_by_its_worker(tmp_path):
    (tmp_path / "shipping.py").write_text("fixture before\n")
    runtime = Runtime(tmp_path)
    task = runtime.store.create("close then try mutation")
    runtime.store.claim(task["id"], "worker-a")
    pool = PlanningPool(runtime, "worker-a", task["id"], ["shipping.py"])
    runtime.store.complete(task["id"], "worker-a")
    result = pool.dispatch(
        tool("write_file", path="shipping.py", content="changed after completion"), tmp_path
    )
    assert result[1]["status"] == "denied"
    assert (tmp_path / "shipping.py").read_text() == "fixture before\n"
