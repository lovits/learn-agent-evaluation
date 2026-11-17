"""Re-score a frozen Agent answer and clearly labelled evidence counterexamples."""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

from deepeval.test_case import LLMTestCase

from eval_course.judge import JudgeModel
from eval_course.knowledge import PROJECT
from eval_course.records import save

from .eval import aggregate, judge_faithfulness


def prepare():
    cases = [
        json.loads(line)
        for line in Path(__file__).with_name("cases.jsonl").read_text().splitlines()
    ]
    source = cases[0]["source"]
    content = (PROJECT / source["path"]).read_bytes()
    if hashlib.sha256(content).hexdigest() != source["sha256"]:
        raise ValueError("Frozen Agent record changed; review samples before scoring")
    baseline = json.loads(content)["baseline"]
    samples = {}
    for case in cases:
        if case["id"] == "frozen_agent":
            samples[case["id"]] = LLMTestCase(
                input=baseline["task"],
                actual_output=baseline["final_answer"],
                retrieval_context=baseline["sample"]["retrieval_context"],
            )
        else:
            contexts = baseline["sample"]["retrieval_context"]
            if case.get("replace_log_days"):
                contexts = [
                    text.replace("[atlas/logs.md#0]", "[constructed/logs-30-days]").replace(
                        "14 天", "30 天"
                    )
                    for text in contexts
                ]
            samples[case["id"]] = LLMTestCase(
                input=case["query"], actual_output=case["answer"], retrieval_context=contexts
            )
    return cases, baseline["run_id"], samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    cases, source_run, samples = prepare()
    report = {"run_id": uuid.uuid4().hex, "source_run": source_run, "conditions": {}}
    model = JudgeModel() if args.judge else None
    for case in cases:
        row = {"case": case, "sample": samples[case["id"]].model_dump(mode="json")}
        if "teaching_labels" in case:
            row["authored"] = {
                "default_fraction": aggregate(case["teaching_labels"]),
                "supported_fraction": aggregate(case["teaching_labels"], True),
            }
        if model is not None:
            row["native"] = judge_faithfulness(samples[case["id"]], model)
        report["conditions"][case["id"]] = row
    if model is not None:
        report["judge_calls"] = model.calls
    print(save(report, prefix="e08-suite"))
    return int(
        model is not None
        and any(row["native"]["status"] == "error" for row in report["conditions"].values())
    )


if __name__ == "__main__":
    raise SystemExit(main())
