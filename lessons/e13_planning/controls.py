"""Instructor protocol controls: real state/file operations, zero model calls."""

import json
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .code import Runtime
from .tools import PlanningPool


def call(name, **args):
    return {"name": name, "arguments_json": json.dumps(args)}


def run():
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        (workspace / "shipping.py").write_text("base\n")
        runtime = Runtime(workspace)
        store = runtime.store
        core, entry = store.create("core"), store.create("entry")
        store.add_dependencies(entry["id"], [core["id"]])
        lead = PlanningPool(runtime)
        denied_dependency = lead.dispatch(call("task_claim", task_id=entry["id"]), workspace)
        cycle = lead.dispatch(
            call("task_dependencies", task_id=core["id"], blocked_by=[entry["id"]]),
            workspace,
        )
        claim_barrier = threading.Barrier(2)

        def claim(owner):
            claim_barrier.wait()
            try:
                return {"status": "claimed", "task": store.claim(core["id"], owner)}
            except ValueError as error:
                return {"status": "rejected", "error": str(error)}

        with ThreadPoolExecutor(max_workers=2) as workers:
            claims = list(workers.map(claim, ["worker-a", "worker-b"]))
        owner = store.load(core["id"])["owner"]
        wrong_owner = lead.dispatch(call("task_complete", task_id=core["id"]), workspace)
        store.complete(core["id"], owner)
        ready = store.claim(entry["id"], "lead")
        # Both roles receive the same initial file version before either edits it.
        edit_tasks = [store.create("edit a"), store.create("edit b")]
        pools = []
        for task, name in zip(edit_tasks, ("editor-a", "editor-b"), strict=True):
            store.claim(task["id"], name)
            pools.append(PlanningPool(runtime, name, task["id"], ["shipping.py"]))
        edit_barrier = threading.Barrier(2)

        def edit(index):
            edit_barrier.wait()
            return pools[index].dispatch(
                call("edit_file", path="shipping.py", old_text="base", new_text=f"edit-{index}"),
                workspace,
            )

        with ThreadPoolExecutor(max_workers=2) as workers:
            edits = list(workers.map(edit, (0, 1)))
        runtime.bus.send(owner, "lead", core["id"], "Instructor fixture summary", "completed_claim")
        first, second = runtime.bus.consume("lead"), runtime.bus.consume("lead")
        checks = {
            "dependency_claim_rejected": denied_dependency[1]["status"] == "error",
            "cycle_rejected": cycle[1]["status"] == "error",
            "one_concurrent_claim": sum(r["status"] == "claimed" for r in claims) == 1,
            "wrong_owner_rejected": wrong_owner[1]["status"] == "error",
            "dependency_unlocks_after_completion_claim": ready["status"] == "in_progress",
            "one_edit_applied_one_stale_denied": sorted(r[1]["status"] for r in edits)
            == ["denied", "ok"],
            "one_consumer_delivery": len(first) == 1 and second == [],
        }
        return {
            "origin": "instructor_protocol_fixture_with_real_file_operations",
            "model_requests": 0,
            "checks": checks,
            "passed": all(checks.values()),
            "dependency_attempt": denied_dependency,
            "cycle_attempt": cycle,
            "claims": claims,
            "wrong_owner": wrong_owner,
            "edits": edits,
            "actual_source": (workspace / "shipping.py").read_text(),
            "task_events": store.events,
            "mail_events": runtime.bus.events,
        }


def main():
    result = {"lesson": "e13", **run()}
    path = Path(os.environ.get("RUNS_DIR", "runs")) / "e13-controls.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "model_requests": 0}))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
