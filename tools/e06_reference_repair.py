"""Clarify one reference sentence; preserve the original answer and primary report."""

import asyncio
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ragas.metrics.collections import FactualCorrectness

from lessons.e03_judges.eval import Transport
from lessons.e05_faithfulness.eval import CapturingJudge
from lessons.e06_answer_quality.eval import scored

source = Path("/data/runs/e06-evaluation.json")
row = next(r for r in json.loads(source.read_text())["rows"] if r["case"]["id"] == "partial")
case = row["case"]
clarified = case["reference"].replace(
    "Use the X-Project-Token header.", "For authentication, use the X-Project-Token header."
)
assert clarified != case["reference"]
transport = Transport()
judge = CapturingJudge(transport)
try:
    metric = FactualCorrectness(llm=judge, mode="f1", atomicity="high", coverage="high")
    value = asyncio.run(metric.ascore(response=case["response"], reference=clarified)).value
    result = scored(value)
except Exception as error:  # noqa: BLE001 - preserve failed runs rather than manufacture a score
    result = {"status": "error", "score": None, "error": str(error)}
report = {
    "mode": "live_native_factual_correctness_reference_clarification",
    "source_report_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "response": case["response"],
    "original_reference": case["reference"],
    "clarified_reference": clarified,
    "original_score": row["metrics"]["RagasFactualCorrectness"]["score"],
    "result": result,
    "steps": judge.steps,
    "calls": transport.calls,
    "model_calls": len(transport.calls),
    "agent_new_execution": False,
}
Path("/data/runs/e06-reference-repair.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
)
print(json.dumps({"result": result, "model_calls": report["model_calls"]}))
raise SystemExit(int(result["status"] == "error"))
