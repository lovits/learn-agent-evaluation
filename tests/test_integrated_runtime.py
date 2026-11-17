import asyncio
import hashlib
import json
import os
import signal
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace

import httpx
import pytest
from anthropic import Anthropic
from anthropic.types import Message

from integrated_agent.runtime import PROJECT, UPSTREAM, RecordedMessages, Runtime
from integrated_agent.transport import MessagesHandler, model_contract, wire_response


def fixture_result(answer="[]", tools=None):
    return {
        "text": json.dumps({"answer": answer, "tool_calls": tools or []}),
        "usage": [{"input_tokens": 16, "output_tokens": 4}],
        "origin": "deterministic_test_callback_not_provider_execution",
    }


class FixtureSDK:
    """Native SDK result objects backed by explicit test callbacks, never provider data."""

    def __init__(self, actions=()):
        self.actions = iter(actions)
        self.messages = self

    def create(self, **request):
        if request.get("tools"):
            result = next(self.actions, fixture_result("Fixture task ended"))
        elif "focused workflow agent" in request.get("system", ""):
            result = fixture_result('{"issues":[]}')
        else:
            result = fixture_result()
        return Message.model_validate(wire_response(request, result))


@pytest.fixture
def runtime(tmp_path):
    previous = signal.getsignal(signal.SIGTERM)
    instance = Runtime(tmp_path, sdk=FixtureSDK(), approved_commands=[])
    try:
        yield instance
    finally:
        instance.close()
        signal.signal(signal.SIGTERM, previous)


def test_vendored_sources_exactly_match_their_pinned_manifest():
    manifest = json.loads((UPSTREAM / "provenance.json").read_text())
    assert manifest["commit"] == "448c75bb596917ad196cc1fb7558f459c5c50fdd"
    for file in manifest["files"]:
        assert hashlib.sha256((UPSTREAM / file["path"]).read_bytes()).hexdigest() == file["sha256"]
    assert "Copyright (c) 2024 shareAI Lab" in (UPSTREAM / "LICENSE").read_text()


def test_real_http_and_native_sdk_preserve_tools_unicode_and_usage():
    seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), MessagesHandler)

    def complete(prompt, **options):
        seen.append((prompt, options))
        return fixture_result(
            "读取文件", [{"name": "read_file", "arguments_json": '{"path":"a.py"}'}]
        )

    server.complete_model = complete
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with Anthropic(
            api_key="fixture",
            base_url=f"http://127.0.0.1:{server.server_port}",
            max_retries=0,
            http_client=httpx.Client(trust_env=False),
        ) as client:
            result = client.messages.create(
                model="course-local-codex",
                max_tokens=100,
                messages=[{"role": "user", "content": "请读文件"}],
                tools=[{"name": "read_file", "input_schema": {"type": "object"}}],
            )
        assert result.content[0].text == "读取文件"
        assert result.content[1].input == {"path": "a.py"}
        assert result.stop_reason == "tool_use" and result.usage.input_tokens == 16
        assert result.course_transport["origin"].startswith("deterministic_test")
        assert "model" not in seen[0][1]
        assert seen[0][1]["schema"]["properties"]["tool_calls"]["maxItems"] == 8
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


def test_bridge_rejects_unavailable_tools_missing_usage_and_nonobjects():
    request = {"model": "course-local-codex", "messages": [{"role": "user", "content": "x"}]}
    _, schema = model_contract(request)
    assert schema["properties"]["tool_calls"]["maxItems"] == 0
    with pytest.raises(ValueError, match="Too many"):
        wire_response(request, fixture_result(tools=[{"name": "bash", "arguments_json": "{}"}]))
    invalid = fixture_result()
    invalid["usage"] = []
    with pytest.raises(ValueError, match="actual input/output usage"):
        wire_response(request, invalid)
    with pytest.raises(TypeError, match="object"):
        model_contract([])
    with pytest.raises(ValueError, match="duplicate"):
        model_contract({**request, "tools": [{"name": "read"}, {"name": "read"}]})


def test_runtime_preserves_environment_and_loads_native_skill_registry(runtime):
    assert len(runtime.host.assemble_tool_pool()[0]) == 27
    assert "repair" in runtime.host.SKILL_REGISTRY
    assert "# Repair workflow" in runtime.host.load_skill("repair")
    assert runtime.workflow.STORE.parent == runtime.workspace
    assert (
        "course-review"
        in runtime.workflow.WORKFLOW_TOOL["input_schema"]["properties"]["name"]["enum"]
    )


def test_real_file_and_shell_execution_with_native_hooks_and_recorded_inputs(runtime, tmp_path):
    command = 'python3 -c "print(6 * 8)"'
    runtime.approved_commands = [command]
    runtime.model.sdk = FixtureSDK(
        [
            fixture_result(
                tools=[
                    {
                        "name": "write_file",
                        "arguments_json": '{"path":"answer.py","content":"print(6 * 8)\\n"}',
                    }
                ]
            ),
            fixture_result(
                tools=[{"name": "bash", "arguments_json": json.dumps({"command": command})}]
            ),
            fixture_result("Executed output 48"),
        ]
    )
    ledger = tmp_path.parent / (tmp_path.name + "-calls.jsonl")
    runtime.model.ledger = ledger
    result = runtime.submit("Write answer.py and actually compute 6 * 8")
    assert (tmp_path / "answer.py").read_text() == "print(6 * 8)\n"
    outputs = [e["output"] for e in result["audit"] if e["phase"] == "PostToolUse"]
    assert any("48" in output for output in outputs)
    assert len(result["model_calls"]) == 4  # Three worker responses plus native memory extraction.
    assert all(c["response_received"] for c in result["model_calls"])
    assert len(ledger.read_text().splitlines()) == 8
    assert "api_key" not in ledger.read_text()


def test_permission_denial_never_reaches_shell_or_post_hook(runtime, tmp_path):
    runtime.model.sdk = FixtureSDK(
        [
            fixture_result(
                tools=[{"name": "bash", "arguments_json": '{"command":"touch forbidden"}'}]
            ),
            fixture_result("Permission was denied"),
        ]
    )
    result = runtime.submit("Observe a declared denied command")
    assert not (tmp_path / "forbidden").exists()
    assert any(e["phase"] == "batch_denied" for e in result["audit"])
    assert not any(e["phase"] == "PostToolUse" for e in result["audit"])
    outside = SimpleNamespace(name="write_file", input={"path": "../escape"}, id="tool-fixture")
    assert "outside" in runtime.host.trigger_hooks("PreToolUse", outside)


def test_late_bound_docs_tools_read_actual_mounted_knowledge(runtime, tmp_path, monkeypatch):
    kb = tmp_path / "mounted-kb"
    kb.mkdir()
    doc = kb / "api.md"
    doc.write_text("shipping contract revision integrated-1: expedited adds 400 cents")
    monkeypatch.setenv("KNOWLEDGE_DIR", str(kb))
    initial = [t["name"] for t in runtime.host.assemble_tool_pool()[0]]
    assert "mcp__docs__search" not in initial
    runtime.host.connect_mcp("docs")
    tools, handlers = runtime.host.assemble_tool_pool()
    assert "mcp__docs__search" in [t["name"] for t in tools]
    output = json.loads(handlers["mcp__docs__search"](query="expedited"))
    assert output[0]["text"] == doc.read_text()
    assert output[0]["sha256"] == hashlib.sha256(doc.read_bytes()).hexdigest()
    assert doc.read_text().endswith("400 cents")


def test_native_task_dependencies_and_wrong_owner_are_enforced(runtime):
    host = runtime.host
    first, second = host.create_task("first"), host.create_task("second")
    host.update_task(second.id, [first.id])
    assert not host.can_start(second.id)
    with pytest.raises(ValueError, match="cycle"):
        host.update_task(first.id, [second.id])
    assert host.claim_task(first.id, "worker").startswith("Claimed ")
    assert "cannot complete" in host.complete_task(first.id, "wrong").lower()
    assert host.load_task(first.id).owner == "worker"
    assert host.load_task(first.id).status == "in_progress"
    host.complete_task(first.id, "worker")
    assert host.can_start(second.id)


def test_native_workflow_interruption_and_resume_reuse_durable_completed_calls(
    runtime, tmp_path, monkeypatch
):
    (tmp_path / "api.py").write_text("def fee(): return 600\n")
    monkeypatch.setenv("COURSE_INTERRUPT_REVIEW", "after-inspect")
    first = asyncio.run(runtime.workflow.run_workflow("course-review", {"files": ["api.py"]}))
    run_id = first["launched"]["runId"]
    assert first["task"]["status"] == "failed"
    assert len(runtime.model.calls) == 2
    journal = runtime.workflow.STORE / (run_id + ".journal.jsonl")
    assert len(journal.read_text().splitlines()) == 2
    monkeypatch.delenv("COURSE_INTERRUPT_REVIEW")
    resumed = asyncio.run(runtime.workflow.run_workflow("course-review", resume_from_run_id=run_id))
    assert resumed["task"]["status"] == "completed"
    assert len(runtime.model.calls) == 3
    assert len(journal.read_text().splitlines()) == 3
    assert resumed["result"] == {"issues": []}
    original = journal.read_text()
    journal.write_text(original + '{"key":')
    with pytest.raises(runtime.workflow.WorkflowInputError, match="invalid resume journal"):
        asyncio.run(runtime.workflow.run_workflow("course-review", resume_from_run_id=run_id))
    assert journal.read_text() == original + '{"key":'


def test_recording_budget_and_sdk_error_remain_unscored(tmp_path):
    class BrokenSDK:
        messages = None

        def create(self, **kwargs):
            raise RuntimeError("declared fixture provider failure")

    sdk = BrokenSDK()
    sdk.messages = sdk
    recorder = RecordedMessages(sdk, maximum=1)
    recorder.ledger = tmp_path / "calls.jsonl"
    with pytest.raises(RuntimeError, match="fixture provider failure"):
        recorder.create(model="fixture", messages=[])
    with pytest.raises(RuntimeError, match="budget exhausted"):
        recorder.create(model="fixture", messages=[])
    assert recorder.calls[0]["response_received"] is False
    assert recorder.calls[0]["error"]["type"] == "RuntimeError"
    assert len(recorder.ledger.read_text().splitlines()) == 2


def test_local_proxy_import_settings_are_restored_even_with_ipv6_skip_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "localhost,::1")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "fixture-original-token")
    previous = signal.getsignal(signal.SIGTERM)
    try:
        instance = Runtime(tmp_path, sdk=FixtureSDK(), approved_commands=[])
        assert os.environ["NO_PROXY"] == "localhost,::1"
        assert os.environ["ANTHROPIC_AUTH_TOKEN"] == "fixture-original-token"
        instance.close()
    finally:
        signal.signal(signal.SIGTERM, previous)
    assert PROJECT.is_dir()


def test_runtime_native_sdk_health_does_not_send_empty_or_inherited_bearer(tmp_path, monkeypatch):
    received = []

    class Health(MessagesHandler):
        def do_GET(self):
            received.append(self.headers.get("Authorization"))
            super().do_GET()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Health)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    monkeypatch.setenv("INTEGRATED_BRIDGE_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "fixture-do-not-export")
    previous = signal.getsignal(signal.SIGTERM)
    instance = None
    try:
        instance = Runtime(tmp_path, approved_commands=[])
        assert instance.model.sdk.get("/healthz", cast_to=httpx.Response).status_code == 200
        assert received == [None]
        assert os.environ["ANTHROPIC_AUTH_TOKEN"] == "fixture-do-not-export"
        assert instance.model.calls == []
    finally:
        if instance:
            instance.close()
            instance.model.sdk.close()
        signal.signal(signal.SIGTERM, previous)
        server.shutdown()
        server.server_close()
        worker.join()


@pytest.mark.parametrize(
    "snapshot,status",
    [
        ({"final_text": "[Error] declared SDK failure"}, "application_error"),
        ({"goal_active": True, "final_text": "not done"}, "goal_incomplete"),
    ],
)
def test_cli_return_is_not_success_when_native_error_or_goal_remains(
    tmp_path, monkeypatch, snapshot, status
):
    from integrated_agent import __main__ as cli

    class FixtureRuntime:
        model = SimpleNamespace(ledger=None)

        def __init__(self, *args, **kwargs):
            pass

        def start_services(self):
            pass

        def submit(self, *args):
            pass

        def wait_until_settled(self, *args):
            return True

        def snapshot(self):
            return snapshot

        def close(self):
            pass

    workspace = tmp_path / "work"
    workspace.mkdir()
    report = tmp_path / "report.json"
    monkeypatch.setattr(cli, "Runtime", FixtureRuntime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "integrated_agent",
            "fixture task",
            "--workspace",
            str(workspace),
            "--report",
            str(report),
            "--wait-seconds",
            "0",
        ],
    )
    assert cli.main() == 1
    result = json.loads(report.read_text())
    assert result["status"] == status and result["independent_acceptance"] is None
