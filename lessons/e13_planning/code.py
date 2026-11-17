"""One lead loop delegates focused tasks; only runtime mail events return summaries."""

import copy
import json
import os
import uuid
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
from lessons.e12_conversation.context import ContextCompactor, SupportModel, size

from .state import MessageBus, TaskStore
from .tools import PlanningPool

HERE = Path(__file__).parent
MODEL_STEPS = 20
CONTEXT_CHARACTERS = 30000
SNIP_TRIGGER_MESSAGES = 50


class PlanningContext(ContextCompactor):
    def snip(self, messages):
        if len(messages) < SNIP_TRIGGER_MESSAGES:
            return messages
        return super().snip(messages)


def call_model(messages, tools, actor):
    request = Request(
        os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8766/next"),
        data=json.dumps(
            {
                "lesson": "e13",
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


class Runtime:
    def __init__(self, workspace, model=call_model, support=None):
        self.workspace, self.model = Path(workspace).resolve(), model
        self.support = support or SupportModel()
        self.store, self.bus = TaskStore(self.workspace), MessageBus(self.workspace)
        self.children = []
        self.native_trace = None
        self.public_reviews = []

    @observe(type="agent", name="coding_role")
    def run_session(self, task, pool):
        update_current_span(
            name=pool.actor, input=task, metadata={"actor": pool.actor, "task_id": pool.task_id}
        )
        if pool.actor == "lead":
            self.native_trace = current_trace_context.get()
            update_current_trace(input=task, name="e13_planned_coding_task")
        visible, inputs, seen, local = [], [], 0, None
        compactor = PlanningContext(self.workspace, self.support, limit=CONTEXT_CHARACTERS)

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
            result = self.model(visible, tools, pool.actor)
            update_current_span(output=copy.deepcopy(result))
            inputs[-1]["response_received"] = True
            compactor.record_sent(visible)
            return result

        @observe(type="tool", name="role_tool")
        def dispatch(call, workspace, approve):
            update_current_span(
                name=call["name"],
                input={"actor": pool.actor, "task_id": pool.task_id, "call": copy.deepcopy(call)},
            )
            policy, result = pool.dispatch(call, workspace, approve)
            update_current_span(output={"permission": policy, "result": copy.deepcopy(result)})
            return policy, result

        result = agent_loop(
            task, self.workspace, model=model, max_steps=MODEL_STEPS, tool_dispatch=dispatch
        )
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
        }

    def run_child(self, task_id, prompt, files):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Delegated prompt cannot be empty")
        if (
            not isinstance(files, list)
            or not files
            or not all(isinstance(f, str) and f in {"shipping.py", "checkout.py"} for f in files)
        ):
            raise ValueError("Assign declared implementation filenames")
        task = self.store.load(task_id)
        if task["status"] == "pending":
            owner = "worker-" + str(len(self.children) + 1)
            task = self.store.claim(task_id, owner)
        elif task["status"] == "in_progress" and task["owner"].startswith("worker-"):
            owner = task["owner"]
        else:
            raise ValueError("Task cannot be delegated in its current state")
        context = (
            f"You are {owner}, assigned task {task_id}. You have a fresh conversation, not the lead's history. "
            f"Description: {task['description']}\nDelegated request:\n{prompt}\n"
            f"Only edit {json.dumps(files)} using file tools. Other files are readable. "
            "Completion is scoped to this task and assigned files. Other dependent components can still fail; report that instead of editing unassigned files. Submit task_complete to run this component's public stop review, including protected-test checks. If accepted, return the scoped result and remaining integration limits; do not repeatedly rerun unchanged passing tests or claim the whole project is complete."
        )
        pool = PlanningPool(self, owner, task_id, files)
        before = copy.deepcopy(task)
        result = self.run_session(context, pool)
        task = self.store.load(task_id)
        status = (
            "completed_claim"
            if result["status"] == "finished" and task["status"] == "completed"
            else "incomplete"
        )
        self.children.append(
            {
                "delegated_prompt": prompt,
                "assigned_files": files,
                "task_before": before,
                "task_after": task,
                "result": result,
            }
        )
        self.bus.send(owner, "lead", task_id, result["final_answer"], status)
        return {
            "task_id": task_id,
            "worker": owner,
            "status": status,
            "result_delivery": "runtime_lead_mailbox_next_model_request",
        }


def run_case(case, model=call_model, support=None):
    run_id = uuid.uuid4().hex
    workspace = prepare_workspace(case, run_id)
    runtime = Runtime(workspace, model, support)
    lead = runtime.run_session(case["task"], PlanningPool(runtime))
    return {
        "run_id": run_id,
        "origin": "live_lead_with_live_one_shot_subagents"
        if model is call_model
        else "injected_model_callback_not_a_claim_of_live_execution",
        "lead": lead,
        "children": runtime.children,
        "tasks": runtime.store.list(),
        "task_events": runtime.store.events,
        "scoped_public_reviews": runtime.public_reviews,
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
            name: (workspace / name).read_text() if (workspace / name).is_file() else None
            for name in case["files"]
        },
    }


def main():
    case = json.loads((HERE / "cases.jsonl").read_text())
    result = {
        "lesson": "e13",
        "case": case,
        "row": run_case(case),
        "protocol": {
            "model_steps_per_role_session": MODEL_STEPS,
            "context_character_budget": CONTEXT_CHARACTERS,
            "snip_trigger_messages": SNIP_TRIGGER_MESSAGES,
            "argument_protocol": "typed wire arguments; planning arrays; normalize once for the prior loop",
            "subagent_context": "fresh_one_shot",
            "workspace": "shared_with_role_file_guards",
        },
    }
    path = Path(os.environ.get("RUNS_DIR", "runs")) / "e13-agent.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    row = result["row"]
    print(
        json.dumps(
            {
                "run_id": row["run_id"],
                "lead_status": row["lead"]["status"],
                "children": len(row["children"]),
                "task_states": [t["status"] for t in row["tasks"]],
            }
        )
    )
    return int(row["lead"]["status"] != "finished" or not row["children"])


if __name__ == "__main__":
    raise SystemExit(main())
