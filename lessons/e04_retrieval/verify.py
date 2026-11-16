"""Independent, network-free verification of the live knowledge-loading task."""

import json
import os
import uuid
from pathlib import Path

from lessons.e02_tools_traces.samples import trace_errors


def main():
    runs = Path(os.environ.get("RUNS_DIR", "/data/runs"))
    report = json.loads((runs / "e04-agent.json").read_text())
    run_id = report["run_id"]
    if uuid.UUID(run_id).hex != run_id:
        raise ValueError("Invalid run ID")
    workspace = (Path(os.environ.get("WORKSPACES_DIR", "/data/workspaces")) / run_id).resolve()
    note = (workspace / "upload_notes.txt").resolve()
    if not note.is_relative_to(workspace):
        raise ValueError("Artifact outside workspace")
    text = note.read_text() if note.is_file() else ""
    criteria = json.loads(Path("/verification/e04.json").read_text())
    retrieved = {
        d["id"]
        for e in report["events"]
        if e["type"] == "tool" and e["call"]["name"] == "search_knowledge"
        for d in e["result"].get("hits", [])
    }
    checks = {
        "finished": report["status"] == "finished",
        "trace_valid": not trace_errors(report),
        "artifact_contents": all(s in text for s in criteria["required_strings"]),
        "required_documents_loaded": set(criteria["required_documents"]) <= retrieved,
        "artifact_matches_record": text == report["notes"],
    }
    grade = {
        "run_id": run_id,
        "checks": checks,
        "passed": all(checks.values()),
        "scope": "fixed fixture output and retrieval trace; not general answer faithfulness",
    }
    (runs / "e04-agent-grade.json").write_text(
        json.dumps(grade, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(grade))
    return int(not grade["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
