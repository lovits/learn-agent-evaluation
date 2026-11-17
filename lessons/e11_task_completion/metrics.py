"""The same structured external evidence, adapted to both native metric interfaces."""

import math

from deepeval.metrics import BaseMetric
from pydantic import BaseModel, ConfigDict
from ragas.metrics.collections.base import BaseMetric as RagasBaseMetric
from ragas.metrics.result import MetricResult


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: str
    checks: dict[str, bool] = {}
    error: str | None = None

    def score(self):
        if self.status != "scored" or not self.checks:
            raise ValueError(self.error or "Evidence missing or outside verifier applicability")
        return float(all(self.checks.values()))


def evidence_score(data):
    return Evidence.model_validate(data).score()


class ExternalCompletionMetric(BaseMetric):
    def __init__(self):
        self.threshold, self.async_mode = 1.0, False

    def measure(self, test_case, **kwargs):
        self.score, self.error, self.reason = None, None, None
        try:
            data = (test_case.metadata or {})["external_evidence"]
            self.score = evidence_score(data)
            self.reason = (
                "All required external checks pass" if self.score else "External check failed"
            )
            return self.score
        except (ValueError, KeyError) as error:
            self.error = str(error)
            raise ValueError(self.error) from error

    async def a_measure(self, test_case, **kwargs):
        return self.measure(test_case, **kwargs)

    @property
    def __name__(self):
        return "External code completion"


class RagasExternalCompletion(RagasBaseMetric):
    def __init__(self):
        super().__init__(name="external_code_completion")

    async def ascore(self, evidence):
        value = evidence_score(evidence)
        return MetricResult(value=value, reason="Conjunction of required external checks")


def composite(rule_score, judge_score):
    if any(s is None for s in (rule_score, judge_score)):
        return {"status": "unscored", "score": None}
    if any(not math.isfinite(s) or not 0 <= s <= 1 for s in (rule_score, judge_score)):
        raise ValueError("Scores must be finite and within [0, 1]")
    return {"status": "scored", "score": min(rule_score, judge_score)}
