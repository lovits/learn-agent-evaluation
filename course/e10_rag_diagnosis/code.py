"""Replay one Agent generation turn with one controlled pipeline change at a time."""

import argparse
import copy
import hashlib
import json
import uuid
from pathlib import Path

from deepeval.test_case import LLMTestCase

from course.e04_scoring.eval import score
from course.e05_knowledge_context.code import sent_contexts
from course.e08_faithfulness.eval import judge_faithfulness
from course.e09_answer_quality.eval import task_metric
from eval_course.judge import JudgeModel
from eval_course.knowledge import PROJECT, catalog
from eval_course.records import save
from eval_course.runtime import call_model
from eval_course.tinyrag import retrieve

from .eval import first_gap, noise_fraction


def prepare():
    cases = [
        json.loads(line)
        for line in Path(__file__).with_name("cases.jsonl").read_text().splitlines()
    ]
    spec = cases[0]["spec"]
    content = (PROJECT / spec["trace"]["path"]).read_bytes()
    if hashlib.sha256(content).hexdigest() != spec["trace"]["sha256"]:
        raise ValueError("Frozen trace changed; review the replay input")
    trace = json.loads(content)["native_deepeval_experiment"]["live_agent"]
    base = catalog()
    versions = {d["path"]: d["sha256"] for d in base}
    if any(versions.get(path) != digest for path, digest in spec["sources"].items()):
        raise ValueError("Knowledge changed; review the reference and fault cases")
    rows = {}
    for case in cases:
        fault = case["fault"]
        documents = copy.deepcopy(base)
        if fault == "source_missing":
            documents = [d for d in documents if d["path"] != spec["source"]["path"]]
        if fault == "stale_source":
            document = next(d for d in documents if d["path"] == spec["source"]["path"])
            document["text"] = document["text"].replace("python -m pytest -q", "python -m unittest")
            document["sha256"] = hashlib.sha256(document["text"].encode()).hexdigest()
        native_hits = retrieve(trace["retrievals"][0]["query"], limit=3, documents=documents)
        retrieved = (
            [p for p in native_hits if p["path"] != spec["source"]["path"]]
            if fault == "retrieval_miss"
            else native_hits
        )
        selected = retrieved[:2]
        if fault == "assembly_drop":
            selected = [p for p in selected if p["path"] != spec["source"]["path"]]
        if fault in {"noise", "conflict"}:
            path = f"constructed/{fault}.md"
            selected = selected + [
                {
                    "path": path,
                    "chunk_id": path + "#0",
                    "text": case["injected_text"],
                    "origin": "constructed context injection",
                }
            ]
        manifest = [{k: d[k] for k in ["path", "sha256"]} for d in documents]
        rows[case["id"]] = {
            "case": case,
            "documents": manifest,
            "native_hits": native_hits,
            "retrieved": retrieved,
            "selected": selected,
            "contexts": [f"[{p['chunk_id']}]\n{p['text']}" for p in selected],
            "knowledge_version": hashlib.sha256(
                json.dumps(manifest, sort_keys=True).encode()
            ).hexdigest(),
            "first_evidence_gap": first_gap(documents, retrieved, selected, spec["source"]),
        }
    return spec, trace, rows


def replay(row, trace, policy):
    messages = copy.deepcopy(trace["model_inputs"][-1])
    messages[0]["content"] += policy
    results = [
        r
        for m in messages
        if m["role"] == "tool"
        for r in m["content"]
        if r.get("kind") == "knowledge_context"
    ]
    if len(results) != 1:
        raise ValueError("This lesson replays a trace with exactly one knowledge result")
    results[0]["output"] = {
        "knowledge_version": row["knowledge_version"],
        "contexts": row["contexts"],
    }
    row["model_input"] = messages
    response = call_model(messages, tools={})
    row["generation_response"] = response
    if response["reply"]["tool_calls"]:
        raise ValueError("Generation replay must answer without new tool calls")
    return LLMTestCase(
        input=messages[0]["content"],
        actual_output=response["reply"]["answer"],
        retrieval_context=sent_contexts([messages]),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    if args.judge and not args.live:
        parser.error("--judge requires --live; no answers are invented for scoring")
    spec, trace, rows = prepare()
    report = {
        "run_id": uuid.uuid4().hex,
        "mode": "frozen_trace_component_replay",
        "spec": spec,
        "conditions": rows,
        "noise_math": noise_fraction(**spec["noise_math"]),
    }
    model = JudgeModel() if args.judge else None
    save(report, prefix="e10-suite")
    if args.live:
        for row in rows.values():
            try:
                sample = replay(row, trace, spec["policy"])
                sample.expected_output = spec["reference"]
                row["sample"] = sample.model_dump(mode="json")
                if model is not None:
                    row["faithfulness"] = judge_faithfulness(sample, model)
                    row["task_quality"] = score(task_metric(model), sample)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                row["error"] = str(error)
            finally:
                if model is not None:
                    report["judge_calls"] = model.calls
                save(report, prefix="e10-suite")
    print(save(report, prefix="e10-suite"))
    return int(
        any(
            "error" in row
            or any(
                row.get(k, {}).get("status") == "error" for k in ["faithfulness", "task_quality"]
            )
            for row in rows.values()
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
