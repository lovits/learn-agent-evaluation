"""Host adapters around unchanged, pinned Learn Claude Code mechanisms."""

import asyncio
import copy
import importlib.util
import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path

import httpx
from anthropic import Anthropic
from deepeval.tracing import observe, update_current_span

from eval_course.knowledge import catalog, search

from .workflows import install as install_course_workflow

PROJECT = Path(__file__).resolve().parent.parent
UPSTREAM = PROJECT / "vendor/learn_claude_code"


def json_value(value):
    if hasattr(value, "model_dump"):
        return json_value(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {k: json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    return value


def load_module(lesson):
    name = "course_" + lesson + "_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, UPSTREAM / lesson / "code.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RecordedMessages:
    def __init__(self, sdk, maximum=80):
        self.sdk, self.maximum = sdk, maximum
        self.calls = []
        self.lock = threading.Lock()
        self.messages = self
        self.ledger = None

    def _write_ledger(self, event):
        if self.ledger is not None:
            with self.ledger.open("a") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    @observe(name="integrated_model", type="llm")
    def create(self, **kwargs):
        request = json_value(kwargs)
        with self.lock:
            if len(self.calls) >= self.maximum:
                raise RuntimeError("Declared application/support request budget exhausted")
            row = {
                "request": copy.deepcopy(request),
                "thread": threading.current_thread().name,
                "started_at_monotonic": time.monotonic(),
                "response_received": False,
            }
            self.calls.append(row)
            index = len(self.calls) - 1
            self._write_ledger({"event": "request_started", "index": index, **row})
        try:
            result = self.sdk.messages.create(**request)
            with self.lock:
                row.update(response_received=True, response=json_value(result))
            update_current_span(input=request["messages"], output=row["response"])
            return result
        except Exception as error:
            with self.lock:
                row["error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        finally:
            with self.lock:
                row["ended_at_monotonic"] = time.monotonic()
                self._write_ledger({"event": "request_ended", "index": index, **row})


class Runtime:
    """One workspace per process; native resident threads end with that process."""

    def __init__(self, workspace, *, sdk=None, approved_commands=None, maximum_requests=80):
        self.workspace = Path(workspace).resolve(strict=True)
        if not self.workspace.is_dir():
            raise ValueError("Workspace must be an existing directory")
        self.audit, self.goal_events, self.history = [], [], []
        self.context = {}
        self.state = {"active_user_request": "(no active user request)"}
        previous_cwd = Path.cwd()
        keys = {
            k: os.environ.get(k)
            for k in (
                "ANTHROPIC_API_KEY",
                "ANTHROPIC_AUTH_TOKEN",
                "ANTHROPIC_BASE_URL",
                "MODEL_ID",
                "NO_PROXY",
                "no_proxy",
            )
        }
        try:
            os.chdir(self.workspace)
            os.environ.update(
                ANTHROPIC_API_KEY="course-local-transport",
                MODEL_ID="course-local-codex",
                NO_PROXY="*",
                no_proxy="*",
                ANTHROPIC_BASE_URL=os.environ.get(
                    "INTEGRATED_BRIDGE_URL", "http://host.docker.internal:8770"
                ),
            )
            self.host = load_module("s15_integrated_harness")
            actual = sdk or Anthropic(
                api_key="course-local-transport",
                max_retries=0,
                timeout=200,
                http_client=httpx.Client(trust_env=False),
                base_url=os.environ.get(
                    "INTEGRATED_BRIDGE_URL", "http://host.docker.internal:8770"
                ),
            )
        finally:
            os.chdir(previous_cwd)
            for key, value in keys.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        native = self.host.client
        memory_native = self.host.MEMORY_RUNTIME.client
        self.model = RecordedMessages(actual, maximum_requests)
        self.host.client = self.host.MEMORY_RUNTIME.client = self.model
        native.close()
        memory_native.close()
        self.workflow = load_module("s16_workflow_runtime")
        self.workflow.STORE = self.workspace / ".workflow_runtime"
        install_course_workflow(self.workflow, self.workspace)
        self.workflow.install_workflow_tool(self.host)
        goals = load_module("s17_goal_loop")
        self.goal = goals.GoalController(
            goals.PromptGoalEvaluator(self.model, self.host.MODEL),
            events=self.goal_events,
        )
        self._native_loop = self.host.agent_loop
        self.host.agent_loop = self._goal_loop
        self.approved_commands = approved_commands
        if approved_commands is not None:
            self.host.CONSOLE.reader = lambda prompt: "y"
        self.host.HOOKS["PreToolUse"].insert(0, self._batch_permission)
        self.host.HOOKS["PreToolUse"].insert(0, self._before_tool)
        self.host.HOOKS["PostToolUse"].append(self._after_tool)
        self.host.MOCK_SERVERS["docs"] = self._knowledge_server
        self.host.SKILLS_DIR = PROJECT / "integrated_agent/skills"
        self.host.scan_skills()
        self._services_started = False

    def _batch_permission(self, block):
        if self.approved_commands is None:
            return None
        reason = None
        if block.name == "bash" and block.input.get("command") not in self.approved_commands:
            reason = "Permission denied: command was not preapproved for this run"
        if (
            block.name.startswith("mcp__")
            and self.host.mcp_tool_policies.get(block.name, "confirm") != "allow"
        ):
            reason = "Permission denied: this run does not approve mutating MCP tools"
        if reason:
            self.audit.append({"phase": "batch_denied", "name": block.name, "reason": reason})
        return reason

    def _before_tool(self, block):
        self.audit.append(
            {
                "phase": "PreToolUse",
                "name": block.name,
                "id": block.id,
                "input": copy.deepcopy(block.input),
                "at_monotonic": time.monotonic(),
            }
        )

    def _after_tool(self, block, output):
        self.audit.append(
            {
                "phase": "PostToolUse",
                "name": block.name,
                "id": block.id,
                "output": str(output),
                "at_monotonic": time.monotonic(),
            }
        )

    def _knowledge_server(self):
        server = self.host.MCPClient("docs")
        server.register(
            [
                {
                    "name": "search",
                    "description": "Search actual read-only mounted project documents.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
                {
                    "name": "get_version",
                    "description": "Return actual mounted document hashes.",
                    "inputSchema": {"type": "object", "properties": {}},
                },
            ],
            {
                "search": lambda query: json.dumps(search(query), ensure_ascii=False),
                "get_version": lambda: json.dumps(
                    [{k: d[k] for k in ("path", "sha256")} for d in catalog()]
                ),
            },
        )
        return server

    def _background_running(self):
        with self.host.background_lock:
            return any(t["status"] == "running" for t in self.host.background_tasks.values())

    @observe(name="integrated_agent_turn", type="agent")
    def _goal_loop(self, messages, context, request):
        while True:
            self._native_loop(messages, context, request)
            decision = asyncio.run(
                self.goal.evaluate_after_turn(messages, self._background_running())
            )
            self.audit.append(
                {"phase": "goal_stop", "decision": decision.action, "reason": decision.reason}
            )
            if decision.action != "block":
                return
            messages.append({"role": "user", "content": "[Goal not complete] " + decision.reason})

    def start_services(self):
        if self._services_started:
            return
        self.host.start_runtime_services()
        threading.Thread(
            target=self.host.async_event_loop,
            args=(self.history, self.context, self.state),
            name="integrated-events",
            daemon=True,
        ).start()
        self._services_started = True

    def submit(self, query, goal=None):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("A nonempty task is required")
        with self.host.agent_lock:
            self.goal.begin_query()
            if goal is not None:
                self.goal.set_goal(goal)
            self.host.trigger_hooks("UserPromptSubmit", query)
            self.state["active_user_request"] = query
            self.history.append({"role": "user", "content": query})
            self.host.agent_loop(self.history, self.context, query)
        return self.snapshot()

    def snapshot(self):
        with self.model.lock:
            calls = copy.deepcopy(self.model.calls)
        with self.host.background_lock:
            backgrounds = copy.deepcopy(self.host.background_tasks)
        history = json_value(self.history)
        last = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
        final_text = (
            last
            if isinstance(last, str)
            else "\n".join(b.get("text", "") for b in last if b.get("type") == "text")
        )
        return json_value(
            {
                "workspace": str(self.workspace),
                "history": self.history,
                "final_text": final_text,
                "model_calls": calls,
                "audit": self.audit,
                "goal_events": self.goal_events,
                "goal_active": self.goal.active is not None,
                "goal_last_status": self.goal.last_status,
                "backgrounds": backgrounds,
                "tasks": [self.host.asdict(t) for t in self.host.list_tasks()],
                "active_teammates": dict(self.host.active_teammates),
                "schedules": [self.host.asdict(j) for j in self.host.scheduled_jobs.values()],
            }
        )

    def wait_until_settled(self, seconds):
        deadline = time.monotonic() + seconds
        while True:
            with self.host.agent_lock:
                with self.host.cron_lock:
                    scheduled = bool(self.host.cron_queue) or any(
                        not j.recurring for j in self.host.scheduled_jobs.values()
                    )
                with self.host.team_lock:
                    working = any(s != "idle" for s in self.host.active_teammates.values())
                pending = (
                    scheduled
                    or working
                    or self._background_running()
                    or self.host.has_pending_background()
                    or self.host.BUS.peek("lead")
                )
                if not pending:
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)

    def close(self):
        for name in list(self.host.active_teammates):
            self.host.run_request_shutdown(name)
        self.host._stop_all_shell_processes()
