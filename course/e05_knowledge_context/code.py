"""Give the existing Agent a TinyRAG tool; retain candidates and actual model inputs."""

import argparse
import copy
import hashlib
import json
import uuid
from pathlib import Path

from course.e02_samples.code import agent_loop
from course.e02_samples.samples import to_deepeval
from course.e02_samples.tools import TOOLS as FILE_TOOLS
from course.e02_samples.tools import execute
from eval_course.knowledge import catalog
from eval_course.records import save
from eval_course.runtime import call_model, prepare_workspace
from eval_course.tinyrag import retrieve

TOOLS = {**FILE_TOOLS, "search_knowledge": {"query": "Search the mounted knowledge base"}}


def sent_contexts(model_inputs):
    if not model_inputs:
        return []
    return [
        text
        for message in model_inputs[-1]
        if message["role"] == "tool"
        for result in message["content"]
        if result.get("kind") == "knowledge_context"
        for text in result["output"]["contexts"]
    ]


def run_task(case, workspace, k=3, context_limit=1, root=None, model=None):
    if not 1 <= context_limit <= k <= 10:
        raise ValueError("Require 1 <= context_limit <= k <= 10")
    documents = catalog(root)
    manifest = [{key: d[key] for key in ["path", "sha256"]} for d in documents]
    version = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    retrievals, model_inputs = [], []

    def dispatch(name, arguments, workspace):
        if name != "search_knowledge":
            return execute(name, arguments, workspace)
        if set(arguments) != {"query"} or not isinstance(arguments["query"], str):
            return {"status": "invalid", "output": "search_knowledge requires a query string"}
        try:
            hits = retrieve(arguments["query"], limit=k, documents=documents)
        except (OSError, ValueError) as error:
            return {"status": "error", "output": str(error)}
        selected = hits[:context_limit]
        emitted = [f"[{part['chunk_id']}]\n{part['text']}" for part in selected]
        retrievals.append(
            {"query": arguments["query"], "hits": hits, "selected": selected, "emitted": emitted}
        )
        return {
            "status": "ok",
            "kind": "knowledge_context",
            "output": {"knowledge_version": version, "contexts": emitted},
        }

    def next_response(messages):
        response = model(messages) if model else call_model(messages, tools=TOOLS)
        model_inputs.append(copy.deepcopy(messages))
        return response

    run = agent_loop(case["task"], workspace, next_response, execute_tool=dispatch)
    run.update(
        task=case["task"],
        retrievals=retrievals,
        model_inputs=model_inputs,
        knowledge={"sha256": version, "documents": manifest},
        retrieval_settings={"k": k, "context_limit": context_limit},
    )
    sample = to_deepeval(run)
    sample.retrieval_context = sent_contexts(model_inputs)
    reference = next((d for d in documents if d["path"] == case["source"]["path"]), None)
    current = reference is not None and reference["sha256"] == case["source"]["sha256"]
    sample.context = [reference["text"]] if current else None
    sample.expected_output = case["reference"] if current else None
    run["reference_status"] = "current" if current else "source_changed_or_missing"
    run["sample"] = sample.model_dump(mode="json")
    return run


def main():
    from .eval import check_run

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--context-limit", type=int, default=1)
    args = parser.parse_args()
    case = json.loads(Path(__file__).with_name("cases.jsonl").read_text().splitlines()[0])
    run_id = uuid.uuid4().hex
    workspace = prepare_workspace({"files": {}}, run_id)
    report = {
        "run_id": run_id,
        "mode": "live_model",
        "case_id": case["id"],
        **run_task(case, workspace, args.k, args.context_limit),
    }
    report["checks"] = check_run(report)
    print(save(report, prefix="e05"))
    return 0 if report["status"] == "finished" and all(report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
