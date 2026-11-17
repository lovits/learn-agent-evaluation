"""Declared teaching orchestration around one native integrated Agent workspace.

The instructor chooses phases, approves a peer plan and commits its review.
All model replies, tool execution, queues and journals are native runtime work.
This is an integration experiment, not a claim that the model invented the plan.
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import threading
import time
from pathlib import Path

from .runtime import Runtime
from .traces import capture_native_traces

CASE = Path(__file__).parent / "cases/foundation.json"
COMMAND = "python3 -m unittest -q"
IGNORE = ".tasks/\n.mailboxes/\n.memory/\n.worktrees/\n.workflow_runtime/\n.task_outputs/\n.transcripts/\n.scheduled_tasks.json\n__pycache__/\n"


def git(workspace, *args):
    return subprocess.run(
        ["git", "-C", str(workspace), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def wait_for(predicate, seconds=240):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise TimeoutError("Declared integration phase did not reach its expected state")


def prepare(workspace):
    workspace.mkdir()  # Fresh directories only; failed experiments stay intact.
    case = json.loads(CASE.read_text())
    for name, text in case["files"].items():
        (workspace / name).write_text(text)
    (workspace / ".gitignore").write_text(IGNORE)
    git(workspace, "init", "-q")
    git(workspace, "config", "user.name", "Course instructor")
    git(workspace, "config", "user.email", "instructor@example.invalid")
    git(workspace, "add", ".")
    git(workspace, "commit", "-qm", "public broken exercise")


def receipt(workspace):
    # Git objects are independently checked by the verifier; avoid embedding them.
    return {
        str(p.relative_to(workspace)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(workspace.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(workspace).parts
    }


def normal(runtime, phases):
    host, workspace = runtime.host, runtime.workspace
    case = json.loads(CASE.read_text())
    runtime.submit(
        case["task"],
        "Both APIs follow the mounted shipping v3 contract, original tests are preserved, "
        "and the actual python3 -m unittest -q command has passed.",
    )
    if runtime.goal.active is not None or not (runtime.goal.last_status or {}).get("met"):
        raise RuntimeError("Public goal reviewer did not accept the repair phase")
    phases.append({"phase": "repair", "goal": runtime.goal.last_status})
    # Instructor Git operation, after the model's repair; never attributed to an Agent tool.
    git(workspace, "add", "shipping.py", "checkout.py")
    git(workspace, "commit", "-qm", "record native model repair")
    summary = host.spawn_subagent(
        "Read shipping.py and checkout.py using file tools. Summarize the two API contracts. "
        "Do not modify files or run Bash. Return only the observed summary."
    )
    phases.append({"phase": "one_shot_subagent", "summary": summary})
    task = host.create_task(
        "Review the repaired APIs",
        "Read shipping.py, checkout.py and both test files. Submit a short plan and wait for "
        "Lead approval before writing. Then write your source-based review to review.txt only, "
        "mark this assigned task completed with complete_task, and return a short summary. "
        "Do not run Bash, modify source/tests, or claim test execution.",
    )
    binding = host.create_worktree("review", task.id)
    if "created" not in binding:
        raise RuntimeError(binding)
    host.spawn_teammate_thread(
        "reviewer", "source reviewer", task.description, task.id, require_plan=True
    )

    def pending_plan():
        with host.team_lock:
            return next(
                (
                    p
                    for p in host.pending_requests.values()
                    if p.type == "plan_approval" and p.status == "pending" and p.task_id == task.id
                ),
                None,
            )

    plan = wait_for(pending_plan)
    review = host.run_review_plan(
        plan.request_id, True, "Instructor approves this read-and-review plan."
    )
    phases.append(
        {"phase": "instructor_plan_approval", "request": host.asdict(plan), "result": review}
    )
    wait_for(lambda: host.load_task(task.id).status == "completed")
    wait_for(lambda: host.active_teammates.get("reviewer") == "idle")
    peer_threads = {
        call["thread"]
        for call in runtime.model.calls
        if str(call["request"].get("system", "")).startswith("You are 'reviewer'")
    }
    branch = workspace / ".worktrees/review"
    review_text = (branch / "review.txt").read_text()
    if not review_text.strip() or (workspace / "review.txt").exists():
        raise RuntimeError("Review did not remain in its assigned worktree")
    host.run_request_shutdown("reviewer")
    wait_for(lambda: "reviewer" not in host.active_teammates)
    wait_for(
        lambda: not any(t.name in peer_threads and t.is_alive() for t in threading.enumerate())
    )
    events = host.consume_lead_inbox()
    git(branch, "add", "review.txt")
    git(branch, "commit", "-qm", "preserve native teammate review")
    removal = host.remove_worktree("review")
    if "retained" not in removal:
        raise RuntimeError(removal)
    phases.append(
        {
            "phase": "persistent_teammate",
            "task_id": task.id,
            "review": review_text,
            "lead_events": events,
            "removal": removal,
        }
    )
    runtime.start_services()
    runtime.submit(
        "Run the already approved command python3 -m unittest -q once with the bash tool's "
        "run_in_background boolean set to true. Read the actual task_notification before "
        "reporting its result. Do not edit files or claim test results before delivery."
    )
    if not runtime.wait_until_settled(240):
        raise TimeoutError("Background result was not delivered")
    phases.append({"phase": "native_background_delivered"})
    job = host.schedule_job(
        "* * * * *",
        "Use write_file to create scheduled.txt with exactly 'scheduled delivery observed'. "
        "Do not modify other files or run Bash. Return after the file tool succeeds.",
        recurring=False,
        durable=True,
    )
    if isinstance(job, str):
        raise TypeError(job)
    wait_for(lambda: (workspace / "scheduled.txt").is_file() and job.id not in host.scheduled_jobs)
    if not runtime.wait_until_settled(240):
        raise TimeoutError("Scheduled turn did not settle")
    phases.append({"phase": "real_clock_one_shot", "job_id": job.id})
    result = asyncio.run(
        runtime.workflow.run_workflow("course-review", {"files": list(case["files"])})
    )
    phases.append({"phase": "native_workflow_full_context", "result": result})
    if result["task"]["status"] != "completed":
        raise RuntimeError("Workflow failed; preserve partial evidence")
    with host.agent_lock:
        runtime.history[:] = host.compact_history(
            runtime.history, "Preserve completed source and original tests."
        )
    phases.append(
        {"phase": "explicit_native_compact", "cause": "instructor command, not size threshold"}
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    args.workspace = args.workspace.resolve()
    if args.report.resolve().is_relative_to(args.workspace):
        parser.error("Report must remain outside the Agent workspace")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as handle:
        json.dump({"status": "started", "profile": "normal_composed"}, handle)
    runtime, phases, error, traces = None, [], None, []
    try:
        prepare(args.workspace)
        runtime = Runtime(args.workspace, approved_commands=[COMMAND], maximum_requests=70)
        runtime.model.ledger = args.report.with_suffix(".calls.jsonl")
        with capture_native_traces() as traces:
            normal(runtime, phases)
    except Exception as caught:  # noqa: BLE001 - preserve every failed phase, no success reroll
        error = {"type": type(caught).__name__, "message": str(caught)}
    finally:
        if runtime:
            runtime.close()
        evidence = runtime.snapshot() if runtime else {}
        evidence.update(
            origin="live_native_integration_with_declared_instructor_orchestration",
            profile="normal_composed",
            phases=phases,
            error=error,
            status="returned" if error is None else "error",
            native_traces=traces,
            artifact_sha256=receipt(args.workspace) if args.workspace.exists() else {},
            independent_acceptance=None,
        )
        temporary = args.report.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )
        temporary.replace(args.report)
    print(json.dumps({"report": str(args.report), "status": evidence["status"], "error": error}))
    return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(main())
