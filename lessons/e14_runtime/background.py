"""Explicit background Bash with one notification and retained execution receipts.

Adapted from pinned Learn Claude Code s11. Linux/POSIX teaching runtime;
permissions are checked by the tool dispatcher before start(), not by this manager.
"""

import copy
import hashlib
import json
import os
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path


def file_hashes(workspace, names):
    return {
        name: hashlib.sha256((workspace / name).read_bytes()).hexdigest()
        if (workspace / name).is_file()
        else None
        for name in names
    }


def stop_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


class BackgroundManager:
    def __init__(self, workspace, filenames):
        self.workspace = Path(workspace).resolve()
        self.filenames = tuple(filenames)
        self.root = self.workspace / ".background"
        if self.root.is_symlink():
            raise ValueError("Background directory cannot be a symlink")
        self.root.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.jobs, self.processes, self.threads, self.ready = {}, {}, {}, []
        self.events = []
        self.closed = False

    def save(self, job):
        if self.root.is_symlink() or self.root.resolve().parent != self.workspace:
            raise ValueError("Background directory escapes workspace")
        path = self.root / (job["id"] + ".json")
        temporary = path.with_suffix(".tmp")
        if path.is_symlink() or temporary.is_symlink():
            raise ValueError("Background record cannot be a symlink")
        temporary.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(path)

    def start(self, command, timeout):
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Background command cannot be empty")
        if type(timeout) not in (int, float) or not 0.01 <= timeout <= 10:
            raise ValueError("Timeout must be 0.01..10 seconds")
        with self.lock:
            if self.closed or len(self.jobs) >= 8:
                raise ValueError("Background manager closed or eight-job budget exhausted")
            ident = "bg_" + uuid.uuid4().hex[:8]
            job = {
                "id": ident,
                "command": command,
                "timeout_seconds": timeout,
                "status": "running",
                "started_at_monotonic": time.monotonic(),
                "initial_hashes": file_hashes(self.workspace, self.filenames),
                "notified": False,
            }
            self.save(job)
            self.jobs[ident] = job
            thread = threading.Thread(target=self.execute, args=(ident,), daemon=True)
            self.threads[ident] = thread
            try:
                thread.start()
            except RuntimeError:
                self.jobs.pop(ident)
                self.threads.pop(ident)
                (self.root / (ident + ".json")).unlink()
                raise
            self.events.append({"action": "start", "id": ident, "at": time.monotonic()})
            return {"id": ident, "status": "running", "result_pending": True}

    def execute(self, ident):
        process = None
        try:
            with self.lock:
                job = self.jobs[ident]
                if self.closed:
                    raise RuntimeError("Manager closed before process launch")
                process = subprocess.Popen(
                    job["command"],
                    shell=True,
                    executable="/bin/bash",
                    cwd=self.workspace,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                    start_new_session=True,
                )
                self.processes[ident] = process
            try:
                stdout, stderr = process.communicate(timeout=job["timeout_seconds"])
                status = "completed" if process.returncode == 0 else "error"
            except subprocess.TimeoutExpired:
                stop_group(process)
                stdout, stderr = process.communicate()
                status = "timeout"
            result = {
                "status": status,
                "exit_code": process.returncode,
                "stdout": stdout[:50000],
                "stderr": stderr[:50000],
                "output_truncated": len(stdout) > 50000 or len(stderr) > 50000,
            }
        except (OSError, RuntimeError) as error:
            result = {"status": "error", "exit_code": None, "error": str(error)}
        finally:
            if process is not None:
                stop_group(process)
                process.wait(timeout=1)
        with self.lock:
            self.processes.pop(ident, None)
            end = time.monotonic()
            job = self.jobs[ident]
            job.update(
                result=result,
                status=result["status"],
                ended_at_monotonic=end,
                elapsed_seconds=end - job["started_at_monotonic"],
                final_hashes=file_hashes(self.workspace, self.filenames),
            )
            self.save(job)
            self.ready.append(ident)
            self.events.append({"action": "ended", "id": ident, "at": end})

    def wait(self, ident, seconds):
        if type(seconds) not in (int, float) or not 0 <= seconds <= 10:
            raise ValueError("Wait must be 0..10 seconds")
        with self.lock:
            thread = self.threads[ident]
        thread.join(seconds)
        with self.lock:
            job = self.jobs[ident]
            return {"id": ident, "status": job["status"], "result_delivery": "next_model_request"}

    def collect(self):
        with self.lock:
            notifications = []
            for ident in self.ready:
                job = self.jobs[ident]
                job["notified"] = True
                self.save(job)
                notifications.append(copy.deepcopy(job))
                self.events.append({"action": "notified", "id": ident, "at": time.monotonic()})
            self.ready.clear()
            return notifications

    def close(self):
        with self.lock:
            self.closed = True
            for process in self.processes.values():
                stop_group(process)
            threads = list(self.threads.values())
        for thread in threads:
            thread.join(2)
            if thread.is_alive():
                raise RuntimeError("Background worker did not terminate")
