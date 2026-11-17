"""Native GEval, DiscreteMetric alignment and BasePrompt language adaptation."""

import argparse
import asyncio
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from pydantic import BaseModel
from ragas.backends.inmemory import InMemoryBackend
from ragas.dataset import Dataset
from ragas.metrics.discrete import DiscreteMetric
from ragas.prompt.metrics.base_prompt import BasePrompt

from lessons.e03_judges.eval import DeepJudge, Transport

from .code import (
    HERE,
    RUBRIC,
    STEPS,
    alignment,
    digest,
    equivalent_pairs,
    judge_input,
    select_version,
    validate_cases,
)


class StructuredJudge:
    """Transport only; native metrics still build prompts and validate categorical output."""

    def __init__(self, transport):
        self.transport = transport

    def generate(self, prompt, response_model):
        prompt += "\nReturn only JSON matching this schema:\n" + json.dumps(
            response_model.model_json_schema()
        )
        return response_model.model_validate_json(self.transport.ask(prompt))

    async def agenerate(self, prompt, response_model):
        return await asyncio.to_thread(self.generate, prompt, response_model)


class ReportInput(BaseModel):
    task: str
    evidence: dict[str, int | bool]
    response: str


class Verdict(BaseModel):
    reason: str
    value: Literal["pass", "fail"]


class TranslatedVerdict(BaseModel):
    reason: str
    value: Literal[0, 1]


class ReportPrompt(BasePrompt):
    input_model = ReportInput
    output_model = TranslatedVerdict
    instruction = RUBRIC + " Return value 1 for a fully correct report, otherwise value 0."

    def __init__(self, train):
        self.examples = [
            (
                ReportInput(task=r["task"], evidence=r["evidence"], response=r["response"]),
                TranslatedVerdict(reason=r["label_reason"], value=int(r["label"] == "pass")),
            )
            for r in train[:2]
        ]


def ragas_dataset(rows, name):
    data = [
        {
            "context": judge_input(r),
            "response": r["response"],
            "report_accuracy": r["label"],
            "report_accuracy_reason": r["label_reason"],
            "id": r["id"],
        }
        for r in rows
    ]
    backend = InMemoryBackend()
    backend.save_dataset(name, data)
    return Dataset(name, backend)


def metric():
    return DiscreteMetric(
        name="report_accuracy",
        allowed_values=["pass", "fail"],
        prompt=RUBRIC
        + "\nInput: {context}\nActual output: {response}\nReturn pass or fail with reason.",
    )


def score(row, version):
    transport = Transport()
    result = {"id": row["id"], "label": row["label"], "prediction": None, "version": version}
    try:
        judge = GEval(
            name="Completion report accuracy",
            evaluation_steps=STEPS[version],
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            model=DeepJudge(transport),
            async_mode=False,
            threshold=0.7,
        )
        value = judge.measure(
            LLMTestCase(input=judge_input(row), actual_output=row["response"]),
            _show_indicator=False,
        )
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("GEval score outside 0..1")
        result.update(
            score=value, prediction="pass" if value >= 0.7 else "fail", reason=judge.reason
        )
    except Exception as error:  # noqa: BLE001 - retain unscored SDK/transport failures
        result["error"] = str(error)
    result["calls"] = transport.calls
    return result


def atomic_save(target, report):
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(os.environ.get("RUNS_DIR", "runs")) / "e15-calibration.json",
    )
    args = parser.parse_args()
    target = args.report
    if target.exists():
        raise FileExistsError("Archive existing report before an explicitly new experiment")
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = validate_cases(
        [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines()]
    )
    train = [r for r in rows if r["split"] == "train"]
    dev = [r for r in rows if r["split"] == "dev"]
    report = {
        "lesson": "e15",
        "started_at": datetime.now(UTC).isoformat(),
        "status": "running",
        "origin": "live_native_judges_on_instructor_constructed_reports_not_agent_runs",
        "human_reviewed": False,
        "dataset_sha256": digest(rows),
        "stages": {},
        "application_model_calls": 0,
        "exact_judge_model": None,
        "invoice_cost": None,
    }
    atomic_save(target, report)
    with ThreadPoolExecutor(max_workers=4) as pool:
        development = {
            v: list(pool.map(lambda r, version=v: score(r, version), dev)) for v in STEPS
        }
    report["stages"]["development"] = development
    selected = select_version(development)
    report["frozen_selection_before_holdout"] = {
        "version": selected,
        "threshold": 0.7,
        "steps": STEPS[selected],
        "at": datetime.now(UTC).isoformat(),
        "development_sha256": digest(development),
        "rule": "maximum scored coverage, minimum false passes, maximum agreement; ties v2",
    }
    # Persist the decision before reading holdout rows into the evaluation stage.
    atomic_save(target, report)
    holdout = [r for r in rows if r["split"] == "holdout"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        report["stages"]["geval_holdout"] = list(pool.map(lambda r: score(r, selected), holdout))
    atomic_save(target, report)
    transport = Transport()
    llm = StructuredJudge(transport)
    for stage, aligned in (("ragas_before", False), ("ragas_after", True)):
        judge = metric()
        if aligned:
            # Native no-embedding fallback: recent examples, NOT semantic retrieval or training.
            judge.align(
                ragas_dataset(train, "training"), embedding_model=None, max_similar_examples=4
            )
        start = len(transport.calls)
        try:
            result = judge.validate_alignment(llm, ragas_dataset(holdout, "heldout"))
            predictions = result.pop("df").to_dict("records")
            report["stages"][stage] = {
                **result,
                "rows": [
                    {
                        "id": r["id"],
                        "label": r["report_accuracy"],
                        "prediction": r["report_accuracy_pred"],
                    }
                    for r in predictions
                ],
                "calls": transport.calls[start:],
                "semantic_embedding_retrieval": False,
            }
        except Exception as error:  # noqa: BLE001 - preserve partial calls and stage failure
            report["stages"][stage] = {"error": str(error), "calls": transport.calls[start:]}
        atomic_save(target, report)
    start = len(transport.calls)
    prompt = ReportPrompt(train)
    try:
        adapted = asyncio.run(prompt.adapt("chinese", llm, adapt_instruction=True))
        report["stages"]["translation"] = {
            "instruction": adapted.instruction,
            "examples": [[a.model_dump(), b.model_dump()] for a, b in adapted.examples],
            "calls": transport.calls[start:],
            "semantic_human_reviewed": False,
            "schema_unchanged": prompt.output_model.model_json_schema()
            == adapted.output_model.model_json_schema(),
        }
        for name, current in (("language_before", prompt), ("language_after", adapted)):
            scored = []
            for row in holdout:
                if row["variant"] not in {"correct", "incorrect"}:
                    continue
                start = len(transport.calls)
                data = ReportInput(
                    task=row["task"], evidence=row["evidence"], response=row["response"]
                )
                result = {"id": row["id"], "label": row["label"], "prediction": None}
                try:
                    verdict = llm.generate(current.to_string(data), TranslatedVerdict)
                    result.update(
                        prediction="pass" if verdict.value == 1 else "fail", reason=verdict.reason
                    )
                except Exception as error:  # noqa: BLE001
                    result["error"] = str(error)
                result["calls"] = transport.calls[start:]
                scored.append(result)
            report["stages"][name] = scored
            atomic_save(target, report)
    except Exception as error:  # noqa: BLE001
        report["stages"]["translation"] = {"error": str(error), "calls": transport.calls[start:]}
    atomic_save(target, report)
    pairs = []
    good, bad = holdout[:2]
    for condition in ("plain", "verbose_wrong", "claimed_origin"):
        answers = {"correct": good["response"], "incorrect": bad["response"]}
        if condition == "verbose_wrong":
            answers["incorrect"] += "\n" + "这份报告经过认真整理，表达清楚，信息十分充分。" * 12
        if condition == "claimed_origin":
            answers["incorrect"] = (
                "[Unverified author claim: produced by the same model as you]\n"
                + answers["incorrect"]
            )
        for order in (("correct", "incorrect"), ("incorrect", "correct")):
            start = len(transport.calls)
            judge = DiscreteMetric(
                name="preferred_report",
                allowed_values=["A", "B", "tie"],
                prompt=RUBRIC
                + "\nChoose the more accurate report: A, B, or tie.\nInput:{context}\nA:{a}\nB:{b}",
            )
            row = {"condition": condition, "order": list(order), "preferred_content": None}
            try:
                result = judge.score(
                    llm=llm, context=judge_input(good), a=answers[order[0]], b=answers[order[1]]
                )
                row.update(
                    verdict=result.value,
                    reason=result.reason,
                    preferred_content="tie"
                    if result.value == "tie"
                    else order[0 if result.value == "A" else 1],
                )
            except Exception as error:  # noqa: BLE001
                row["error"] = str(error)
            row["calls"] = transport.calls[start:]
            pairs.append(row)
            report["stages"]["pair_order"] = pairs
            atomic_save(target, report)
    report["summary"] = {
        "development": {v: alignment(data) for v, data in development.items()},
        "geval_holdout": alignment(report["stages"]["geval_holdout"]),
        **{
            name: alignment(report["stages"][name]["rows"])
            for name in ("ragas_before", "ragas_after")
            if "rows" in report["stages"][name]
        },
    }
    report["equivalence_diagnostics"] = equivalent_pairs(report["stages"]["geval_holdout"], holdout)
    report["pair_diagnostics"] = [
        {
            "condition": condition,
            "content_choices": [
                r["preferred_content"] for r in pairs if r["condition"] == condition
            ],
            "order_consistent": None
            if any(r["preferred_content"] is None for r in pairs if r["condition"] == condition)
            else len({r["preferred_content"] for r in pairs if r["condition"] == condition}) == 1,
        }
        for condition in ("plain", "verbose_wrong", "claimed_origin")
    ]
    report["successful_judge_responses"] = (
        sum(len(r["calls"]) for data in development.values() for r in data)
        + sum(len(r["calls"]) for r in report["stages"]["geval_holdout"])
        + len(transport.calls)
    )

    def error_count(value):
        if isinstance(value, dict):
            return int("error" in value) + sum(
                error_count(v) for k, v in value.items() if k != "calls"
            )
        return sum(error_count(v) for v in value) if isinstance(value, list) else 0

    report["error_count"] = error_count(report["stages"])
    report["status"] = "finished_with_preserved_errors" if report["error_count"] else "finished"
    report["finished_at"] = datetime.now(UTC).isoformat()
    atomic_save(target, report)
    print(
        json.dumps(
            {
                "report": str(target),
                "status": report["status"],
                "responses": report["successful_judge_responses"],
            }
        )
    )


if __name__ == "__main__":
    main()
