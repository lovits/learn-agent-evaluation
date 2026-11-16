"""Change retrieval k only; freeze development selection before opening holdout."""

import argparse
import asyncio
import hashlib
import json
import os
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from deepeval.test_case import LLMTestCase
from ragas.backends.inmemory import InMemoryBackend
from ragas.dataset import Dataset
from ragas.experiment import experiment

from eval_course.knowledge import document, search
from lessons.e01_agent_baseline.code import prepare_workspace
from lessons.e04_retrieval.code import agent_loop, call_model, dispatch

from .statistics import choose

HERE = Path(__file__).parent
REPEATS = 2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases():
    return [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines() if line]


def manifest(cases):
    project = HERE.parents[1]
    sources = [
        "lessons/e04_retrieval/code.py",
        "eval_course/knowledge.py",
        "tools/model_bridge.py",
        "lessons/e09_comparison/code.py",
        "lessons/e09_comparison/statistics.py",
        "lessons/e09_comparison/cases.jsonl",
        "uv.lock",
    ]
    return {
        "code_sha256": {p: sha(project / p) for p in sources},
        "documents": {p: document(p)["sha256"] for c in cases for p in c["knowledge_paths"]},
        "only_changed_factor": "retrieval_limit_k",
        "k_values": [1, 2],
        "repeats": REPEATS,
        "minimum_effect": 0.1,
        "model_sampling_seed": None,
    }


def limited_dispatch(case, k, corpus, retrievals):
    def execute(call, workspace, approve):
        if call.get("name") != "search_knowledge":
            return dispatch(call, workspace, approve)
        try:
            if json.loads(call["arguments_json"]) != {"query": case["query"]}:
                raise ValueError("The query is fixed in this controlled experiment")
            hits = [{**d, "id": d["path"]} for d in search(case["query"], limit=k, root=corpus)]
            retrievals.append({"query": case["query"], "k": k, "hits": hits})
            return {"decision": "allow", "reason": "controlled_retrieval_limit"}, {
                "status": "ok",
                "hits": hits,
                "output": json.dumps(hits, ensure_ascii=False),
            }
        except (ValueError, TypeError, KeyError, OSError) as error:
            return {"decision": "not_executed", "reason": "knowledge_error"}, {
                "status": "error",
                "output": str(error),
            }

    return execute


def inspect(workspace, case, returned_ids):
    path = workspace / "answer.json"
    raw = path.read_text() if path.is_file() else None
    try:
        value = json.loads(raw) if raw is not None else None
        if not isinstance(value, dict) or set(value) != {*case["expected"], "sources"}:
            raise ValueError("Wrong output object keys")
        if not isinstance(value["sources"], list) or not all(
            isinstance(s, str) and s in returned_ids for s in value["sources"]
        ):
            raise ValueError("Sources must be actual retrieved IDs")
        matches = {
            key: type(value[key]) is type(expected) and value[key] == expected
            for key, expected in case["expected"].items()
        }
        return {
            "raw": raw,
            "value": value,
            "valid": True,
            "field_matches": matches,
            "passed": all(matches.values()),
        }
    except (ValueError, TypeError) as error:
        return {"raw": raw, "valid": False, "passed": False, "error": str(error)}


def execute_trial(case, k, repeat, order):
    run_id = uuid.uuid4().hex
    workspace = prepare_workspace(case, run_id)
    retrievals, requests = [], 0

    def counted_model(messages):
        nonlocal requests
        requests += 1
        return call_model(messages)

    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="e09-corpus-") as temp:
        corpus = Path(temp)
        for name in case["knowledge_paths"]:
            target = corpus / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(document(name)["text"])
        result = agent_loop(
            case["task"],
            workspace,
            model=counted_model,
            tool_dispatch=limited_dispatch(case, k, corpus, retrievals),
        )
    elapsed = time.monotonic() - start
    returned = {d["id"] for r in retrievals for d in r["hits"]}
    artifact = inspect(workspace, case, returned)
    sample = LLMTestCase(
        input=case["task"],
        actual_output=artifact["raw"] or "[no file produced]",
        expected_output=json.dumps(case["expected"]),
        retrieval_context=[d["text"] for r in retrievals for d in r["hits"]],
        metadata={"case_id": case["id"], "k": k, "repeat": repeat, "run_id": run_id},
    )
    return {
        "case_id": case["id"],
        "family": case["family"],
        "split": case["split"],
        "stratum": case["stratum"],
        "k": k,
        "repeat": repeat,
        "order": order,
        "run_id": run_id,
        "elapsed_seconds": round(elapsed, 6),
        "application_requests": requests,
        "token_count": None,
        "cost": None,
        "artifact": artifact,
        "passed": artifact["passed"] and result["status"] == "finished",
        "retrievals": retrievals,
        "deepeval_sample": sample.model_dump(mode="json"),
        **result,
    }


async def run_phase(cases, repeats=REPEATS, runner=execute_trial, progress_path=None):
    backend = InMemoryBackend()

    @experiment(backend=backend)
    async def trial(row):
        return await asyncio.to_thread(runner, row["case"], row["k"], row["repeat"], row["order"])

    rows = []
    for case in cases:
        for repeat in range(repeats):
            for k in [1, 2] if repeat % 2 == 0 else [2, 1]:
                item = {"case": case, "repeat": repeat, "k": k, "order": len(rows)}
                dataset = Dataset("one-matched-trial", backend=backend, data=[item])
                result = await trial.arun(dataset, name="e09-trial-" + str(len(rows)))
                if len(result) != 1:
                    raise RuntimeError(
                        "Ragas experiment omitted a failed trial; comparison is incomplete"
                    )
                rows.append(result[0])
                if progress_path is not None:
                    progress_path.write_text(
                        json.dumps({"complete": False, "rows": rows}, ensure_ascii=False, indent=2)
                        + "\n"
                    )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["development", "holdout"], required=True)
    args = parser.parse_args()
    root = Path(os.environ.get("RUNS_DIR", "runs"))
    all_cases = load_cases()
    frozen = manifest(all_cases)
    decision_path = root / "e09-decision.json"
    decision = None
    if args.phase == "holdout":
        decision = json.loads(decision_path.read_text())
        if decision["manifest"] != frozen:
            raise ValueError(
                "Code, data or protocol changed after selection; start a new experiment"
            )
    cases = [c for c in all_cases if c["split"] == args.phase]
    rows = asyncio.run(run_phase(cases, progress_path=root / f"e09-{args.phase}.partial.json"))
    report = {
        "lesson": "e09",
        "phase": args.phase,
        "mode": "live_agent",
        "created_at": datetime.now(UTC).isoformat(),
        "manifest": frozen,
        "rows": rows,
        "native_ragas_experiments": len(rows),
        "decision": decision,
        "scope": "public synthetic family split; not a production blind benchmark",
    }
    target = root / f"e09-{args.phase}.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.phase == "development":
        decision = {
            **choose(rows),
            "manifest": frozen,
            "development_report_sha256": sha(target),
            "frozen_before_holdout": datetime.now(UTC).isoformat(),
        }
        decision_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {"report": str(target), "trials": len(rows), "selected_k": decision["selected_k"]}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
