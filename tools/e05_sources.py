"""Re-score the recorded answer using source-prefixed judge inputs; preserve body-only results."""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lessons.e05_faithfulness.eval import evaluate

source = Path("/data/runs/e05-evaluation.json")
original = json.loads(source.read_text())["rows"][-1]["case"]
case = json.loads(json.dumps(original))
case["id"] = "recorded_agent_source_prefixed"
case["origin"] = "recorded_agent_same_answer_source_prefixed_judge_input"
for document in case["documents"]:
    document["original_text"] = document["text"]
    document["original_sha256"] = document["sha256"]
    document["text"] = "Source: " + document["id"] + "\n" + document["text"]
    document["sha256"] = hashlib.sha256(document["text"].encode()).hexdigest()
row = evaluate(case)
report = {
    "input_packing": "source-prefixed derived judge text; original evidence and hash retained; no knowledge-base revision",
    "answer_unchanged": case["response"] == original["response"],
    "rows": [row],
    "model_calls": len(row["calls"]),
}
Path("/data/runs/e05-source-prefixed.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
)
print({k: v["score"] for k, v in row["metrics"].items()})
raise SystemExit(int(any(v.get("status") == "error" for v in row["metrics"].values())))
