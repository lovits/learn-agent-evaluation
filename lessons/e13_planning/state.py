"""Explicit plans, dependency transitions, and one-consumer file mailboxes."""

import copy
import json
import re
import threading
import uuid
from pathlib import Path

STATES = {"pending", "in_progress", "completed"}


class TodoManager:
    def __init__(self):
        self.items = []
        self.rounds_without_update = 0

    def update(self, items):
        if not isinstance(items, list) or not 1 <= len(items) <= 20:
            raise ValueError("A plan must contain 1..20 items")
        for item in items:
            if (
                not isinstance(item, dict)
                or set(item) != {"content", "status"}
                or not isinstance(item["content"], str)
                or not item["content"].strip()
                or not isinstance(item["status"], str)
                or item["status"] not in STATES
            ):
                raise ValueError("Each item needs nonempty content and a valid status")
        if sum(i["status"] == "in_progress" for i in items) > 1:
            raise ValueError("Only one todo may be in_progress")
        self.items = copy.deepcopy(items)
        self.rounds_without_update = 0
        return self.items

    def reminder(self, tool_names):
        self.rounds_without_update = (
            0 if "todo_write" in tool_names else self.rounds_without_update + 1
        )
        if self.rounds_without_update < 3:
            return None
        self.rounds_without_update = 0
        return "Plan reminder: update your explicit todos using actual progress."


class TaskStore:
    def __init__(self, workspace):
        self.workspace = Path(workspace).resolve()
        self.root = self.workspace / ".tasks"
        if self.root.is_symlink():
            raise ValueError("Task directory cannot be a symlink")
        self.root.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.events = []

    def path(self, task_id):
        if self.root.is_symlink() or self.root.resolve().parent != self.workspace:
            raise ValueError("Task directory escapes workspace")
        if not isinstance(task_id, str) or not re.fullmatch(r"task_[a-f0-9]{8}", task_id):
            raise ValueError("Invalid task ID")
        path = self.root / (task_id + ".json")
        if path.is_symlink():
            raise ValueError("Task record cannot be a symlink")
        return path

    def load(self, task_id):
        task = json.loads(self.path(task_id).read_text())
        if (
            task["id"] != task_id
            or not isinstance(task["status"], str)
            or task["status"] not in STATES
            or not isinstance(task["blocked_by"], list)
            or not all(isinstance(d, str) for d in task["blocked_by"])
            or (task["status"] != "pending" and not isinstance(task["owner"], str))
        ):
            raise ValueError("Invalid persisted task")
        return task

    def list(self):
        with self.lock:
            return [self.load(p.stem) for p in sorted(self.root.glob("task_*.json"))]

    def save(self, task, action, actor):
        path = self.path(task["id"])
        temporary = path.with_suffix(".tmp")
        if temporary.is_symlink():
            raise ValueError("Temporary task record cannot be a symlink")
        temporary.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(path)
        self.events.append(
            {
                "sequence": len(self.events),
                "action": action,
                "actor": actor,
                "task": copy.deepcopy(task),
            }
        )
        return copy.deepcopy(task)

    def create(self, subject, description=""):
        if not isinstance(subject, str) or not subject.strip() or not isinstance(description, str):
            raise ValueError(
                "Task subject and description must be strings; subject cannot be blank"
            )
        with self.lock:
            task = {
                "id": "task_" + uuid.uuid4().hex[:8],
                "subject": subject,
                "description": description,
                "status": "pending",
                "owner": None,
                "blocked_by": [],
            }
            if self.path(task["id"]).exists():
                raise FileExistsError("Task ID collision")
            return self.save(task, "create", "lead")

    def add_dependencies(self, task_id, dependencies):
        with self.lock:
            task = self.load(task_id)
            if task["status"] != "pending" or task["owner"] is not None:
                raise ValueError("Only an unowned pending task can change dependencies")
            if not isinstance(dependencies, list) or not all(
                isinstance(d, str) for d in dependencies
            ):
                raise ValueError("Dependencies must be a list of task IDs")
            for dependency in dependencies:
                pending, seen = [dependency], set()
                while pending:
                    current = pending.pop()
                    if current == task_id:
                        raise ValueError("Dependency cycle")
                    if current not in seen:
                        seen.add(current)
                        pending.extend(self.load(current)["blocked_by"])
            task["blocked_by"] = list(dict.fromkeys([*task["blocked_by"], *dependencies]))
            return self.save(task, "add_dependencies", "lead")

    def claim(self, task_id, owner):
        if not isinstance(owner, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", owner):
            raise ValueError("Invalid owner")
        with self.lock:
            task = self.load(task_id)
            if task["status"] != "pending" or task["owner"] is not None:
                raise ValueError("Task is already claimed or completed")
            if any(t["owner"] == owner and t["status"] == "in_progress" for t in self.list()):
                raise ValueError("Owner already has an active task")
            if any(self.load(d)["status"] != "completed" for d in task["blocked_by"]):
                raise ValueError("Dependencies are incomplete")
            task.update(owner=owner, status="in_progress")
            return self.save(task, "claim", owner)

    def complete(self, task_id, owner):
        with self.lock:
            task = self.load(task_id)
            if task["status"] != "in_progress" or task["owner"] != owner:
                raise ValueError("Only the active owner may complete a task")
            task["status"] = "completed"
            return self.save(task, "complete_claim", owner)


class MessageBus:
    def __init__(self, workspace):
        self.workspace = Path(workspace).resolve()
        self.root = self.workspace / ".mailboxes"
        if self.root.is_symlink():
            raise ValueError("Mailbox directory cannot be a symlink")
        self.root.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.events = []

    def path(self, name):
        if self.root.is_symlink() or self.root.resolve().parent != self.workspace:
            raise ValueError("Mailbox directory escapes workspace")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", name):
            raise ValueError("Invalid mailbox name")
        path = self.root / (name + ".jsonl")
        if path.is_symlink():
            raise ValueError("Mailbox cannot be a symlink")
        return path

    def send(self, sender, recipient, task_id, content, status):
        with self.lock:
            self.path(sender)
            row = {
                "sender": sender,
                "recipient": recipient,
                "task_id": task_id,
                "content": content,
                "status": status,
            }
            with self.path(recipient).open("a") as file:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.events.append(copy.deepcopy(row))
            return row

    def consume(self, recipient):
        with self.lock:
            path = self.path(recipient)
            if not path.exists():
                return []
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            path.unlink()
            return rows
