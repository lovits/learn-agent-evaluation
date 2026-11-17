"""Planning tools reuse prior file permissions and keep child capabilities explicit."""

import hashlib
import json

from lessons.e10_tool_evaluation.mcp_tools import definition
from lessons.e12_conversation.tools import PagedToolPool

from .state import TodoManager

PLANNING = [
    definition(
        "todo_write",
        ["todos"],
        "Replace explicit todo list. todos is a JSON array string of content/status objects; at most one in_progress.",
    ),
    definition(
        "task_create",
        ["subject", "description"],
        "Create a persistent pending task; returns its actual task_id.",
    ),
    definition(
        "task_dependencies",
        ["task_id", "blocked_by"],
        "Lead only: add dependencies using existing IDs. blocked_by is a JSON array string.",
    ),
    definition("task_list", [], "Read current tasks, dependencies, states and owners."),
    definition("task_claim", ["task_id"], "Claim one ready task as the current role."),
    definition(
        "task_complete",
        ["task_id"],
        "Submit your active task for a scoped public component review, then record its completion claim. Other dependent components may still fail; whole-project holdouts remain separate.",
    ),
    definition(
        "task",
        ["task_id", "prompt", "files"],
        "Lead only: run a one-shot subagent with fresh context for a ready task. files is a JSON array string of permitted implementation paths. Its result arrives through runtime events.",
    ),
]
for spec in PLANNING:
    array_field = {"todo_write": "todos", "task_dependencies": "blocked_by", "task": "files"}.get(
        spec["name"]
    )
    if array_field:
        item = {"type": "string"}
        if array_field == "todos":
            item = {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "content": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                },
                "required": ["content", "status"],
            }
        spec["input_schema"]["properties"][array_field] = {"type": "array", "items": item}
        spec["description"] = spec["description"].replace("JSON array string", "JSON array")
CHILD_TEST_COMMANDS = {
    "python3 -m unittest -v",
    "python3 -m unittest -v test_shipping",
    "python3 -m unittest -v test_checkout",
    "python3 -m unittest -v test_shipping test_checkout",
    "python3 -m unittest -v test_checkout test_shipping",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


class PlanningPool(PagedToolPool):
    def __init__(self, runtime, actor="lead", task_id=None, files=None):
        super().__init__()
        self.runtime, self.actor, self.task_id = runtime, actor, task_id
        self.todo = TodoManager()
        self.files = files
        self.expected = {name: digest(runtime.workspace / name) for name in (files or [])}

    def assemble(self):
        extra = (
            PLANNING
            if self.actor == "lead"
            else [t for t in PLANNING if t["name"] in {"todo_write", "task_list", "task_complete"}]
        )
        tools = super().assemble() + extra
        if self.actor != "lead":
            next(t for t in tools if t["name"] == "bash")["description"] = (
                "Worker Bash permits only python3 -m unittest -v, optionally followed by "
                "test_shipping or test_checkout. Other commands are denied; use file tools to edit."
            )
        return tools

    def dispatch(self, call, workspace, approve=lambda n, a: False):
        if workspace.resolve() != self.runtime.workspace:
            return self.denied("Role workspace mismatch")
        workspace = self.runtime.workspace
        name = call.get("name")
        try:
            if name not in {t["name"] for t in self.assemble()}:
                return self.denied("Tool not available to this role")
            args = json.loads(call["arguments_json"])
            if not isinstance(args, dict):
                raise TypeError("Tool arguments must be a JSON object")
            if name in {t["name"] for t in PLANNING}:
                spec = next(t for t in PLANNING if t["name"] == name)
                if set(args) != set(spec["input_schema"]["required"]):
                    raise ValueError("Missing or extra planning arguments")
                value = self.planning(name, args)
                return {"decision": "allow", "reason": "role_scoped_planning"}, {
                    "status": "ok",
                    "output": json.dumps(value, ensure_ascii=False),
                }
            if not all(isinstance(v, str) for v in args.values()):
                raise ValueError("Base file/test tool arguments must be strings")
            if (
                self.actor != "lead"
                and name == "bash"
                and args.get("command") not in CHILD_TEST_COMMANDS
            ):
                return self.denied("Worker command is outside its declared test commands")
            if name in {"write_file", "edit_file"}:
                path = (workspace / args["path"]).resolve()
                if not path.is_relative_to(workspace.resolve()):
                    return self.denied("Outside workspace")
                relative = str(path.relative_to(workspace.resolve()))
                if relative not in {"shipping.py", "checkout.py"}:
                    return self.denied("Only declared implementation files may change")
                if self.files is not None and relative not in self.files:
                    return self.denied("File not assigned to this subagent")
                with self.runtime.store.lock:
                    if self.task_id is not None:
                        assigned = self.runtime.store.load(self.task_id)
                        if assigned["status"] != "in_progress" or assigned["owner"] != self.actor:
                            return self.denied(
                                "Only the active task owner may modify assigned files"
                            )
                    if self.files is not None and digest(path) != self.expected[relative]:
                        return self.denied(
                            "Stale file: reassign after reviewing the concurrent change"
                        )
                    policy, result = super().dispatch(call, workspace, approve)
                    if self.files is not None and result["status"] == "ok":
                        self.expected[relative] = digest(path)
                    return policy, result
            return super().dispatch(call, workspace, approve)
        except (ValueError, TypeError, KeyError, OSError) as error:
            return {"decision": "not_executed", "reason": "planning_boundary_error"}, {
                "status": "error",
                "output": f"{type(error).__name__}: {error}",
            }

    @staticmethod
    def denied(reason):
        return {"decision": "deny", "reason": reason}, {"status": "denied", "output": reason}

    def planning(self, name, args):
        store = self.runtime.store
        if name == "todo_write":
            return self.todo.update(args["todos"])
        if name == "task_create":
            return store.create(args["subject"], args["description"])
        if name == "task_dependencies":
            return store.add_dependencies(args["task_id"], args["blocked_by"])
        if name == "task_list":
            return store.list()
        if name == "task_claim":
            return store.claim(args["task_id"], self.actor)
        if name == "task_complete":
            if self.task_id is not None and args["task_id"] != self.task_id:
                raise ValueError("Worker can complete only its assigned task")
            if self.task_id is not None:
                from .verify import scoped_public_review

                current = store.load(self.task_id)
                if current["owner"] != self.actor or current["status"] != "in_progress":
                    raise ValueError("Only the active owner may submit this component")
                review = scoped_public_review(self.runtime.workspace, self.files)
                self.runtime.public_reviews.append(
                    {"actor": self.actor, "task_id": self.task_id, **review}
                )
                if review["passed"] is not True:
                    raise ValueError("Scoped public component review failed: " + json.dumps(review))
                return {
                    **store.complete(self.task_id, self.actor),
                    "scoped_public_review": {
                        "passed": True,
                        "public_cases_per_api": review["public_cases_per_api"],
                        "whole_project_assessment": "not_assessed",
                        "artifact_hashes": review["artifact_hashes"],
                        "original_test_hashes": review["original_test_hashes"],
                    },
                }
            return store.complete(args["task_id"], self.actor)
        return self.runtime.run_child(args["task_id"], args["prompt"], args["files"])
