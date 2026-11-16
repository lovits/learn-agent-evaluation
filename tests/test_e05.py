import math

import pytest

from lessons.e05_faithfulness.code import (
    deep_aggregate,
    evidence_key,
    ragas_aggregate,
    require_same_evidence,
)


@pytest.mark.parametrize(
    "values,default,penalized",
    [([], 1, 1), (["yes", "borderline", "no"], 2 / 3, 1 / 3), (["no"], 0, 0)],
)
def test_deep_matches_native_aggregation(values, default, penalized):
    from deepeval.metrics import FaithfulnessMetric
    from deepeval.metrics.faithfulness.schema import FaithfulnessVerdict

    from lessons.e03_judges.eval import DeepJudge, Transport

    metric = FaithfulnessMetric(model=DeepJudge(Transport()), async_mode=False)
    metric.verdicts = [FaithfulnessVerdict(verdict=v, reason="fixture") for v in values]
    assert (
        metric._calculate_score() == pytest.approx(default) == pytest.approx(deep_aggregate(values))
    )
    metric.penalize_ambiguous_claims = True
    assert metric._calculate_score() == pytest.approx(penalized)
    assert deep_aggregate(values, True) == pytest.approx(penalized)


@pytest.mark.parametrize("values,expected", [([], None), ([1, 0, 0], 1 / 3), ([1], 1)])
def test_ragas_aggregation(values, expected):
    assert ragas_aggregate(values) == expected
    with pytest.raises(ValueError):
        ragas_aggregate([True])


def test_stale_annotations_rejected():
    original = [{"id": "same.md", "sha256": "old"}]
    assert require_same_evidence(evidence_key(original), original) is None
    with pytest.raises(ValueError):
        require_same_evidence(evidence_key(original), [{"id": "same.md", "sha256": "new"}])


def test_empty_native_ragas_is_nan_and_blank_input_rejected():
    import asyncio

    from ragas.metrics.collections import Faithfulness

    from lessons.e03_judges.eval import Transport
    from lessons.e04_retrieval.eval import ModernJudge

    metric = Faithfulness(llm=ModernJudge(Transport()))

    class Empty:
        statements = ()

    assert math.isnan(metric._compute_score(Empty()))
    with pytest.raises(ValueError):
        asyncio.run(metric.ascore(user_input="q", response="", retrieved_contexts=["x"]))
