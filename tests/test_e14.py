import json
import shlex
import sys
from datetime import datetime, timedelta

import pytest

from lessons.e14_runtime.background import BackgroundManager, file_hashes
from lessons.e14_runtime.cron import cron_matches, validate_cron
from lessons.e14_runtime.scheduler import Scheduler


def command(code):
    return shlex.quote(sys.executable) + " -c " + shlex.quote(code)


def test_background_returns_before_independent_work_and_notifies_once(tmp_path):
    (tmp_path / "source.py").write_text("version1\n")
    manager = BackgroundManager(tmp_path, ["source.py"])
    try:
        job = manager.start(
            command(
                "from pathlib import Path; import time\n"
                "while not Path('release').exists(): time.sleep(0.01)\n"
                "print('actual subprocess finished')"
            ),
            2,
        )
        assert job["result_pending"] is True
        assert manager.wait(job["id"], 0)["status"] == "running"
        assert manager.collect() == []
        (tmp_path / "release").write_text("independent parent work\n")
        assert manager.wait(job["id"], 2)["status"] == "completed"
        notification = manager.collect()[0]
        assert notification["result"]["stdout"] == "actual subprocess finished\n"
        assert notification["initial_hashes"] == notification["final_hashes"]
        assert manager.collect() == []
        (tmp_path / "source.py").write_text("version2\n")
        assert notification["final_hashes"] != file_hashes(tmp_path, ["source.py"])
        saved = json.loads((tmp_path / ".background" / (job["id"] + ".json")).read_text())
        assert saved["notified"] is True
        assert [e["action"] for e in manager.events] == ["start", "ended", "notified"]
    finally:
        manager.close()


def test_timeout_and_nonzero_exit_keep_different_actual_results(tmp_path):
    manager = BackgroundManager(tmp_path, [])
    try:
        timeout = manager.start(command("import time; time.sleep(5)"), 0.05)
        failed = manager.start(command("raise SystemExit(7)"), 2)
        assert manager.wait(timeout["id"], 2)["status"] == "timeout"
        assert manager.wait(failed["id"], 2)["status"] == "error"
        by_id = {j["id"]: j for j in manager.collect()}
        assert by_id[failed["id"]]["result"]["exit_code"] == 7
        assert by_id[timeout["id"]]["result"]["exit_code"] != 0
        assert manager.processes == {}
    finally:
        manager.close()


def test_background_close_terminates_pending_processes_and_rejects_new_jobs(tmp_path):
    manager = BackgroundManager(tmp_path, [])
    job = manager.start(command("import time; time.sleep(5)"), 8)
    manager.close()
    assert not manager.threads[job["id"]].is_alive()
    assert manager.jobs[job["id"]]["status"] == "error"
    assert manager.processes == {}
    with pytest.raises(ValueError, match="closed"):
        manager.start("true", 1)


def test_background_boundaries_and_record_symlinks(tmp_path):
    manager = BackgroundManager(tmp_path, [])
    for seconds in (True, 0, -1, 11, float("nan")):
        with pytest.raises(ValueError):
            manager.start("true", seconds)
    manager.close()
    other = tmp_path / "elsewhere"
    other.mkdir()
    (tmp_path / ".background").rmdir()
    (tmp_path / ".background").symlink_to(other)
    with pytest.raises(ValueError, match="symlink"):
        BackgroundManager(tmp_path, [])


def test_cron_ranges_lists_and_day_weekday_or():
    monday = datetime.fromisoformat("2026-11-16T09:00:00+08:00")
    assert validate_cron("*/5 9 1 * 1-5") is None
    assert cron_matches("*/5 9 1 * 1-5", monday)
    assert cron_matches("0,30 9 * * 1", monday)
    assert not cron_matches("0 10 * * *", monday)
    assert cron_matches("0 9 16 * 0", monday)
    for cron in ("* * * *", "*/0 * * * *", "61 * * * *", "* * 0 * *", "* * * * 7"):
        assert validate_cron(cron)


def test_schedule_due_pending_same_minute_and_next_minute(tmp_path):
    scheduler = Scheduler(tmp_path)
    now = datetime.fromisoformat("2026-11-16T09:00:00+08:00")
    job = scheduler.create("* 9 * * *", "run tests", True, True)
    assert scheduler.poll(now - timedelta(hours=1)) == []
    assert len(scheduler.poll(now)) == 1
    assert scheduler.poll(now) == []
    offered = scheduler.take()
    assert offered[0]["id"] == job["id"]
    assert scheduler.poll(now + timedelta(minutes=1)) == []
    scheduler.acknowledge(offered)
    assert scheduler.poll(now) == []
    assert len(scheduler.poll(now + timedelta(minutes=1))) == 1
    assert scheduler.events[-2]["action"] == "model_received_not_task_completed"


def test_failed_model_request_restore_and_restart_reoffers_pending(tmp_path):
    scheduler = Scheduler(tmp_path)
    now = datetime.fromisoformat("2026-11-16T09:00:00+08:00")
    scheduler.create("0 9 * * *", "run tests", False, True)
    scheduler.poll(now)
    offered = scheduler.take()
    scheduler.restore(offered)
    assert scheduler.take() == offered
    restored = Scheduler(tmp_path)
    assert restored.take() == offered
    restored.acknowledge(offered)
    assert restored.list() == []
    assert Scheduler(tmp_path).take() == []


def test_transient_schedule_disappears_and_cancel_clears_pending(tmp_path):
    scheduler = Scheduler(tmp_path)
    job = scheduler.create("* * * * *", "temporary", False, False)
    scheduler.poll(datetime.fromisoformat("2026-11-16T09:00:00+08:00"))
    assert Scheduler(tmp_path).list() == []
    scheduler.cancel(job["id"])
    assert scheduler.take() == []
    assert scheduler.list() == []


def test_schedule_persistence_failure_rolls_back_before_queue_visibility(tmp_path, monkeypatch):
    scheduler = Scheduler(tmp_path)
    job = scheduler.create("* * * * *", "run tests", False, True)
    saved = scheduler.path.read_bytes()

    def fail():
        raise OSError("instructor injected disk failure")

    monkeypatch.setattr(scheduler, "persist", fail)
    with pytest.raises(OSError):
        scheduler.poll(datetime.fromisoformat("2026-11-16T09:00:00+08:00"))
    assert scheduler.queue == []
    assert not scheduler.list()[0]["pending_delivery"]
    assert scheduler.path.read_bytes() == saved
    with pytest.raises(OSError):
        scheduler.cancel(job["id"])
    assert scheduler.list()[0]["id"] == job["id"]


def test_corrupt_saved_schedule_and_string_booleans_are_visible_errors(tmp_path):
    scheduler = Scheduler(tmp_path)
    with pytest.raises(ValueError):
        scheduler.create("* * * * *", "x", "false", True)
    scheduler.path.write_text("invalid json")
    with pytest.raises(ValueError):
        Scheduler(tmp_path)


def test_failed_acknowledgment_restores_queue_and_retains_durable_pending(tmp_path, monkeypatch):
    scheduler = Scheduler(tmp_path)
    scheduler.create("* * * * *", "run tests", False, True)
    scheduler.poll(datetime.fromisoformat("2026-11-16T09:00:00+08:00"))
    offered = scheduler.take()
    saved = scheduler.path.read_bytes()

    def fail():
        raise OSError("instructor injected acknowledgment write failure")

    monkeypatch.setattr(scheduler, "persist", fail)
    with pytest.raises(OSError):
        scheduler.acknowledge(offered)
    assert scheduler.path.read_bytes() == saved
    assert scheduler.take() == offered
    assert Scheduler(tmp_path).take() == offered


def test_timed_wire_types_do_not_widen_previous_lesson_contracts(tmp_path, monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "tools"))
    from model_bridge import e13_contract, normalize_e13_reply

    from lessons.e14_runtime.code import TimedRuntime
    from lessons.e14_runtime.tools import TimedPool

    runtime = TimedRuntime(tmp_path, [])
    tools = TimedPool(runtime).assemble()
    with pytest.raises(ValueError, match="Unknown"):
        e13_contract(tools)
    _, schema = e13_contract(tools, timing=True)
    choices = schema["properties"]["tool_calls"]["items"]["anyOf"]
    advance = next(c for c in choices if c["properties"]["name"]["enum"] == ["advance_clock"])
    assert advance["properties"]["arguments"]["properties"]["seconds"]["type"] == "integer"
    schedule = next(c for c in choices if c["properties"]["name"]["enum"] == ["schedule_cron"])
    assert schedule["properties"]["arguments"]["properties"]["durable"]["type"] == "boolean"
    wire = {"answer": "", "tool_calls": [{"name": "advance_clock", "arguments": {"seconds": 60}}]}
    assert json.loads(normalize_e13_reply(wire)["tool_calls"][0]["arguments_json"])["seconds"] == 60


def test_timed_tools_deny_unauthorized_commands_and_string_booleans(tmp_path):
    from lessons.e14_runtime.code import TimedRuntime
    from lessons.e14_runtime.tools import TimedPool

    runtime = TimedRuntime(tmp_path, [])
    runtime.backgrounds["lead"] = BackgroundManager(tmp_path, [])
    pool = TimedPool(runtime)

    def tool(name, **args):
        return {"name": name, "arguments_json": json.dumps(args)}

    assert (
        pool.dispatch(tool("background_bash", command="sudo true", timeout_seconds=1), tmp_path)[1][
            "status"
        ]
        == "denied"
    )
    assert (
        pool.dispatch(
            tool("background_bash", command="touch unrequested", timeout_seconds=1), tmp_path
        )[1]["status"]
        == "denied"
    )
    assert runtime.backgrounds["lead"].jobs == {}
    assert (
        pool.dispatch(
            tool("schedule_cron", cron="* * * * *", prompt="x", recurring=False, durable="false"),
            tmp_path,
        )[1]["status"]
        == "error"
    )
    assert pool.dispatch(tool("advance_clock", seconds=True), tmp_path)[1]["status"] == "error"
    assert pool.dispatch(tool("advance_clock", seconds=60), tmp_path)[1]["status"] == "ok"
    assert pool.dispatch(tool("advance_clock", seconds=61), tmp_path)[1]["status"] == "error"
    runtime.backgrounds["lead"].close()


def test_scheduled_prompt_is_in_recorded_model_input_and_ack_is_not_execution(tmp_path):
    import copy

    from lessons.e14_runtime.code import TimedRuntime
    from lessons.e14_runtime.tools import TimedPool

    calls = []

    def model(messages, tools, actor):
        calls.append(copy.deepcopy(messages))
        return {
            "reply": {
                "answer": "Received only; did not execute the scheduled task",
                "tool_calls": [],
            },
            "model": {"fixture": True},
        }

    runtime = TimedRuntime(tmp_path, [], model=model)
    job = runtime.scheduler.create("0 9 * * *", "real scheduled text", False, True)
    result = runtime.run_session("Observe only", TimedPool(runtime))
    assert result["model_inputs"][0]["messages"] == calls[0]
    assert any("real scheduled text" in m["content"] for m in calls[0])
    assert runtime.delivery_receipts[0]["jobs"][0]["id"] == job["id"]
    assert runtime.scheduler.list() == []
    assert result["background_jobs"] == []
    assert runtime.delivery_receipts[0]["meaning"] == "model_received_not_task_completed"


def test_model_failure_preserves_pending_schedule_and_records_failed_attempt(tmp_path):
    from lessons.e14_runtime.code import TimedRuntime
    from lessons.e14_runtime.tools import TimedPool

    def model(messages, tools, actor):
        raise RuntimeError("instructor model-transport fixture")

    runtime = TimedRuntime(tmp_path, [], model=model)
    job = runtime.scheduler.create("0 9 * * *", "scheduled task", False, True)
    result = runtime.run_session("Observe fixture failure", TimedPool(runtime))
    assert result["status"] == "model_error"
    assert result["model_inputs"][0]["response_received"] is False
    assert runtime.delivery_receipts == []
    assert runtime.scheduler.take()[0]["id"] == job["id"]
    assert Scheduler(tmp_path).take()[0]["id"] == job["id"]


@pytest.fixture
def completed_timed_fixture(tmp_path, monkeypatch):
    from pathlib import Path

    from lessons.e14_runtime.code import run_case

    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    project = Path(__file__).parents[1]
    case = json.loads((project / "lessons/e14_runtime/cases.jsonl").read_text().splitlines()[0])
    original = case["files"]
    step = 0

    def call(name, **args):
        return {"name": name, "arguments_json": json.dumps(args)}

    def model(messages, tools, actor):
        nonlocal step
        if step == 0:
            calls = [
                call(
                    "todo_write",
                    todos=[
                        {
                            "content": "actual regression and scheduled check",
                            "status": "in_progress",
                        }
                    ],
                ),
                call(
                    "write_file",
                    path="shipping.py",
                    content=original["shipping.py"].replace(
                        "max(0, (weight_grams - 1000) // 1000)", "(weight_grams - 1) // 1000"
                    ),
                ),
                call(
                    "write_file",
                    path="checkout.py",
                    content=original["checkout.py"].replace(
                        "shipping_fee(weight_grams)", "shipping_fee(weight_grams, expedited)"
                    ),
                ),
                call("background_bash", command="python3 slow_tests.py", timeout_seconds=5),
                call("read_file", path="review.txt"),
            ]
        elif step == 1:
            result = next(m["content"] for m in reversed(messages) if m["role"] == "tool")[3]
            ident = json.loads(result["output"])["id"]
            calls = [
                call("background_wait", id=ident, seconds=2),
                call(
                    "schedule_cron",
                    cron="1 9 * * *",
                    prompt=case["scheduled_prompt"],
                    recurring=False,
                    durable=True,
                ),
                call("advance_clock", seconds=60),
            ]
        elif step == 2:
            calls = [call("background_bash", command="python3 slow_tests.py", timeout_seconds=5)]
        elif step == 3:
            latest = next(m["content"] for m in reversed(messages) if m["role"] == "tool")
            ident = json.loads(latest[0]["output"])["id"]
            calls = [call("background_wait", id=ident, seconds=2)]
        elif step == 4:
            calls = [
                call(
                    "todo_write",
                    todos=[
                        {"content": "actual regression and scheduled check", "status": "completed"}
                    ],
                )
            ]
        else:
            calls = []
        step += 1
        return {
            "reply": {
                "answer": "Instructor callback, actual tools; not live model" if not calls else "",
                "tool_calls": calls,
            },
            "model": {"fixture": True},
        }

    row = run_case(case, model=model)
    row["repetition"] = 1
    criteria = json.loads((project / "evaluation_private/e14.json").read_text())
    return row, criteria, tmp_path / row["run_id"]


def test_actual_process_and_schedule_fixture_passes_independent_checks(completed_timed_fixture):
    from lessons.e14_runtime.eval import grade_row

    row, criteria, _ = completed_timed_fixture
    assert row["origin"] == "injected_model_callback_not_live_execution"
    grade = grade_row(row, criteria)
    assert grade["passed"] is True, grade["checks"]
    assert (
        grade["resources"]["application_model"]["provider_counter_totals"]["input_tokens"] is None
    )
    json.dumps(row, allow_nan=False)


def test_correct_artifact_does_not_hide_deleted_background_record(completed_timed_fixture):
    from lessons.e14_runtime.eval import grade_row

    row, criteria, workspace = completed_timed_fixture
    job = row["lead"]["background_jobs"][0]
    (workspace / ".background" / (job["id"] + ".json")).unlink()
    grade = grade_row(row, criteria)
    assert grade["artifacts"]["passed"] is True
    assert grade["checks"]["background_records_match_disk"] is False
    assert grade["passed"] is False


def test_post_receipt_code_edit_invalidates_old_test_result(completed_timed_fixture):
    from lessons.e14_runtime.eval import grade_row

    row, criteria, workspace = completed_timed_fixture
    with (workspace / "shipping.py").open("a") as file:
        file.write("\n# behavior-neutral edit after the tests\n")
    grade = grade_row(row, criteria)
    assert grade["artifacts"]["passed"] is True
    assert grade["checks"]["current_version_test_receipts"] is False
    assert grade["checks"]["actual_files_match_report"] is False
    assert grade["passed"] is False


def test_missing_usage_stays_unknown_and_cache_is_not_added_twice():
    from lessons.e14_runtime.resources import usage_ledger

    metadata = {
        "usage": [{"input_tokens": 100, "cached_input_tokens": 70, "output_tokens": 20}],
        "reported_model": None,
    }
    ledger = usage_ledger([metadata])
    assert ledger["provider_counter_totals"]["input_tokens"] == 100
    assert ledger["provider_counter_totals"]["cached_input_tokens"] == 70
    assert ledger["real_bill"] is None
    assert ledger["responses_without_model_id"] == 1
    assert usage_ledger([metadata, {}])["provider_counter_totals"]["input_tokens"] is None
    assert usage_ledger([])["provider_counter_totals"]["input_tokens"] is None
