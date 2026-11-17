"""Freeze TinyRAG candidates, label their usefulness, and isolate ordering effects."""

import argparse
import json
import uuid
from pathlib import Path

from deepeval.test_case import LLMTestCase

from eval_course.judge import JudgeModel
from eval_course.knowledge import catalog
from eval_course.records import save
from eval_course.tinyrag import retrieve

from .eval import judge_precision, judge_relevancy, ranking


def prepare():
    case = json.loads(Path(__file__).with_name("cases.jsonl").read_text().splitlines()[0])
    documents = catalog()
    versions = {d["path"]: d["sha256"] for d in documents}
    if any(versions.get(path) != digest for path, digest in case["sources"].items()):
        raise ValueError("Source changed; review relevance labels and reference before scoring")
    hits = retrieve(case["query"], limit=3, documents=documents)
    if {p["chunk_id"] for p in hits} != set(case["labels"]):
        raise ValueError("Candidate set changed; annotate new candidates before comparison")
    useful_first = sorted(hits, key=lambda p: -case["labels"][p["chunk_id"]]["value"])
    useful_last = sorted(hits, key=lambda p: case["labels"][p["chunk_id"]]["value"])
    return (
        case,
        hits,
        {
            "original": hits,
            "useful_first": useful_first,
            "useful_last": useful_last,
            "trailing_noise": useful_first + [case["added_noise"]],
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    case, hits, orders = prepare()
    report = {
        "run_id": uuid.uuid4().hex,
        "query": case["query"],
        "reference": case["reference"],
        "sources": case["sources"],
        "raw_hits": hits,
        "annotation_origin": case["annotation_origin"],
        "orders": {},
    }
    for name, parts in orders.items():
        labels = [
            case["labels"][p["chunk_id"]]["value"]
            if p["chunk_id"] in case["labels"]
            else p["label"]
            for p in parts
        ]
        report["orders"][name] = {
            "ids": [p["chunk_id"] for p in parts],
            "labels": labels,
            "scores": ranking(labels),
        }
    if args.judge:
        model = JudgeModel()
        report["native_precision"] = {}
        for name in ["original", "useful_first"]:
            sample = LLMTestCase(
                input=case["query"],
                expected_output=case["reference"],
                retrieval_context=[p["text"] for p in orders[name]],
            )
            report["native_precision"][name] = {
                "sample": sample.model_dump(mode="json"),
                **judge_precision(sample, model),
            }
        sample = LLMTestCase(input=case["query"], retrieval_context=[p["text"] for p in hits])
        report["native_relevancy"] = {
            "sample": sample.model_dump(mode="json"),
            **judge_relevancy(sample, model),
        }
        report["judge_calls"] = model.calls
    print(save(report, prefix="e06-suite"))
    if args.judge:
        return (
            0
            if all(
                r["status"] == "ok"
                for r in [*report["native_precision"].values(), report["native_relevancy"]]
            )
            else 1
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
