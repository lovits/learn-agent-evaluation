"""Compare controlled answers and optionally score the existing live Agent."""

import argparse
import json
import uuid
from pathlib import Path

from deepeval.test_case import LLMTestCase

from course.e04_scoring.eval import score
from course.e05_knowledge_context.code import run_task
from eval_course.judge import JudgeModel
from eval_course.knowledge import catalog
from eval_course.records import save
from eval_course.runtime import prepare_workspace

from .eval import fact_scores, judge_relevance, task_metric


def prepare():
    cases = [
        json.loads(line)
        for line in Path(__file__).with_name("cases.jsonl").read_text().splitlines()
    ]
    spec = cases[0]["spec"]
    documents = {d["path"]: d for d in catalog()}
    if any(
        documents.get(path, {}).get("sha256") != digest for path, digest in spec["sources"].items()
    ):
        raise ValueError("Reference source changed; review answers and annotations")
    samples = {
        case["id"]: LLMTestCase(
            input=spec["query"],
            actual_output=case["answer"],
            expected_output=spec["reference"],
            retrieval_context=[documents[path]["text"] for path in case["context_paths"]],
        )
        for case in cases
    }
    return spec, cases, samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    spec, cases, samples = prepare()
    run_id = uuid.uuid4().hex
    report = {"run_id": run_id, "spec": spec, "conditions": {}}
    for case in cases:
        report["conditions"][case["id"]] = {
            "case": case,
            "sample": samples[case["id"]].model_dump(mode="json"),
            "authored_facts": fact_scores(case["fact_ids"], spec["reference_fact_ids"]),
        }
    save(report, prefix="e09-suite")
    if args.live:
        workspace = prepare_workspace({"files": {}}, run_id)
        live = run_task(
            {
                "task": spec["query"] + "先查询知识库再回答；不要执行测试或发布。",
                "source": {
                    "path": "atlas/release.md",
                    "sha256": spec["sources"]["atlas/release.md"],
                },
                "reference": spec["reference"],
            },
            workspace,
            k=3,
            context_limit=2,
        )
        report["live_agent"] = live
        report["conditions"]["live_agent"] = {
            "origin": "new live Agent output; fact IDs not pre-annotated",
            "sample": live["sample"],
        }
        save(report, prefix="e09-suite")
    if args.judge:
        model = JudgeModel()
        for row in report["conditions"].values():
            try:
                sample = LLMTestCase(
                    **{
                        key: row["sample"][key]
                        for key in [
                            "input",
                            "actual_output",
                            "expected_output",
                            "retrieval_context",
                        ]
                    }
                )
                row["native_relevance"] = judge_relevance(sample, model)
                row["native_task_quality"] = score(task_metric(model), sample)
            finally:
                report["judge_calls"] = model.calls
                save(report, prefix="e09-suite")
    print(save(report, prefix="e09-suite"))
    return int(
        (args.live and report["live_agent"]["status"] != "finished")
        or (
            args.judge
            and any(
                row[key]["status"] == "error"
                for row in report["conditions"].values()
                for key in ["native_relevance", "native_task_quality"]
            )
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
