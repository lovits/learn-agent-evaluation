"""Execute one course task and save its actual run."""

import argparse
import importlib
import json
import uuid
from pathlib import Path

from eval_course.records import save
from eval_course.runtime import prepare_workspace

LESSONS = {"e01": "e01_success", "e02": "e02_samples"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lesson", choices=LESSONS)
    parser.add_argument("--case", required=True)
    args = parser.parse_args()
    module = importlib.import_module(f"course.{LESSONS[args.lesson]}.code")
    cases = [
        json.loads(line)
        for line in Path(module.__file__).with_name("cases.jsonl").read_text().splitlines()
    ]
    case = next(c for c in cases if c["id"] == args.case)
    run_id = uuid.uuid4().hex
    workspace = prepare_workspace(case, run_id)
    run = {
        "run_id": run_id,
        "lesson": args.lesson,
        "case_id": case["id"],
        "task": case["task"],
        "mode": "live_model",
        **module.agent_loop(case["task"], workspace),
    }
    save(run, prefix=args.lesson)
    print(json.dumps({"run_id": run_id, "status": run["status"]}))
    return 0 if run["status"] == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
