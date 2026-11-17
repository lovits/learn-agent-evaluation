"""Audit actual model-input text, separately from executing a whole-file read."""

import hashlib
import json
import os
from pathlib import Path


def log_exposure(row, original):
    total, expected_hash = len(original), hashlib.sha256(original.encode()).hexdigest()
    intervals, paths = [], {"diagnostics.log"}
    first_session = row["sessions"][0]
    paths.update(
        e["path"]
        for e in first_session["compaction_events"]
        if e.get("sha256") == expected_hash and e.get("chars") == total
    )
    for request in first_session["model_inputs"]:
        if request.get("response_received") is False:
            continue
        messages = request["messages"]
        for index, message in enumerate(messages):
            if message["role"] != "tool" or not index or messages[index - 1]["role"] != "assistant":
                continue
            calls = messages[index - 1]["content"].get("tool_calls", [])
            if len(calls) != len(message["content"]):
                raise ValueError("Cannot attribute tool results to their requested batch")
            for call, result in zip(calls, message["content"], strict=True):
                if call["name"] != "read_file" or result.get("status") != "ok":
                    continue
                args = json.loads(call["arguments_json"])
                if args.get("path") not in paths:
                    continue
                offset, output = int(args.get("offset", "0")), result.get("output", "")
                if result.get("visible_output_truncated"):
                    output = output.split("\nPreview:\n", 1)[-1]
                if output and output == original[offset : offset + len(output)]:
                    intervals.append((offset, offset + len(output)))
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return {
        "scope": "characters present in actual model inputs; not proof of internal reasoning",
        "total_chars": total,
        "unique_chars_exposed": sum(b - a for a, b in merged),
        "covered_intervals": merged,
        "complete_text_exposed": merged == [[0, total]],
    }


def main():
    root = Path(os.environ.get("RUNS_DIR", "runs"))
    agents = json.loads((root / "e12-agents.json").read_text())
    rows = [
        {
            "run_id": r["run_id"],
            "compact_enabled": r["compact_enabled"],
            **log_exposure(r, agents["case"]["files"]["diagnostics.log"]),
        }
        for r in agents["rows"]
    ]
    report = {"lesson": "e12", "mode": "post_run_actual_model_input_exposure_audit", "rows": rows}
    (root / "e12-exposure.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"complete_text_exposed": [r["complete_text_exposed"] for r in rows]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
