"""Run or resume the saved native review workflow; this is a component experiment."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from .runtime import Runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "resume"])
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--file", action="append")
    parser.add_argument("--interrupt-after-inspect", action="store_true")
    args = parser.parse_args()
    if args.action == "resume" and (not args.run_id or args.interrupt_after_inspect or args.file):
        parser.error("Resume requires a run ID and the original saved arguments")
    if args.report.resolve().is_relative_to(args.workspace.resolve()):
        parser.error("Report must remain outside the application workspace")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as handle:
        json.dump(
            {"status": "started", "origin": "native_workflow_component_not_agent_task"}, handle
        )
    runtime = Runtime(args.workspace, approved_commands=[], maximum_requests=12)
    runtime.model.ledger = args.report.with_suffix(".calls.jsonl")
    previous = os.environ.get("COURSE_INTERRUPT_REVIEW")
    result, error = None, None
    try:
        if args.interrupt_after_inspect:
            os.environ["COURSE_INTERRUPT_REVIEW"] = "after-inspect"
        else:
            os.environ.pop("COURSE_INTERRUPT_REVIEW", None)
        if args.action == "start":
            result = asyncio.run(
                runtime.workflow.run_workflow(
                    "course-review",
                    {"files": args.file or ["shipping.py", "checkout.py"]},
                )
            )
        else:
            result = asyncio.run(
                runtime.workflow.run_workflow("course-review", resume_from_run_id=args.run_id)
            )
    except Exception as caught:  # noqa: BLE001 - preserve SDK/registry/journal failures as failures
        error = {"type": type(caught).__name__, "message": str(caught)}
    finally:
        if previous is None:
            os.environ.pop("COURSE_INTERRUPT_REVIEW", None)
        else:
            os.environ["COURSE_INTERRUPT_REVIEW"] = previous
        report = {
            "origin": "live_native_workflow_component_not_agent_task",
            "action": args.action,
            "declared_instructor_interruption": args.interrupt_after_inspect,
            "result": result,
            "error": error,
            "model_calls": runtime.model.calls,
        }
        temporary = args.report.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )
        temporary.replace(args.report)
        runtime.close()
        runtime.model.sdk.close()
    status = result["task"]["status"] if result else "error"
    print(
        json.dumps(
            {
                "report": str(args.report),
                "status": status,
                "run_id": result["launched"]["runId"] if result else None,
            }
        )
    )
    return int(status != "completed")


if __name__ == "__main__":
    raise SystemExit(main())
