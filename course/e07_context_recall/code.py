"""Remove one necessary source and inspect what remains uncovered."""

import argparse
import json
import uuid
from pathlib import Path

from deepeval.test_case import LLMTestCase

from eval_course.judge import JudgeModel
from eval_course.knowledge import catalog
from eval_course.records import save
from eval_course.tinyrag import retrieve

from .eval import coverage, judge_recall


def prepare():
    case = json.loads(Path(__file__).with_name("cases.jsonl").read_text().splitlines()[0])
    documents = catalog()
    versions = {d["path"]: d["sha256"] for d in documents}
    if any(versions.get(path) != digest for path, digest in case["sources"].items()):
        raise ValueError("Source changed; review facts and reference before scoring")
    hits = retrieve(case["query"], limit=3, documents=documents)
    selected = [p for p in hits if p["path"] in case["sources"]]
    if {p["path"] for p in selected} != set(case["sources"]):
        raise ValueError("Required teaching sources were not retrieved")
    missing = [p for p in selected if p["path"] != "atlas/logs.md"]
    facts = case["facts"]
    return (
        case,
        hits,
        {
            "complete": (selected, facts),
            "missing_logs": (missing, facts),
            "incomplete_reference": (missing, [f for f in facts if f["id"] != "log_days"]),
        },
    )


def summarize(parts, facts):
    paths = {p["path"] for p in parts}
    covered = [f["id"] for f in facts if f["source"] in paths]
    required_paths = {f["source"] for f in facts}
    return {
        "document_recall": coverage(required_paths, paths),
        "fact_recall": coverage([f["id"] for f in facts], covered),
        "covered": covered,
        "missing": [f["text"] for f in facts if f["id"] not in covered],
        "precision": len(paths & required_paths) / len(paths) if paths else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    case, hits, conditions = prepare()
    report = {"run_id": uuid.uuid4().hex, "case": case, "raw_hits": hits, "conditions": {}}
    model = JudgeModel() if args.judge else None
    for name, (parts, facts) in conditions.items():
        sample = LLMTestCase(
            input=case["query"],
            expected_output="\n".join(f["text"] for f in facts),
            retrieval_context=[p["text"] for p in parts],
        )
        row = {
            "contexts": parts,
            "required_facts": facts,
            "sample": sample.model_dump(mode="json"),
            "authored": summarize(parts, facts),
        }
        if model is not None:
            row["native"] = judge_recall(sample, model)
        report["conditions"][name] = row
    if model is not None:
        report["judge_calls"] = model.calls
    print(save(report, prefix="e07-suite"))
    return int(
        model is not None
        and any(row["native"]["status"] != "ok" for row in report["conditions"].values())
    )


if __name__ == "__main__":
    raise SystemExit(main())
