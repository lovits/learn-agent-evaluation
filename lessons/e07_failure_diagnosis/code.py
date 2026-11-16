"""Only fault switches and stage records are new; reuse the e04 Agent loop."""

import hashlib
import json
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

from eval_course.knowledge import document
from lessons.e01_agent_baseline.code import prepare_workspace
from lessons.e04_retrieval.code import agent_loop, dispatch, search_knowledge

HERE = Path(__file__).parent
QUERY = "POST upload API token size limit"
EXPECTED = {"auth_header": "X-Project-Token", "max_bytes": 1048576, "over_limit_status": 413}
REQUIRED = {"e04/auth.md", "e04/limits.md"}
TASK = (
    f"First call search_knowledge with exactly this query: {QUERY}. "
    "Using only the current upload documentation, write upload_notes.json with exactly four keys: "
    "auth_header (string or null), max_bytes (integer or null), over_limit_status (integer or null), "
    "and sources (array of source document IDs). Use null for facts missing from the evidence; "
    "do not guess. Preserve current specifications over explicitly expired legacy notes. "
    "Read back the file before finishing. Do not call network APIs or read the knowledge mount "
    "through Bash; use search_knowledge."
)


def extra_document(kind):
    text = (
        "Expired legacy upload specification v0, not current. POST /upload used a maximum "
        "of 524288 bytes. The current specification supersedes this historical note."
        if kind == "add_old"
        else "Office theme guide. The editor theme is dark green. The meeting room has 12 chairs."
    )
    return {
        "id": f"e07/{kind}.md",
        "text": text,
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def fault_dispatch(case_id, corpus, retrievals):
    def execute(call, workspace, approve):
        if call.get("name") != "search_knowledge":
            return dispatch(call, workspace, approve)
        try:
            args = json.loads(call["arguments_json"])
            if args != {"query": QUERY}:
                raise ValueError("Use the fixed query so retrieval experiments remain comparable")
            hits = search_knowledge(QUERY, root=corpus)
            before = json.loads(json.dumps(hits))
            if case_id == "drop_hit":
                hits = [d for d in hits if d["id"] != "e04/limits.md"]
            if case_id in ("add_old", "add_noise"):
                hits = [*hits, extra_document(case_id)]
            retrievals.append({"query": QUERY, "before": before, "after": hits})
            return {"decision": "allow", "reason": "controlled_read_only_snapshot"}, {
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


def call_model(messages, faulty_generation=False):
    request = Request(
        os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8766/next"),
        data=json.dumps(
            {"lesson": "e07", "messages": messages, "faulty_generation": faulty_generation}
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=200) as response:
        return json.load(response)


def inspect_artifact(workspace):
    path = workspace / "upload_notes.json"
    raw = path.read_text() if path.is_file() else None
    try:
        value = json.loads(raw) if raw is not None else None
        if not isinstance(value, dict) or set(value) != {*EXPECTED, "sources"}:
            raise ValueError("Expected three business fields and sources")
        if value["auth_header"] is not None and not isinstance(value["auth_header"], str):
            raise ValueError("auth_header must be a string or null")
        for key in ("max_bytes", "over_limit_status"):
            if value[key] is not None and type(value[key]) is not int:
                raise ValueError("Numeric fields must be integers or null")
        if not isinstance(value["sources"], list) or not all(
            isinstance(x, str) for x in value["sources"]
        ):
            raise ValueError("sources must be a string array")
        return {
            "status": "valid",
            "raw": raw,
            "value": value,
            "field_matches": {k: value[k] == v for k, v in EXPECTED.items()},
        }
    except (ValueError, TypeError) as error:
        return {"status": "invalid", "raw": raw, "error": str(error)}


def diagnose(available_ids, returned_ids, artifact):
    if artifact["status"] != "valid":
        return "artifact_error"
    if not REQUIRED <= set(available_ids):
        return "knowledge_gap"
    if not REQUIRED <= set(returned_ids):
        return "retrieval_gap"
    if all(artifact["field_matches"].values()):
        return "no_observed_task_failure"
    return "generation_mismatch_requires_review"


def run_case(case, documents, model=None):
    workspace = prepare_workspace({}, "e07-" + uuid.uuid4().hex)
    available = [d for d in documents if case["id"] != "drop_doc" or d["id"] != "e04/limits.md"]
    retrievals = []
    with tempfile.TemporaryDirectory(prefix="e07-corpus-") as folder:
        corpus = Path(folder)
        for doc in available:
            path = corpus / doc["id"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(doc["text"])
        result = agent_loop(
            TASK,
            workspace,
            model=model or (lambda messages: call_model(messages, case["id"] == "bad_prompt")),
            tool_dispatch=fault_dispatch(case["id"], corpus, retrievals),
        )
    artifact = inspect_artifact(workspace)
    returned = retrievals[-1]["after"] if retrievals else []
    return {
        "case": case,
        "workspace_id": workspace.name,
        "task": TASK,
        "available_documents": available,
        "retrievals": retrievals,
        "artifact": artifact,
        "diagnosis": diagnose([d["id"] for d in available], [d["id"] for d in returned], artifact),
        "protocol_valid": result["status"] == "finished"
        and bool(retrievals)
        and artifact["status"] == "valid",
        **result,
    }


def main():
    documents = []
    for name in sorted(REQUIRED):
        doc = document(name)
        documents.append({"id": doc["path"], "text": doc["text"], "sha256": doc["sha256"]})
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines()]
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda case: run_case(case, documents), cases))
    report = {
        "lesson": "e07",
        "mode": "live_agent_controlled_stage_interventions",
        "rows": rows,
        "reference": EXPECTED,
        "reference_version": "e04-synthetic-contract-v1",
        "source_mount_unchanged": all(
            document(d["id"])["sha256"] == d["sha256"] for d in documents
        ),
        "model_calls": sum(e["type"] == "model" for r in rows for e in r["events"]),
        "implementation": {
            n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
            for n in ["code.py", "cases.jsonl"]
        },
    }
    target = Path(os.environ.get("RUNS_DIR", "runs")) / "e07-agents.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "model_calls": report["model_calls"],
                "protocol_valid": sum(r["protocol_valid"] for r in rows),
            }
        )
    )
    return int(not report["source_mount_unchanged"] or not all(r["protocol_valid"] for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
