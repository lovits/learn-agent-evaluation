"""Timed tools add explicit background work and controlled cron to the prior pool."""

import copy
import json
from datetime import timedelta

from lessons.e02_tools_traces.code import permission
from lessons.e13_planning.tools import PLANNING, PlanningPool


def definition(name, description, properties):
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": {k: {"type": v} for k, v in properties.items()},
            "required": list(properties),
            "additionalProperties": False,
        },
    }


TIMED = [
    definition(
        "background_bash",
        "Explicitly start the declared read-only test command in the background. Returns a pending ID, not a test result. timeout_seconds is 0.01..10; results arrive as runtime data before a later model request.",
        {"command": "string", "timeout_seconds": "number"},
    ),
    definition(
        "background_wait",
        "Wait up to seconds (0..10) for an actual returned background ID. Its result is delivered as a separate runtime notification, not a second result for the original call.",
        {"id": "string", "seconds": "number"},
    ),
    definition(
        "schedule_cron",
        "Register a five-field cron prompt. This is a definition; model receipt and task completion are separate. The current lesson uses its explicitly controlled +08:00 clock.",
        {"cron": "string", "prompt": "string", "recurring": "boolean", "durable": "boolean"},
    ),
    definition("list_crons", "Read actual schedule definitions and pending delivery state.", {}),
    definition("cancel_cron", "Cancel the definition and its queued delivery.", {"id": "string"}),
    definition(
        "advance_clock",
        "Teaching experiment only: advance the controlled clock by integer seconds, 1..120 total for this run. Does not wait for wall time or simulate a completed command.",
        {"seconds": "integer"},
    ),
]


class TimedPool(PlanningPool):
    def assemble(self):
        graph_tools = {t["name"] for t in PLANNING if t["name"] != "todo_write"}
        relevant = [t for t in super().assemble() if t["name"] not in graph_tools]
        return relevant + (copy.deepcopy(TIMED) if self.actor == "lead" else [])

    def dispatch(self, call, workspace, approve=lambda n, a: False):
        name = call.get("name")
        if name not in {t["name"] for t in TIMED}:
            return super().dispatch(call, workspace, approve)
        if workspace.resolve() != self.runtime.workspace or self.actor != "lead":
            return self.denied("Timed tools require the lead's current workspace")
        try:
            args = json.loads(call["arguments_json"])
            spec = next(t for t in TIMED if t["name"] == name)
            properties = spec["input_schema"]["properties"]
            if not isinstance(args, dict) or set(args) != set(properties):
                raise ValueError("Missing or extra timed arguments")
            for key, rule in properties.items():
                expected = {
                    "string": (str,),
                    "number": (int, float),
                    "integer": (int,),
                    "boolean": (bool,),
                }[rule["type"]]
                if type(args[key]) not in expected:
                    raise TypeError("Invalid typed argument: " + key)
            background = self.runtime.backgrounds[self.actor]
            if name == "background_bash":
                decision, reason = permission(
                    "bash", {"command": args["command"]}, workspace, approve
                )
                if decision != "allow":
                    return self.denied(reason)
                if args["command"] != "python3 slow_tests.py":
                    return self.denied("This lesson permits only the declared regression command")
                result = background.start(args["command"], args["timeout_seconds"])
            elif name == "background_wait":
                result = background.wait(args["id"], args["seconds"])
            elif name == "schedule_cron":
                result = self.runtime.scheduler.create(**args)
            elif name == "list_crons":
                result = self.runtime.scheduler.list()
            elif name == "cancel_cron":
                result = self.runtime.scheduler.cancel(args["id"])
            else:
                seconds = args["seconds"]
                if not 1 <= seconds <= 120 or self.runtime.advanced_seconds + seconds > 120:
                    raise ValueError("Controlled clock budget is 1..120 seconds total")
                self.runtime.moment += timedelta(seconds=seconds)
                self.runtime.advanced_seconds += seconds
                result = {
                    "controlled_clock": self.runtime.moment.isoformat(),
                    "wall_time_waited": False,
                }
            return {"decision": "allow", "reason": "explicit_timed_tool"}, {
                "status": "ok",
                "output": json.dumps(result, ensure_ascii=False),
            }
        except (ValueError, TypeError, KeyError, OSError) as error:
            return {"decision": "not_executed", "reason": "timed_boundary_error"}, {
                "status": "error",
                "output": f"{type(error).__name__}: {error}",
            }
