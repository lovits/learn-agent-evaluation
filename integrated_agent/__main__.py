"""Run the integrated coding Agent in one process and preserve its actual evidence."""

import argparse
import json
import os
import time
import uuid
from pathlib import Path

from .runtime import Runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--goal")
    parser.add_argument("--approve-command", action="append", default=None)
    parser.add_argument("--maximum-requests", type=int, default=80)
    parser.add_argument("--wait-seconds", type=float, default=120)
    args = parser.parse_args()
    if args.maximum_requests < 1 or not 0 <= args.wait_seconds <= 600:
        parser.error("Require positive request budget and 0..600 wait seconds")
    report = args.report or Path(os.environ.get("RUNS_DIR", "runs")) / (
        "integrated-" + uuid.uuid4().hex + ".json"
    )
    report = report.resolve()
    if report.is_relative_to(args.workspace.resolve()):
        parser.error("Evidence report must be outside the Agent workspace")
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("x") as handle:
        json.dump({"status": "started", "task": args.task}, handle)
    runtime = None
    status = "interrupted_or_incomplete"
    error = None
    try:
        runtime = Runtime(
            args.workspace,
            approved_commands=args.approve_command,
            maximum_requests=args.maximum_requests,
        )
        runtime.model.ledger = report.with_suffix(".calls.jsonl")
        runtime.start_services()
        runtime.submit(args.task, args.goal)
        settled = runtime.wait_until_settled(args.wait_seconds)
        status = "returned" if settled else "pending_at_deadline"
    except Exception as caught:  # noqa: BLE001 - final evidence is saved even on failure
        status, error = "error", {"type": type(caught).__name__, "message": str(caught)}
    finally:
        evidence = runtime.snapshot() if runtime else {}
        if status == "returned":
            if evidence.get("final_text", "").startswith("[Error]"):
                status = "application_error"
            elif evidence.get("goal_active") or (evidence.get("goal_last_status") or {}).get(
                "failed"
            ):
                status = "goal_incomplete"
        evidence.update(
            status=status,
            error=error,
            task=args.task,
            observed_at_unix=time.time(),
            independent_acceptance=None,
        )
        temporary = report.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )
        temporary.replace(report)
        if runtime:
            runtime.close()
    print(json.dumps({"report": str(report), "status": status, "independent_acceptance": None}))
    return int(status != "returned")


if __name__ == "__main__":
    raise SystemExit(main())
