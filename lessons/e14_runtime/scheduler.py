"""At-least-once scheduled prompt delivery, separate from execution completion.

Adapted from pinned Learn Claude Code s12. poll() uses its explicit datetime;
this module starts no runtime threads and cannot schedule while its process is off.
"""

import copy
import json
import re
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

from .cron import cron_matches, validate_cron


class Scheduler:
    def __init__(self, workspace):
        self.workspace = Path(workspace).resolve()
        self.path = self.workspace / ".scheduled_tasks.json"
        self.lock = threading.RLock()
        self.jobs, self.queue, self.events = {}, [], []
        self.check_path()
        if self.path.exists():
            payload = json.loads(self.path.read_text())
            if not isinstance(payload, list):
                raise ValueError("Saved schedule must be an array")
            for job in payload:
                self.validate(job)
                if job["id"] in self.jobs:
                    raise ValueError("Duplicate saved schedule")
                self.jobs[job["id"]] = job
                if job["pending_delivery"]:
                    self.queue.append(job["id"])

    def check_path(self):
        if self.path.is_symlink() or self.path.with_suffix(".tmp").is_symlink():
            raise ValueError("Schedule file cannot be a symlink")

    @staticmethod
    def validate(job):
        if (
            not isinstance(job, dict)
            or set(job)
            != {"id", "cron", "prompt", "recurring", "durable", "pending_delivery", "last_fired"}
            or not isinstance(job["id"], str)
            or not re.fullmatch(r"cron_[a-f0-9]{8}", job["id"])
            or not isinstance(job["cron"], str)
            or validate_cron(job["cron"])
            or not isinstance(job["prompt"], str)
            or not job["prompt"].strip()
            or any(type(job[k]) is not bool for k in ("recurring", "durable", "pending_delivery"))
            or not (job["last_fired"] is None or isinstance(job["last_fired"], str))
        ):
            raise ValueError("Invalid schedule definition or saved state")

    def persist(self):
        self.check_path()
        temporary = self.path.with_suffix(".tmp")
        payload = [j for j in self.jobs.values() if j["durable"]]
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(self.path)

    @contextmanager
    def transaction(self):
        with self.lock:
            before_jobs, before_queue = copy.deepcopy(self.jobs), list(self.queue)
            try:
                yield
                if self.jobs != before_jobs:
                    self.persist()
            except (OSError, ValueError):
                self.jobs, self.queue = before_jobs, before_queue
                raise

    def create(self, cron, prompt, recurring, durable):
        job = {
            "id": "cron_" + uuid.uuid4().hex[:8],
            "cron": cron,
            "prompt": prompt,
            "recurring": recurring,
            "durable": durable,
            "pending_delivery": False,
            "last_fired": None,
        }
        self.validate(job)
        with self.transaction():
            if len(self.jobs) >= 8 or job["id"] in self.jobs:
                raise ValueError("Eight-job budget exhausted or ID collision")
            self.jobs[job["id"]] = job
        self.events.append({"action": "registered", "job": copy.deepcopy(job)})
        return copy.deepcopy(job)

    def list(self):
        with self.lock:
            return copy.deepcopy(list(self.jobs.values()))

    def cancel(self, ident):
        with self.transaction():
            job = self.jobs.pop(ident)
            self.queue = [i for i in self.queue if i != ident]
        self.events.append({"action": "cancelled", "id": job["id"]})
        return {"id": ident, "cancelled": True}

    def poll(self, moment):
        marker = moment.isoformat(timespec="minutes")
        due = []
        with self.transaction():
            for job in self.jobs.values():
                if job["pending_delivery"] or job["last_fired"] == marker:
                    continue
                if cron_matches(job["cron"], moment):
                    job.update(pending_delivery=True, last_fired=marker)
                    self.queue.append(job["id"])
                    due.append(copy.deepcopy(job))
        self.events.extend({"action": "due", "job": job} for job in due)
        return due

    def take(self):
        with self.lock:
            jobs = [copy.deepcopy(self.jobs[i]) for i in self.queue]
            self.queue.clear()
            self.events.extend({"action": "offered_to_model", "job": j} for j in jobs)
            return jobs

    def restore(self, offered):
        with self.lock:
            for job in offered:
                if (
                    job["id"] in self.jobs
                    and self.jobs[job["id"]]["pending_delivery"]
                    and job["id"] not in self.queue
                ):
                    self.queue.append(job["id"])
            self.events.append(
                {"action": "model_request_failed_queue_restored", "ids": [j["id"] for j in offered]}
            )

    def acknowledge(self, offered):
        try:
            with self.transaction():
                for receipt in offered:
                    job = self.jobs.get(receipt["id"])
                    if job is None:
                        continue
                    if not job["pending_delivery"] or job["last_fired"] != receipt["last_fired"]:
                        raise ValueError("Stale schedule delivery receipt")
                    if job["recurring"]:
                        job["pending_delivery"] = False
                    else:
                        del self.jobs[job["id"]]
        except (OSError, ValueError):
            self.restore(offered)
            raise
        self.events.append(
            {"action": "model_received_not_task_completed", "ids": [j["id"] for j in offered]}
        )
