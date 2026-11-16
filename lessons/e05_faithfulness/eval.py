"""Native DeepEval and Ragas faithfulness, with per-claim audit and evidence versions."""

import asyncio
import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase
from ragas.metrics.collections import Faithfulness

from lessons.e03_judges.eval import DeepJudge, Transport
from lessons.e04_retrieval.eval import ModernJudge

from .code import evidence_key, require_same_evidence

HERE = Path(__file__).parent


class CapturingJudge(ModernJudge):
    def __init__(self, transport):
        super().__init__(transport)
        self.steps = []

    def generate(self, prompt, response_model):
        result = super().generate(prompt, response_model)
        self.steps.append(
            {"schema": response_model.__name__, "result": result.model_dump(mode="json")}
        )
        return result


def evaluate(case):
    t = Transport()
    sample = LLMTestCase(
        input=case["question"],
        actual_output=case["response"],
        retrieval_context=[d["text"] for d in case["documents"]],
    )
    scores = {}
    try:
        metric = FaithfulnessMetric(
            model=DeepJudge(t), async_mode=False, include_reason=False, threshold=0.7
        )
        value = metric.measure(sample, _show_indicator=False)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid DeepEval score")
        scores["DeepEval"] = {
            "score": value,
            "claims": metric.claims,
            "truths": metric.truths,
            "verdicts": [v.model_dump(mode="json") for v in metric.verdicts],
            "passed": value >= 0.7,
        }
        metric.penalize_ambiguous_claims = True
        scores["DeepEval"]["penalized_same_verdicts"] = metric._calculate_score()
    except Exception as error:  # noqa: BLE001 - keep judge failures separate from low scores
        scores["DeepEval"] = {"score": None, "status": "error", "error": str(error)}
    judge = CapturingJudge(t)
    try:
        metric = Faithfulness(llm=judge)
        value = asyncio.run(
            metric.ascore(
                user_input=case["question"],
                response=case["response"],
                retrieved_contexts=[d["text"] for d in case["documents"]],
            )
        ).value
        if math.isnan(value):
            scores["Ragas"] = {"score": None, "status": "undefined_nan", "passed": None}
        elif math.isfinite(value) and 0 <= value <= 1:
            scores["Ragas"] = {"score": value, "status": "scored", "passed": value >= 0.7}
        else:
            raise ValueError("Invalid Ragas score")
    except Exception as error:  # noqa: BLE001 - keep judge failures separate from low scores
        scores["Ragas"] = {"score": None, "status": "error", "error": str(error)}
    scores["Ragas"]["steps"] = judge.steps
    return {
        "case": case,
        "evidence_key": evidence_key(case["documents"]),
        "metrics": scores,
        "calls": t.calls,
    }


def main():
    agent_path = HERE.parent / "e04_retrieval/agent_report.json"
    agent = json.loads(agent_path.read_text())
    documents = next(
        e["result"]["hits"]
        for e in agent["events"]
        if e["type"] == "tool" and e["call"]["name"] == "search_knowledge"
    )
    question = "Explain the upload authentication, size limit, status and optional retry behavior based only on retrieved project documentation."
    cases = [
        {
            **json.loads(line),
            "question": question,
            "documents": documents,
            "origin": "controlled_answer",
        }
        for line in (HERE / "cases.jsonl").read_text().splitlines()
    ]
    changed = [dict(d) for d in documents]
    for d in changed:
        if d["id"] == "e04/limits.md":
            d["text"] = d["text"].replace("1048576", "2097152").replace("1 MiB", "2 MiB")
            d["sha256"] = hashlib.sha256(d["text"].encode()).hexdigest()
    cases.append(
        {
            "id": "evidence_v2",
            "response": "The maximum upload size is 2097152 bytes.",
            "question": question,
            "documents": changed,
            "origin": "controlled_evidence_revision",
        }
    )
    cases.append(
        {
            "id": "recorded_agent",
            "response": agent["notes"],
            "question": agent["case"]["task"],
            "documents": documents,
            "origin": "recorded_live_agent_e04",
            "source_run_id": agent["run_id"],
        }
    )
    rejected = False
    try:
        require_same_evidence(evidence_key(documents), changed)
    except ValueError:
        rejected = True
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(evaluate, cases))
    errors = sum(v.get("status") == "error" for row in rows for v in row["metrics"].values())
    report = {
        "lesson": "e05",
        "mode": "live_judges_controlled_answers_and_recorded_agent",
        "rows": rows,
        "source_agent_sha256": hashlib.sha256(agent_path.read_bytes()).hexdigest(),
        "source_agent_run_id": agent["run_id"],
        "agent_new_execution": False,
        "stale_annotation_rejected": rejected,
        "model_calls": sum(len(row["calls"]) for row in rows),
        "metric_errors": errors,
        "implementation": {
            n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
            for n in ["code.py", "eval.py", "cases.jsonl"]
        },
    }
    Path("/data/runs/e05-evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps({"model_calls": report["model_calls"], "metric_errors": errors}))
    return int(bool(errors) or not rejected)


if __name__ == "__main__":
    raise SystemExit(main())
