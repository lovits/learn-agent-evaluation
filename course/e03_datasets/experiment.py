"""Reuse lesson two's Agent for one approved task, keeping reference and output apart."""

import argparse
import uuid

from course.e02_samples.code import agent_loop
from course.e02_samples.samples import to_deepeval
from eval_course.records import save
from eval_course.runtime import prepare_workspace

from .code import curate, load_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="auth-header")
    args = parser.parse_args()
    rows, _ = curate(load_candidates())
    row = next(row for row in rows if row["id"] == args.case)
    run_id = uuid.uuid4().hex
    workspace = prepare_workspace({"files": {"upload.md": row["context"]}}, run_id)
    run = {
        "run_id": run_id,
        "case_id": row["id"],
        "task": row["task"],
        "mode": "live_model",
        **agent_loop(row["task"], workspace),
    }
    sample = to_deepeval(run)
    sample.expected_output = row["reference"]
    run["sample"] = sample.model_dump(mode="json")
    run["source"] = row["source"]
    run["split"] = row["split"]
    print(save(run, prefix="e03"))
    return 0 if run["status"] == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
