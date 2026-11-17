import copy
import hashlib
import json

import pytest

from lessons.e01_agent_baseline.code import prepare_workspace
from lessons.e12_conversation.code import HERE, Conversation, candidate
from lessons.e12_conversation.context import ContextCompactor, Summary, check_pairs, size
from lessons.e12_conversation.eval import (
    evaluate,
    evaluate_simulations,
    expected_cases,
    judge_one,
    native_samples,
    verify_artifacts,
)
from lessons.e12_conversation.memory import MemoryStore
from lessons.e12_conversation.tools import PagedToolPool


class StubSummary:
    def generate(self, instruction, payload, schema):
        assert schema is Summary
        return Summary(
            facts=["fixture summary"],
            constraints=["Keep exact shipping_fee signature"],
            remaining=["Read the current request"],
        )


def batch(output):
    return [
        {
            "role": "assistant",
            "content": {
                "answer": "read",
                "tool_calls": [
                    {"name": "read_file", "arguments_json": '{"path":"diagnostics.log"}'}
                ],
            },
        },
        {"role": "tool", "content": [{"call_id": "m1:t1", "status": "ok", "output": output}]},
    ]


def test_large_output_is_recoverable_without_mutating_raw_history(tmp_path):
    output = "full original diagnostic result\n" * 1000
    messages = [{"role": "user", "content": "Inspect logs"}, *batch(output)]
    original = copy.deepcopy(messages)
    compact = ContextCompactor(tmp_path, StubSummary(), limit=5000)
    prepared = compact.prepare(messages, "Inspect logs")
    assert messages == original
    event = next(e for e in compact.events if e["phase"] == "tool_result_budget")
    assert (tmp_path / event["path"]).read_text() == output
    assert event["sha256"] == hashlib.sha256(output.encode()).hexdigest()
    assert size(prepared) < size(original)
    check_pairs(prepared)


def test_snip_preserves_pair_and_restores_current_request(tmp_path):
    messages = [
        {"role": "user", "content": "Initial request"},
        {"role": "user", "content": "Current request"},
    ]
    for _ in range(9):
        messages.extend(batch("small output"))
    compact = ContextCompactor(tmp_path, StubSummary(), limit=100000)
    prepared = compact.prepare(messages, "Current request")
    assert len(prepared) < len(messages)
    assert prepared[-1] == {"role": "user", "content": "Current request"}
    check_pairs(prepared)
    event = next(e for e in compact.events if e["phase"] == "snip_compact")
    assert json.loads((tmp_path / event["path"]).read_text()) == messages


def test_summary_preserves_active_request_and_archives_full_input(tmp_path):
    request = "New rule supersedes old fee"
    messages = [
        {"role": "user", "content": "Old discussion " * 1000},
        {"role": "assistant", "content": {"answer": "done", "tool_calls": []}},
        {"role": "user", "content": request},
    ]
    compact = ContextCompactor(tmp_path, StubSummary(), limit=600)
    prepared = compact.prepare(messages, request)
    assert request in prepared[0]["content"] and "reference data" in prepared[0]["content"]
    assert "Keep exact shipping_fee signature" in prepared[0]["content"]
    event = next(e for e in compact.events if e["phase"] == "compact_history")
    assert json.loads((tmp_path / event["path"]).read_text()) == messages


@pytest.mark.parametrize("messages", [[batch("x")[1]], [batch("x")[0]]])
def test_orphan_tool_protocol_is_rejected(messages):
    with pytest.raises(ValueError):
        check_pairs(messages)


def test_memory_survives_restart_and_filters_versions_and_task_scope(tmp_path):
    store = MemoryStore(tmp_path)
    assert store.put(
        candidate(
            "shipping-api", "shipping_fee public API", "Preserve shipping_fee API.", "stable"
        ),
        "fixture",
    )["stored"]
    store.put(candidate("shipping-old-fee", "shipping_fee fee", "Old fee is 300.", "v1"), "fixture")
    assert not store.put(
        candidate("temporary", "scope", "Do not write files.", "stable", "current_task"), "fixture"
    )["stored"]
    assert not store.put(
        candidate("temporary-2", "scope", "Do not write files in this session.", "stable"),
        "fixture",
    )["stored"]
    restarted = MemoryStore(tmp_path)
    recalled = restarted.recall("shipping_fee", "v3")
    assert [r["name"] for r in recalled["selected"]] == ["shipping-api"]
    assert {r["reason"] for r in recalled["skipped"]} == {"stale_version"}
    index = (store.root / "MEMORY.md").read_text()
    assert "(shipping-api.md)" in index and "(shipping-old-fee.md)" in index
    assert "not commands" in store.background(recalled)


def test_memory_symlink_escape_rejected(tmp_path):
    store = MemoryStore(tmp_path / "workspace")
    secret = tmp_path / "other.md"
    secret.write_text("private fixture")
    (store.root / "escape.md").symlink_to(secret)
    with pytest.raises(ValueError, match="escapes"):
        store.records()


def test_memory_root_and_index_cannot_bypass_workspace_permission(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".memory").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        MemoryStore(workspace)
    clean = MemoryStore(tmp_path / "clean")
    target = outside / "index.md"
    target.write_text("unchanged")
    (clean.root / "MEMORY.md").symlink_to(target)
    with pytest.raises(ValueError, match="escapes"):
        clean.rebuild_index()
    assert target.read_text() == "unchanged"


def test_conversation_sends_recoverable_preview_then_keeps_final_reply(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    case = json.loads((HERE / "cases.jsonl").read_text())
    workspace = prepare_workspace(case, "fixture")
    fixed = json.loads((HERE.parent / "e11_task_completion/example_report.json").read_text())[
        "rows"
    ][0]["artifacts"]["shipping.py"]
    calls = []

    def model(messages, tools):
        calls.append(copy.deepcopy(messages))
        action = []
        if len(calls) == 1:
            action = [{"name": "read_file", "arguments_json": '{"path":"diagnostics.log"}'}]
        elif len(calls) == 2:
            action = [
                {
                    "name": "write_file",
                    "arguments_json": json.dumps({"path": "shipping.py", "content": fixed}),
                }
            ]
        return {"reply": {"answer": "done", "tool_calls": action}}

    conversation = Conversation(workspace, case, StubSummary(), compact=True, model=model)
    row = conversation.run_turn(case["turns"][0]["task"], "v1")
    assert row["goal_status"] == "ready_for_external_verification"
    assert conversation.visible[-1]["content"]["answer"] == "done"
    assert any(e["phase"] == "tool_result_budget" for e in conversation.compactor.events)
    assert len(conversation.raw) == 6
    assert row["artifacts"]["test_shipping.py"] == case["files"]["test_shipping.py"]


def test_version_update_is_not_forgetting_and_signature_failure_is_decidable():
    criteria = [
        {"id": "new-range", "arguments": {"weight_grams": 5001}, "expected": {}},
        {"id": "fee", "arguments": {"weight_grams": 1000, "expedited": True}, "expected": {}},
    ]
    assert expected_cases(criteria, "v1")[0]["expected"] == {"exception": "ValueError"}
    assert expected_cases(criteria, "v3")[0]["expected"] == {"value": 1600, "type": "int"}
    assert expected_cases(criteria, "v1")[1]["expected"]["value"] == 900
    assert expected_cases(criteria, "v3")[1]["expected"]["value"] == 1000
    case = json.loads((HERE / "cases.jsonl").read_text())
    artifacts = {**case["files"], "shipping.py": "def shipping_fee(weight):\n    return 600\n"}
    result = verify_artifacts(artifacts, case, criteria, "v3")
    assert result["status"] == "scored" and result["passed"] is False
    assert result["checks"]["signature_preserved"] is False


def test_native_multiturn_samples_roundtrip_and_reject_orphan_tools():
    from ragas.dataset_schema import MultiTurnSample
    from ragas.messages import AIMessage, HumanMessage, ToolMessage

    deep, ragas = native_samples([{"user": "Keep the signature", "assistant": "Kept it"}])
    assert [t.role for t in deep.turns] == ["user", "assistant"]
    assert len(ragas.user_input) == 2
    with pytest.raises(ValueError, match="tools were called"):
        MultiTurnSample(
            user_input=[HumanMessage(content="x"), AIMessage(content="x"), ToolMessage(content="x")]
        )


def test_native_retention_yes_is_attrition_and_empty_verdicts_are_not_coverage():
    from deepeval.metrics import KnowledgeRetentionMetric
    from deepeval.metrics.knowledge_retention.schema import KnowledgeRetentionVerdict

    from lessons.e03_judges.eval import DeepJudge, Transport

    metric = KnowledgeRetentionMetric(
        model=DeepJudge(Transport()), async_mode=False, include_reason=False
    )
    metric.verdicts = [
        KnowledgeRetentionVerdict(verdict="yes"),
        KnowledgeRetentionVerdict(verdict="no"),
    ]
    assert metric._calculate_score() == 0.5
    metric.verdicts = []
    assert metric._calculate_score() == 1


def test_saved_tool_output_is_recoverable_by_the_agent_in_pages(tmp_path):
    text = "实际原始日志\n" * 1500
    messages = [{"role": "user", "content": "Inspect logs"}, *batch(text)]
    compactor = ContextCompactor(tmp_path, StubSummary(), limit=100000)
    prepared = compactor.prepare(messages, "Inspect logs")
    recovery = prepared[-1]["content"][0]["recovery"]
    pool = PagedToolPool()
    reader = next(t for t in pool.assemble() if t["name"] == "read_file")
    assert reader["input_schema"]["required"] == ["path"]
    assembled, offset = "", 0
    while offset < len(text):
        call = {
            "name": "read_file",
            "arguments_json": json.dumps(
                {"path": recovery["path"], "offset": str(offset), "limit": "2000"}
            ),
        }
        policy, result = pool.dispatch(call, tmp_path)
        assert policy["decision"] == "allow" and result["status"] == "ok"
        assert len(result["output"]) <= 2000
        assembled += result["output"]
        assert result["next_offset"] > offset
        offset = result["next_offset"]
    assert assembled == text


@pytest.mark.parametrize(
    "args",
    [
        {"path": "x", "offset": "-1"},
        {"path": "x", "limit": "2001"},
        {"path": "x", "limit": "0"},
        {"path": "x", "offset": 3},
    ],
)
def test_page_arguments_are_validated(tmp_path, args):
    policy, result = PagedToolPool().dispatch(
        {"name": "read_file", "arguments_json": json.dumps(args)}, tmp_path
    )
    assert policy["decision"] == "not_checked" and result["status"] == "invalid_arguments"


def test_page_reading_preserves_workspace_permission(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("unchanged")
    call = {
        "name": "read_file",
        "arguments_json": json.dumps({"path": "../outside.txt", "offset": "0"}),
    }
    policy, result = PagedToolPool().dispatch(call, workspace)
    assert policy["decision"] == "deny" and result["status"] == "denied"


def test_deterministic_controls_exercise_snip_and_micro_without_models():
    from lessons.e12_conversation.context_controls import run

    rows = run()
    assert all(r["saved_files_read_back_match_hashes"] for r in rows)
    assert any(e["phase"] == "snip_compact" for e in rows[0]["events"])
    assert any(e["phase"] == "micro_compact" for e in rows[1]["events"])


def test_simulator_completion_is_separate_from_scenario_coverage():
    from lessons.e12_conversation.simulate import coverage, stop_after_one

    assert not stop_after_one(0).should_end
    assert stop_after_one(1).should_end
    assert not coverage(["v1"])["all_phases_requested_in_order"]
    assert coverage(["v1", "v2", "v3"])["all_phases_requested_in_order"]
    assert not coverage(["v3", "v2", "v1"])["all_phases_requested_in_order"]


def test_summary_retains_latest_real_tool_evidence_for_stop_decision(tmp_path):
    request = "Keep signature and repair current rules"
    messages = [
        {"role": "user", "content": "old discussion " * 1000},
        {"role": "assistant", "content": {"answer": "working", "tool_calls": []}},
        {"role": "user", "content": request},
        *batch("Actual tests passed; exit_code=0"),
    ]
    compact = ContextCompactor(tmp_path, StubSummary(), limit=1000)
    prepared = compact.prepare(messages, request)
    assert prepared[-2:] == messages[-2:]
    assert "Current user request" in prepared[0]["content"]
    check_pairs(prepared)


def test_correct_files_do_not_turn_a_step_limit_into_completed_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    case = json.loads((HERE / "cases.jsonl").read_text())
    source = (
        json.loads((HERE.parent / "e11_task_completion/example_report.json").read_text())["rows"][
            0
        ]["artifacts"]["shipping.py"]
        .replace("> 5000", "> 6000")
        .replace("(300 if", "(400 if")
    )
    artifacts = {"shipping.py": source, "test_shipping.py": case["files"]["test_shipping.py"]}
    run_id = "a" * 32
    workspace = tmp_path / run_id
    workspace.mkdir()
    for name, text in artifacts.items():
        (workspace / name).write_text(text)
    recall = {
        "selected": [
            {"origin": "live_model_extraction"},
            {"origin": "instructor_seeded_injection_data"},
        ],
        "skipped": [{"reason": "stale_version"}],
    }
    row = {
        "run_id": run_id,
        "artifacts": artifacts,
        "compact_enabled": True,
        "memory": {"temporary": {"stored": False}},
        "turns": [
            {
                "version": "v3",
                "goal_status": "review_error",
                "artifacts": artifacts,
                "memory_recall": recall,
            }
        ],
    }
    criteria = [{"id": "boundary", "arguments": {"weight_grams": 6000}, "expected": {}}]
    report = evaluate({"case": case, "rows": [row]}, criteria)
    assert report["rows"][0]["final_current_workspace"]["passed"] is True
    assert report["passed"] is False


def test_missing_final_response_is_unscored_without_judge_requests():
    row = judge_one(
        {
            "id": "incomplete",
            "origin": "unit_fixture",
            "pairs": [{"user": "Finish the task", "assistant": None}],
        }
    )
    assert row["calls"] == [] and row["sample_status"] == "invalid_or_incomplete"
    assert all(v["score"] is None for v in row["scores"].values())


def test_non_utf8_page_is_a_tool_error_not_an_agent_crash(tmp_path):
    (tmp_path / "binary.log").write_bytes(b"\xff")
    call = {
        "name": "read_file",
        "arguments_json": json.dumps({"path": "binary.log", "offset": "0"}),
    }
    policy, result = PagedToolPool().dispatch(call, tmp_path)
    assert policy["decision"] == "allow" and result["status"] == "error"


def test_model_bridge_error_body_is_preserved_for_diagnosis(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError

    from lessons.e12_conversation import code

    def unavailable(*args, **kwargs):
        raise HTTPError(
            "http://fixture", 502, "failed", None, BytesIO(b'{"error":"provider timeout fixture"}')
        )

    monkeypatch.setattr(code, "urlopen", unavailable)
    with pytest.raises(RuntimeError, match="provider timeout fixture"):
        code.call_model([{"role": "user", "content": "fixture"}], PagedToolPool().assemble())


def test_scenario_recovery_keeps_failed_turn_and_requires_all_phases_to_finish(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))
    case = json.loads((HERE / "cases.jsonl").read_text())
    base = json.loads((HERE.parent / "e11_task_completion/example_report.json").read_text())[
        "rows"
    ][0]["artifacts"]["shipping.py"]
    sources = {
        "v1": base,
        "v2": base.replace("(300 if", "(400 if"),
        "v3": base.replace("(300 if", "(400 if").replace("> 5000", "> 6000"),
    }

    def turn(version, ready=True, initial=False):
        return {
            "version": version,
            "goal_status": "ready_for_external_verification" if ready else "review_error",
            "artifacts": {
                "shipping.py": case["files"]["shipping.py"] if initial else sources[version],
                "test_shipping.py": case["files"]["test_shipping.py"],
            },
        }

    normal = {
        "variant": "default_outcome_stop",
        "run_id": "b" * 32,
        "coverage_audit": {"all_phases_requested_in_order": True},
        "agent_turns": [turn("v1", False, True), turn("v1"), turn("v2"), turn("v3")],
    }
    early = {
        "variant": "controlled_early_stop",
        "run_id": "c" * 32,
        "coverage_audit": {"all_phases_requested_in_order": False},
        "agent_turns": [turn("v1")],
    }
    for row in (normal, early):
        workspace = tmp_path / row["run_id"]
        workspace.mkdir()
        for name, text in row["agent_turns"][-1]["artifacts"].items():
            (workspace / name).write_text(text)
    criteria = [{"id": "range", "arguments": {"weight_grams": 6000}, "expected": {}}]
    report = evaluate_simulations({"rows": [normal, early]}, case, criteria)
    assert report["expected_controls_observed"] is True
    assert report["rows"][0]["runtime_goals_ready"] is False
    assert report["rows"][0]["completed_after_retries"] is True
    assert report["rows"][0]["states"][0]["verification"]["passed"] is False
    normal["agent_turns"][-1]["goal_status"] = "review_error"
    assert (
        evaluate_simulations({"rows": [normal, early]}, case, criteria)[
            "expected_controls_observed"
        ]
        is False
    )


def test_exposure_counts_actual_preview_and_pages_not_full_archived_output():
    from lessons.e12_conversation.exposure import log_exposure

    original = "0123456789" * 100
    saved = {
        "phase": "tool_result_budget",
        "path": ".task_outputs/full.txt",
        "sha256": hashlib.sha256(original.encode()).hexdigest(),
        "chars": len(original),
    }

    def messages(offset, text, truncated=False, path="diagnostics.log"):
        call = {
            "name": "read_file",
            "arguments_json": json.dumps({"path": path, "offset": str(offset)}),
        }
        result = {"status": "ok", "output": text}
        if truncated:
            result.update(
                output="Full output saved\nPreview:\n" + text, visible_output_truncated=True
            )
        return [
            {"role": "assistant", "content": {"tool_calls": [call]}},
            {"role": "tool", "content": [result]},
        ]

    inputs = [{"messages": messages(0, original[:300], True)}]
    row = {"sessions": [{"compaction_events": [saved], "model_inputs": inputs}]}
    assert log_exposure(row, original)["unique_chars_exposed"] == 300
    assert not log_exposure(row, original)["complete_text_exposed"]
    inputs.append({"messages": messages(300, original[300:], path=saved["path"])})
    inputs.append(inputs[-1])
    report = log_exposure(row, original)
    assert report["unique_chars_exposed"] == len(original) and report["complete_text_exposed"]
    for request in inputs[1:]:
        request["response_received"] = False
    assert log_exposure(row, original)["unique_chars_exposed"] == 300


def test_successful_input_receipts_survive_shortened_history(tmp_path):
    seen = []

    class SummaryWithReceipts:
        def generate(self, instruction, payload, schema):
            seen.append(payload)
            return Summary(facts=["fixture summary"], constraints=[], remaining=[])

    compact = ContextCompactor(tmp_path, SummaryWithReceipts(), limit=900)
    messages = [{"role": "user", "content": "Inspect logs"}, *batch("x" * 2000)]
    compact.record_sent(messages)
    assert compact.exposed_ranges["diagnostics.log"] == [[0, 2000]]
    prepared = compact.prepare(messages, "Inspect logs")
    assert seen[-1]["successful_request_text_ranges"]["diagnostics.log"] == [[0, 2000]]
    assert compact.events[-2]["successful_request_text_ranges"]["diagnostics.log"] == [[0, 2000]]
    compact.record_sent(prepared)
    assert compact.exposed_ranges["diagnostics.log"] == [[0, 2000]]


def test_simulator_failure_preserves_partial_coverage_without_fabricating_sample(tmp_path, monkeypatch):
    from lessons.e12_conversation import simulate

    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path))

    class InterruptedSimulator:
        def __init__(self, **kwargs):
            pass

        def simulate(self, *args, **kwargs):
            raise RuntimeError("controlled provider failure")

    monkeypatch.setattr(simulate, "ConversationSimulator", InterruptedSimulator)
    case = json.loads((HERE / "cases.jsonl").read_text())
    row = simulate.run_simulation(case, False)
    assert row["status"] == "error" and row["sample"] is None
    assert row["error"] == "RuntimeError: controlled provider failure"
    assert row["agent_turns"] == []
    assert row["coverage_audit"]["all_phases_requested_in_order"] is False
    report = evaluate_simulations({"rows": [row]}, case, [])
    assert report["rows"][0]["scenario_complete"] is False
    assert report["expected_controls_observed"] is False
