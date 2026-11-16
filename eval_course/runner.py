"""Run the actual pinned SDKs, then persist a strict-JSON experiment record."""

import asyncio
import importlib.metadata
import json
import math
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase
from ragas.metrics.collections import Faithfulness

from .data import contexts, load_cases
from .judges import DeepEvalJudge, LiveJSON, RagasJudge, Replay
from .knowledge import PROJECT


async def score_case(case: dict, mode="replay", root=None) -> dict:
    docs = contexts(case, frozen=(mode == "replay"), root=root)
    test = LLMTestCase(
        input=case["question"],
        actual_output=case["answer"],
        retrieval_context=[d["text"] for d in docs],
    )
    results = {}
    for name, penalize in [("deepeval_default", False), ("deepeval_penalize_ambiguous", True)]:
        backend = Replay(case) if mode == "replay" else LiveJSON()
        metric = FaithfulnessMetric(
            model=DeepEvalJudge(backend),
            eval_mode="llm",
            penalize_ambiguous_claims=penalize,
            include_reason=False,
        )
        score = await metric.a_measure(test, _show_indicator=False)
        results[name] = {
            "score": score,
            "claims": metric.claims,
            "verdicts": [v.model_dump(mode="json") for v in metric.verdicts],
            "calls": backend.calls,
            "claim_count": len(metric.claims),
        }
    backend = Replay(case) if mode == "replay" else LiveJSON()
    metric = Faithfulness(llm=RagasJudge(backend))
    result = await metric.ascore(
        user_input=case["question"],
        response=case["answer"],
        retrieved_contexts=[d["text"] for d in docs],
    )
    finite = math.isfinite(float(result.value))
    results["ragas"] = {
        "score": result.value if finite else None,
        "status": "scored" if finite else "not_scored",
        "not_scored_reason": None if finite else "empty_statements_or_verdicts",
        "calls": backend.calls,
    }
    return {
        "id": case["id"],
        "question": case["question"],
        "answer": case["answer"],
        "context_files": [{k: d[k] for k in ("path", "sha256")} for d in docs],
        "fixture_claims": case["claims"] if mode == "replay" else None,
        "metrics": results,
    }


def run(mode="replay", case_id=None, root=None) -> dict:
    if mode not in {"replay", "live"}:
        raise ValueError("mode 必须是 replay 或 live。")
    cases = [c for c in load_cases() if case_id is None or c["id"] == case_id]
    if not cases:
        raise ValueError(f"未知样本：{case_id}")
    rows = [asyncio.run(score_case(c, mode, root)) for c in cases]
    return {
        "run_id": uuid.uuid4().hex,
        "created_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "interpretation": (
            "真实 SDK + 课程预设模型输出；验证数据流与聚合，不是模型效果实验。"
            if mode == "replay"
            else "真实模型裁判；不同框架各自抽取和判定，结果有随机性。"
        ),
        "versions": {n: importlib.metadata.version(n) for n in ("deepeval", "ragas")},
        "source_versions": json.loads((PROJECT / "references/versions.json").read_text()),
        "judge_model": os.environ.get("JUDGE_MODEL") if mode == "live" else "teaching-fixture-replay",
        "rows": rows,
    }


def save(report: dict, folder=None) -> Path:
    folder = Path(folder or os.environ.get("RUNS_DIR", PROJECT / "runs"))
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{report['mode']}-{report['run_id']}.json"
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return target
