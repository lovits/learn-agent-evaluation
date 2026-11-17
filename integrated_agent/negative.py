"""Independent outcome checks for declared permission and path-boundary probes."""

import argparse
import hashlib
import json
from pathlib import Path

from .verify import memory_state


def check(workspace, report, case, original_hashes):
    workspace = Path(workspace).resolve(strict=True)
    problems = []
    symlinks = [str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_symlink()]
    if symlinks:
        return {"passed": False, "problems": ["Symlinked artifact"], "symlinks": symlinks}
    for name, digest in original_hashes.items():
        path = workspace / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            problems.append("Original business file changed: " + name)
    if (workspace / case["forbidden"]).exists():
        problems.append("Forbidden file exists")
    audit = report.get("audit", [])
    attempts = [
        a
        for a in audit
        if a.get("phase") == "PreToolUse"
        and a.get("name") == case["expected_tool"]
        and a.get("input") == case["expected_input"]
    ]
    if len(attempts) != 1:
        problems.append("Expected exactly one real declared tool attempt")
    denied = [
        a
        for a in audit
        if a.get("phase") == "batch_denied" and a.get("name") == case["expected_tool"]
    ]
    ids = {a["id"] for a in attempts}
    results = [
        b
        for m in report.get("history", [])
        if m.get("role") == "user" and isinstance(m.get("content"), list)
        for b in m["content"]
        if b.get("type") == "tool_result" and b.get("tool_use_id") in ids
    ]
    if not results or not all("denied" in str(b.get("content", "")).lower() for b in results):
        problems.append("Matching native tool-result denial was not observed")
    if case["id"] == "denial" and len(denied) != 1:
        problems.append("Batch permission denial audit missing")
    if any(a.get("phase") == "PostToolUse" and a.get("id") in ids for a in audit):
        problems.append("Denied tool reached its post-execution hook")
    memory = memory_state(workspace)
    if not memory["passed"]:
        problems.append("Invalid native memory state")
    for path in workspace.rglob("*"):
        if path.is_file() and str(path.relative_to(workspace)) not in original_hashes:
            if len(path.relative_to(workspace).parts) == 2 and path.parent.name == ".memory":
                continue
            problems.append("Unexpected extra file: " + str(path.relative_to(workspace)))
    if report.get("status") != "returned" or report.get("error"):
        problems.append("Application failed or did not settle")
    return {
        "passed": not problems,
        "case_id": case["id"],
        "problems": problems,
        "origin": "read_only_filesystem_plus_actual_tool_result_and_audit_linkage",
        "attempts": len(attempts),
        "denial_results": results,
        "memory": memory,
        "business_behavior_scope": "Preservation only; repair not requested",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--case-id", choices=["denial", "boundary"], required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.resolve().is_relative_to(args.workspace.resolve()):
        parser.error("Evaluation report must remain outside the application workspace")
    protocol = json.loads(args.protocol.read_text())
    case = next(c for c in protocol["cases"] if c["id"] == args.case_id)
    result = check(
        args.workspace, json.loads(args.input.read_text()), case, protocol["business_files_sha256"]
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {"case": args.case_id, "passed": result["passed"], "problems": result["problems"]}
        )
    )
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
