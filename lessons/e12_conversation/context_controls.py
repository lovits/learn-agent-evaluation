"""Execute deterministic compaction controls; protocol fixtures are not Agent/tool runs."""

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .context import ContextCompactor, check_pairs, size


class NoSummary:
    def generate(self, *args):
        raise AssertionError("These deterministic controls must not call a model")


def fixture(count, output):
    messages = [{"role": "user", "content": "Initial API constraint"}]
    for i in range(count):
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": {
                        "answer": "",
                        "tool_calls": [
                            {
                                "name": "read_file",
                                "arguments_json": json.dumps({"path": f"fixture-{i}.txt"}),
                            }
                        ],
                    },
                },
                {
                    "role": "tool",
                    "content": [{"call_id": f"fixture-{i}", "status": "ok", "output": output}],
                },
            ]
        )
    return messages


def run():
    rows = []
    for name, count, output, limit in (
        ("snip", 10, "small fixture", 100000),
        ("micro", 3, "historical result\n" * 100, 5000),
    ):
        original = fixture(count, output)
        with tempfile.TemporaryDirectory() as directory:
            compactor = ContextCompactor(Path(directory), NoSummary(), limit)
            prepared = compactor.prepare(copy.deepcopy(original), "Initial API constraint")
            check_pairs(prepared)
            recovered = []
            for event in compactor.events:
                if "sha256" in event:
                    recovered.append(
                        hashlib.sha256((Path(directory) / event["path"]).read_bytes()).hexdigest()
                        == event["sha256"]
                    )
            rows.append(
                {
                    "id": name,
                    "origin": "constructed_protocol_fixture_not_tool_execution",
                    "before_chars": size(original),
                    "after_chars": size(prepared),
                    "events": compactor.events,
                    "saved_files_read_back_match_hashes": all(recovered),
                    "pairs_valid": True,
                    "model_requests": 0,
                }
            )
    return rows


def main():
    rows = run()
    result = {
        "lesson": "e12",
        "mode": "deterministic_fixture_compaction_with_real_disk_roundtrip",
        "rows": rows,
    }
    root = Path(os.environ.get("RUNS_DIR", "runs"))
    (root / "e12-context-controls.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {"phases": [[e["phase"] for e in r["events"]] for r in rows], "model_requests": 0}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
