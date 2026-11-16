import asyncio

import numpy as np
import pytest

from lessons.e03_judges.eval import Transport
from lessons.e04_retrieval.eval import ModernJudge
from lessons.e06_answer_quality.code import combine, cosine, factual_from_verdicts, fbeta


@pytest.mark.parametrize("mode", ["precision", "recall", "f1"])
def test_native_factual_modes_match_same_verdict_explanation(mode):
    from ragas.metrics.collections import FactualCorrectness

    metric = FactualCorrectness(llm=ModernJudge(Transport()), mode=mode)
    directions = iter([[True], [True, False, False]])

    async def fixed_verdicts(text, reference):
        return np.array(next(directions), dtype=bool)

    metric._decompose_and_verify_claims = fixed_verdicts
    result = asyncio.run(metric.ascore(response="partial", reference="three facts"))
    assert result.value == factual_from_verdicts([1], [1, 0, 0])[mode]


def test_native_factual_recall_is_not_simple_reverse_coverage():
    from ragas.metrics.collections import FactualCorrectness

    metric = FactualCorrectness(llm=ModernJudge(Transport()), mode="recall")
    directions = iter([[True, True, True], [True, False]])

    async def fixed_verdicts(text, reference):
        return np.array(next(directions), dtype=bool)

    metric._decompose_and_verify_claims = fixed_verdicts
    assert asyncio.run(metric.ascore(response="three facts", reference="two clauses")).value == 0.75
    assert factual_from_verdicts([1, 1, 1], [1, 0])["recall"] == 0.75


def test_answer_correctness_empty_side_and_embedding_requirement():
    from ragas.metrics.collections import AnswerCorrectness

    with pytest.raises(ValueError, match="Embeddings are required"):
        AnswerCorrectness(llm=ModernJudge(Transport()))
    metric = AnswerCorrectness(llm=ModernJudge(Transport()), weights=[1.0, 0.0])

    async def empty_on_response(question, text):
        return [] if text == "Thanks" else ["a fact"]

    metric._generate_statements = empty_on_response
    assert (
        asyncio.run(metric.ascore(user_input="q", response="Thanks", reference="fact")).value == 1
    )


def test_hand_calculations_and_zero_vector_boundary():
    assert fbeta(1, 0, 2) == 0.5
    assert fbeta(1, 0, 2, 2) == pytest.approx(5 / 13)
    assert cosine([1, 0], [0.8, 0.6]) == pytest.approx(0.8)
    assert combine(0.5, 0.8) == pytest.approx(0.575)
    with pytest.raises(ValueError, match="zero vector"):
        cosine([0, 0], [1, 0])
    with pytest.raises(ValueError):
        combine(0.5, 0.8, (0, 0))
    with pytest.raises(ValueError):
        factual_from_verdicts([True], [1])
