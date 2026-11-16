"""Deterministic retrieval contracts and native SDK reference-based metrics."""

import asyncio
import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
)
from deepeval.test_case import LLMTestCase
from ragas.llms.base import InstructorBaseRagasLLM
from ragas.metrics.collections import ContextPrecisionWithReference, ContextRecall

from eval_course.knowledge import catalog
from lessons.e03_judges.eval import DeepJudge, Transport

from .code import search_knowledge

HERE = Path(__file__).parent
QUESTION = "For POST /upload, what authentication header, maximum file size in bytes, and over-limit status code should the client use?"
REFERENCE = "Use the X-Project-Token header. The maximum file size is 1048576 bytes. Larger requests return HTTP 413."
REQUIRED = ["e04/auth.md", "e04/limits.md"]


def ranking(ids, relevant):
    ids = list(dict.fromkeys(ids))
    relevant = set(relevant)
    if not relevant:
        raise ValueError("No relevance annotation: recall is undefined, not perfect")
    flags = [int(i in relevant) for i in ids]
    found = sum(flags)
    numerator = sum(sum(flags[: i + 1]) / (i + 1) for i, v in enumerate(flags) if v)
    dcg = sum(v / math.log2(i + 2) for i, v in enumerate(flags))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(ids), len(relevant))))
    return {
        "precision": found / len(ids) if ids else 0.0,
        "recall": found / len(relevant),
        "ap_retrieved": numerator / found if found else 0.0,
        "ap_reference": numerator / len(relevant),
        "mrr": next((1 / (i + 1) for i, v in enumerate(flags) if v), 0.0),
        "ndcg": dcg / ideal if ideal else 0.0,
        "relevance": flags,
        "deduplication": "first occurrence by document ID",
    }


class ModernJudge(InstructorBaseRagasLLM):
    def __init__(self, transport):
        self.transport = transport

    def generate(self, prompt, response_model):
        text = self.transport.ask(
            prompt
            + "\nReturn JSON matching this schema:\n"
            + json.dumps(response_model.model_json_schema())
        )
        return response_model.model_validate_json(text)

    async def agenerate(self, prompt, response_model):
        return await asyncio.to_thread(self.generate, prompt, response_model)


def evaluate_variant(item):
    name, docs = item
    transport = Transport()
    contexts = [d["text"] for d in docs]
    scores = {}
    if not contexts:
        return {
            "name": name,
            "documents": docs,
            "rules": ranking([], REQUIRED),
            "sdk": {
                "status": "skipped",
                "reason": "empty retrieval; modern ContextRecall rejects empty contexts",
            },
            "calls": [],
        }
    sample = LLMTestCase(input=QUESTION, expected_output=REFERENCE, retrieval_context=contexts)
    for cls in (ContextualPrecisionMetric, ContextualRecallMetric, ContextualRelevancyMetric):
        try:
            metric = cls(
                model=DeepJudge(transport), include_reason=False, async_mode=False, threshold=0.7
            )
            score = metric.measure(sample, _show_indicator=False)
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Invalid metric score")
            scores[cls.__name__] = {
                "score": score,
                "passed": score >= 0.7,
                "verdicts": [
                    v.model_dump(mode="json")
                    for v in (
                        metric.verdicts_list
                        if cls is ContextualRelevancyMetric
                        else metric.verdicts
                    )
                ],
            }
        except Exception as error:  # noqa: BLE001 - preserve SDK failures as unscored
            scores[cls.__name__] = {"score": None, "error": str(error)}
    for cls in (ContextPrecisionWithReference, ContextRecall):
        try:
            metric = cls(llm=ModernJudge(transport))
            value = asyncio.run(
                metric.ascore(user_input=QUESTION, reference=REFERENCE, retrieved_contexts=contexts)
            ).value
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Invalid metric score")
            scores["Ragas" + cls.__name__] = {"score": value, "passed": value >= 0.7}
        except Exception as error:  # noqa: BLE001 - preserve SDK failures as unscored
            scores["Ragas" + cls.__name__] = {"score": None, "error": str(error)}
    return {
        "name": name,
        "documents": docs,
        "rules": ranking([d["id"] for d in docs], REQUIRED),
        "sdk": scores,
        "calls": transport.calls,
    }


def main():
    docs = {
        d["path"]: {"id": d["path"], "text": d["text"], "sha256": d["sha256"]} for d in catalog()
    }
    auth, limit, noise = [docs[p] for p in ("e04/auth.md", "e04/limits.md", "e04/noise.md")]
    variants = [
        ("good", [auth, limit, noise]),
        ("late", [noise, auth, limit]),
        ("missing", [auth]),
        ("empty", []),
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(evaluate_variant, variants))
    baseline = search_knowledge("POST upload API token size limit")
    report = {
        "lesson": "e04",
        "mode": "live_sdk_judges_controlled_retrieval_perturbations",
        "question": QUESTION,
        "reference": REFERENCE,
        "required_ids": REQUIRED,
        "baseline_retrieval": baseline,
        "baseline_rules": ranking([d["id"] for d in baseline], REQUIRED),
        "rows": rows,
        "incomplete_reference_demo": ranking([auth["id"]], [auth["id"]]),
        "model_calls": sum(len(r["calls"]) for r in rows),
        "implementation": {
            n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
            for n in ["code.py", "eval.py", "cases.jsonl"]
        },
    }
    target = Path("/data/runs/e04-evaluation.json")
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    errors = sum("error" in v for r in rows if r["name"] != "empty" for v in r["sdk"].values())
    print(
        json.dumps(
            {"model_calls": report["model_calls"], "metric_errors": errors, "report": str(target)}
        )
    )
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
