"""Judge recorded live experiments without rerunning the Agent or replacing its evidence."""

import asyncio
import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from deepeval.metrics import ContextualRelevancyMetric
from deepeval.test_case import LLMTestCase
from ragas.metrics.collections import NoiseSensitivity

from lessons.e03_judges.eval import DeepJudge, Transport
from lessons.e05_faithfulness.eval import CapturingJudge
from lessons.e06_answer_quality.eval import scored

from .code import EXPECTED

HERE = Path(__file__).parent
QUESTION = "For POST /upload, what authentication header, maximum file size in bytes, and over-limit HTTP status should a client use?"
REFERENCE = "For the current POST /upload API, the authentication header is X-Project-Token. The maximum upload size for POST /upload is 1048576 bytes. POST /upload requests larger than 1048576 bytes return HTTP 413."


class AuditedNoise(NoiseSensitivity):
    def _compute_score(self, answers):
        self.matrices = answers
        return super()._compute_score(answers)


def response_text(value):
    descriptions = {
        "auth_header": "the authentication header",
        "max_bytes": "the maximum upload size in bytes",
        "over_limit_status": "the over-limit HTTP status",
    }
    return " ".join(
        f"For POST /upload, {label} is {value[key]}."
        if value[key] is not None
        else f"The retrieved documents do not provide {label} for POST /upload; this value is unknown from the retrieved evidence."
        for key, label in descriptions.items()
    )


def evaluate(row):
    if not row["protocol_valid"]:
        return {"case_id": row["case"]["id"], "status": "invalid_agent_protocol", "calls": []}
    contexts = [d["text"] for d in row["retrievals"][-1]["after"]]
    response = response_text(row["artifact"]["value"])
    transport = Transport()
    scores = {}
    try:
        metric = ContextualRelevancyMetric(
            model=DeepJudge(transport), eval_mode="llm", async_mode=False, include_reason=False
        )
        value = metric.measure(
            LLMTestCase(input=QUESTION, actual_output=response, retrieval_context=contexts),
            _show_indicator=False,
        )
        scores["DeepEvalContextualRelevancy"] = scored(
            value, verdicts=[v.model_dump(mode="json") for v in metric.verdicts_list]
        )
    except Exception as error:  # noqa: BLE001 - keep execution failures separate from valid zero
        scores["DeepEvalContextualRelevancy"] = {
            "status": "error",
            "score": None,
            "error": str(error),
        }
    judge = CapturingJudge(transport)
    try:
        metric = AuditedNoise(llm=judge, mode="relevant")
        value = asyncio.run(
            metric.ascore(
                user_input=QUESTION,
                response=response,
                reference=REFERENCE,
                retrieved_contexts=contexts,
            )
        ).value
        metric.mode = "irrelevant"
        irrelevant = metric._compute_score(metric.matrices)
        scores["RagasNoiseSensitivity"] = {
            "status": "scored"
            if math.isfinite(value) and math.isfinite(irrelevant)
            else "undefined_nan",
            "score": value if math.isfinite(value) else None,
            "irrelevant_same_verdicts": irrelevant if math.isfinite(irrelevant) else None,
            "lower_is_better": True,
            "matrices": {k: v.tolist() for k, v in metric.matrices.items()},
        }
    except Exception as error:  # noqa: BLE001
        scores["RagasNoiseSensitivity"] = {"status": "error", "score": None, "error": str(error)}
    scores["RagasNoiseSensitivity"]["steps"] = judge.steps
    return {
        "case_id": row["case"]["id"],
        "status": "evaluated",
        "response_projection": response,
        "projection_scope": "Three business fields from the actual artifact; sources and final acknowledgement are not scored by these SDKs.",
        "metrics": scores,
        "calls": transport.calls,
    }


def main():
    source = Path("/data/runs/e07-agents.json")
    agents = json.loads(source.read_text())
    assert agents["reference"] == EXPECTED
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(evaluate, agents["rows"]))
    errors = sum(v["status"] == "error" for r in rows for v in r.get("metrics", {}).values())
    report = {
        "lesson": "e07",
        "mode": "native_judges_on_recorded_live_agent_interventions",
        "agent_new_execution": False,
        "source_agent_report_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "question": QUESTION,
        "reference": REFERENCE,
        "grading_protocol": "v2 explicit endpoint and evidence-scoped unknown values; no Agent output changed",
        "rows": rows,
        "model_calls": sum(len(r["calls"]) for r in rows),
        "metric_errors": errors,
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    Path("/data/runs/e07-evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps({"model_calls": report["model_calls"], "metric_errors": errors}))
    return int(bool(errors) or any(r["status"] != "evaluated" for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
