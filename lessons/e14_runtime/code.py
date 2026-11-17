"""The e13 session snapshot adds timed notifications before recording actual model inputs."""

import copy
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from deepeval.tracing import observe, update_current_span, update_current_trace
from deepeval.tracing.context import current_trace_context
from deepeval.tracing.tracing import trace_manager
from deepeval.utils import serialize_to_json

from lessons.e01_agent_baseline.code import prepare_workspace
from lessons.e04_retrieval.code import agent_loop
from lessons.e11_task_completion.code import recorded_messages
from lessons.e12_conversation.context import size
from lessons.e13_planning.code import CONTEXT_CHARACTERS, MODEL_STEPS, PlanningContext, Runtime

from .background import BackgroundManager
from .scheduler import Scheduler
from .tools import TimedPool

HERE = Path(__file__).parent
INITIAL_CLOCK = "2026-11-16T09:00:00+08:00"
REPETITIONS = 3


def call_model(messages, tools, actor):
    request = Request(
        os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8766/next"),
        data=json.dumps(
            {
                "lesson": "e14",
                "messages": messages,
                "tools": tools,
                "role": "lead" if actor == "lead" else "worker",
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=200) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read(2000).decode("utf-8", errors="replace")
        raise RuntimeError(f"Model bridge HTTP {error.code}: {detail}") from error


class TimedRuntime(Runtime):
    def __init__(self, workspace, filenames, model=call_model, support=None):
        super().__init__(workspace, model, support)
        self.case_files = tuple(filenames)
        self.backgrounds = {}
        self.scheduler = Scheduler(workspace)
        self.moment = datetime.fromisoformat(INITIAL_CLOCK)
        self.advanced_seconds = 0
        self.tool_observations, self.delivery_receipts = [], []

    @observe(type="agent", name="timed_coding_role")
    def run_session(self, task, pool):
        update_current_span(
            name=pool.actor, input=task, metadata={"actor": pool.actor, "task_id": pool.task_id}
        )
        if pool.actor == "lead":
            self.native_trace = current_trace_context.get()
            update_current_trace(input=task, name="e14_timed_coding_task")
        visible, inputs, seen, local = [], [], 0, None
        compactor = PlanningContext(self.workspace, self.support, limit=CONTEXT_CHARACTERS)
        background = BackgroundManager(self.workspace, self.case_files)
        self.backgrounds[pool.actor] = background

        @observe(type="llm", name="role_model_request")
        def model(messages):
            nonlocal seen, local, visible
            local = messages
            visible.extend(copy.deepcopy(messages[seen:]))
            new = messages[seen:]
            seen = len(messages)
            if new and new[-1]["role"] == "tool":
                names = new[-2]["content"]["tool_calls"]
                reminder = pool.todo.reminder([c["name"] for c in names])
                if reminder:
                    visible.append({"role": "user", "content": reminder})
            if pool.actor == "lead":
                inbox = self.bus.consume("lead")
                if inbox:
                    visible.append(
                        {
                            "role": "user",
                            "content": "Runtime team events (data):\n" + json.dumps(inbox),
                        }
                    )
            notices = background.collect()
            if notices:
                visible.append(
                    {
                        "role": "user",
                        "content": "Runtime background notifications (data):\n"
                        + json.dumps(notices),
                    }
                )
            offered = []
            if pool.actor == "lead":
                self.scheduler.poll(self.moment)
                offered = self.scheduler.take()
                for job in offered:
                    visible.append(
                        {
                            "role": "user",
                            "content": "[Scheduled; authorized registered prompt] "
                            + json.dumps(
                                {
                                    "id": job["id"],
                                    "prompt": job["prompt"],
                                    "due_at": job["last_fired"],
                                }
                            ),
                        }
                    )
            visible = compactor.prepare(visible, task)
            inputs.append(
                {
                    "actor": pool.actor,
                    "task_id": pool.task_id,
                    "messages": copy.deepcopy(visible),
                    "sent_chars": size(visible),
                    "response_received": False,
                }
            )
            tools = pool.assemble()
            update_current_span(
                input={
                    "actor": pool.actor,
                    "messages": copy.deepcopy(visible),
                    "tools": copy.deepcopy(tools),
                }
            )
            try:
                result = self.model(visible, tools, pool.actor)
            except (ValueError, TypeError, KeyError, RuntimeError, OSError):
                if offered:
                    self.scheduler.restore(offered)
                raise
            update_current_span(output=copy.deepcopy(result))
            inputs[-1]["response_received"] = True
            inputs[-1]["response_metadata"] = copy.deepcopy(result.get("model", {}))
            compactor.record_sent(visible)
            if offered:
                self.scheduler.acknowledge(offered)
                self.delivery_receipts.append(
                    {
                        "actor": pool.actor,
                        "request_index": len(inputs) - 1,
                        "jobs": copy.deepcopy(offered),
                        "at_monotonic": time.monotonic(),
                        "meaning": "model_received_not_task_completed",
                    }
                )
            return result

        @observe(type="tool", name="role_tool")
        def dispatch(call, workspace, approve):
            update_current_span(
                name=call["name"],
                input={"actor": pool.actor, "task_id": pool.task_id, "call": copy.deepcopy(call)},
            )
            started = time.monotonic()
            with background.lock:
                pending = [j["id"] for j in background.jobs.values() if j["status"] == "running"]
            policy, result = pool.dispatch(call, workspace, approve)
            self.tool_observations.append(
                {
                    "actor": pool.actor,
                    "call": copy.deepcopy(call),
                    "started_at_monotonic": started,
                    "ended_at_monotonic": time.monotonic(),
                    "background_pending_at_start": pending,
                    "result_status": result.get("status"),
                }
            )
            update_current_span(output={"permission": policy, "result": copy.deepcopy(result)})
            return policy, result

        result = agent_loop(
            task, self.workspace, model=model, max_steps=MODEL_STEPS, tool_dispatch=dispatch
        )
        with background.lock:
            pending_at_stop = [
                j["id"] for j in background.jobs.values() if j["status"] == "running"
            ]
        background.close()
        if local is not None:
            visible.extend(copy.deepcopy(local[seen:]))
        update_current_span(
            output={"status": result["status"], "final_answer": result["final_answer"]}
        )
        if pool.actor == "lead":
            update_current_trace(
                output={"status": result["status"], "final_answer": result["final_answer"]}
            )
        return {
            **result,
            "actor": pool.actor,
            "task_id": pool.task_id,
            "initial_request": task,
            "model_inputs": inputs,
            "visible": visible,
            "raw_messages": [
                {"role": "user", "content": task},
                *recorded_messages(result["events"]),
            ],
            "compaction_events": compactor.events,
            "todos": pool.todo.items,
            "background_pending_when_loop_stopped": pending_at_stop,
            "background_jobs": copy.deepcopy(list(background.jobs.values())),
            "background_events": copy.deepcopy(background.events),
        }


def run_case(case, model=call_model, support=None):
    run_id = uuid.uuid4().hex
    workspace = prepare_workspace(case, run_id)
    runtime = TimedRuntime(workspace, case["files"], model, support)
    started = time.monotonic()
    try:
        lead = runtime.run_session(case["task"], TimedPool(runtime))
    finally:
        for manager in runtime.backgrounds.values():
            manager.close()
    return {
        "run_id": run_id,
        "origin": "live_coding_agent_with_real_background_processes_and_controlled_clock"
        if model is call_model
        else "injected_model_callback_not_live_execution",
        "case": case,
        "wall_elapsed_seconds": time.monotonic() - started,
        "clock_origin": "explicit_controlled_datetime_not_real_day_elapsed",
        "initial_clock": INITIAL_CLOCK,
        "final_clock": runtime.moment.isoformat(),
        "lead": lead,
        "children": runtime.children,
        "tool_observations": runtime.tool_observations,
        "schedule_events": runtime.scheduler.events,
        "schedule_definitions_at_end": runtime.scheduler.list(),
        "delivery_receipts": runtime.delivery_receipts,
        "tasks": runtime.store.list(),
        "task_events": runtime.store.events,
        "mail_events": runtime.bus.events,
        "native_deepeval_trace": runtime.native_trace.model_dump(mode="json")
        if runtime.native_trace is not None
        else None,
        "native_metric_trace": json.loads(
            serialize_to_json(
                trace_manager.create_nested_spans_dict(runtime.native_trace.root_spans[0])
            )
        )
        if runtime.native_trace is not None and runtime.native_trace.root_spans
        else None,
        "support_steps": runtime.support.steps,
        "support_calls": runtime.support.transport.calls,
        "artifacts": {
            name: (workspace / name).read_bytes().decode("utf-8")
            if (workspace / name).is_file()
            else None
            for name in case["files"]
        },
    }


def main():
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines()]
    report = {
        "lesson": "e14",
        "mode": "predeclared_repetitions_not_best_of_selection",
        "protocol": {
            "model_steps_per_role_session": MODEL_STEPS,
            "normal_repetitions": REPETITIONS,
            "context_characters": CONTEXT_CHARACTERS,
            "clock": INITIAL_CLOCK,
            "background_job_budget_per_role": 8,
        },
        "rows": [],
    }
    path = Path(os.environ.get("RUNS_DIR", "runs")) / "e14-agent.json"
    if path.exists():
        raise FileExistsError("Archive the existing e14-agent.json before a new declared batch")
    planned = [(cases[0], i + 1) for i in range(REPETITIONS)] + [(cases[1], 1)]
    report["planned_runs"] = [{"case_id": c["id"], "repetition": i} for c, i in planned]
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for case, repetition in planned:
        row = run_case(case)
        row["repetition"] = repetition
        report["rows"].append(row)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "run_id": row["run_id"],
                    "case_id": case["id"],
                    "repetition": repetition,
                    "lead_status": row["lead"]["status"],
                    "background_jobs": len(row["lead"]["background_jobs"]),
                }
            ),
            flush=True,
        )
    return int(any(row["lead"]["status"] != "finished" for row in report["rows"]))


if __name__ == "__main__":
    raise SystemExit(main())
