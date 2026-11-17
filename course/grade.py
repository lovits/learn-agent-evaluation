"""Read actual records and artifacts without invoking the model."""

import argparse
import importlib
import json
import os
from pathlib import Path

from eval_course.records import report_path, save

from .run import LESSONS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lesson", choices=LESSONS)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    module = importlib.import_module(f"course.{LESSONS[args.lesson]}.eval")
    run = json.loads(report_path(f"{args.lesson}-{args.run_id}.json").read_text())
    cases = [
        json.loads(line)
        for line in Path(module.__file__).with_name("cases.jsonl").read_text().splitlines()
    ]
    case = next(c for c in cases if c["id"] == run["case_id"])
    workspace = Path(os.environ.get("WORKSPACES_DIR", "workspaces")) / args.run_id
    grade = {"run_id": args.run_id, **module.evaluate(run, workspace, case)}
    save(grade, prefix=f"grade-{args.lesson}")
    print(json.dumps(grade, ensure_ascii=False, indent=2))
    return 0 if grade["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
