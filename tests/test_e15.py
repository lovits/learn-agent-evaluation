import asyncio
import copy
import json

import pytest

from lessons.e15_calibration.code import (
    alignment,
    equivalent_pairs,
    judge_input,
    make_cases,
    select_version,
    validate_cases,
)
from lessons.e15_calibration.eval import (
    ReportPrompt,
    StructuredJudge,
    TranslatedVerdict,
    metric,
    ragas_dataset,
)


def test_family_split_rejects_paraphrase_leakage_and_duplicate_ids():
    rows = make_cases()
    validate_cases(rows)
    changed = copy.deepcopy(rows)
    changed[-1]["family"] = rows[0]["family"]
    with pytest.raises(ValueError, match="Family leakage"):
        validate_cases(changed)
    with pytest.raises(ValueError, match="Duplicate"):
        validate_cases([*rows, rows[0]])


def test_contract_labels_and_unreviewed_provenance_are_explicit():
    rows = make_cases()
    assert len(rows) == 16
    assert all(not row["human_reviewed"] for row in rows)
    bad = copy.deepcopy(rows)
    bad[0]["label"] = "fail"
    with pytest.raises(ValueError, match="Label contradicts"):
        validate_cases(bad)
    honest_failure = next(r for r in rows if r["id"] == "inventory_correct")
    assert honest_failure["label"] == "pass"
    assert not honest_failure["evidence"]["verification_passed"]


def test_judge_input_excludes_reference_label_and_split_metadata():
    text = judge_input(make_cases()[0])
    for key in ("label_source", "reported_fields", "human_reviewed", "split"):
        assert key not in text
    assert '"expected_value": 48' in text


def test_errors_remain_paired_and_separate_from_false_rejections():
    rows = [
        {"id": "a", "label": "pass", "prediction": None},
        {"id": "b", "label": "fail", "prediction": "pass"},
        {"id": "c", "label": "pass", "prediction": "pass"},
    ]
    result = alignment(rows)
    assert result["coverage"] == 2 / 3
    assert result["false_pass"] == 1 and result["false_reject"] == 0
    assert result["agreement"] == 0.5 and result["disagreements"] == ["b"]
    with pytest.raises(ValueError, match="unique paired"):
        alignment([rows[0], rows[0]])


def test_kappa_degenerate_and_empty_are_null_not_nan():
    result = alignment([{"id": "a", "label": "pass", "prediction": "pass"}])
    assert result["agreement"] == 1 and result["kappa"] is None
    assert alignment([])["agreement"] is None
    json.dumps(result, allow_nan=False)


def test_development_selection_never_prefers_an_unscored_candidate():
    correct = [{"id": "a", "label": "pass", "prediction": "pass"}]
    missing = [{"id": "a", "label": "pass", "prediction": None}]
    assert select_version({"v1": correct, "v2": correct}) == "v2"
    assert select_version({"v1": correct, "v2": missing}) == "v1"
    with pytest.raises(ValueError, match="No fully scored"):
        select_version({"v1": missing, "v2": missing})


class FixtureLLM:
    """Deterministic callback, never a provider response."""

    def __init__(self):
        self.prompts = []

    def generate(self, prompt, response_model):
        self.prompts.append(prompt)
        return response_model(value="pass", reason="fixture")


def test_native_ragas_alignment_recent_examples_and_validation_pairing():
    rows = make_cases()
    judge = metric()
    judge.align(ragas_dataset(rows[:4], "train"), embedding_model=None, max_similar_examples=4)
    assert judge.prompt.example_store.embedding_model is None
    assert len(judge.prompt.example_store._examples) == 4
    llm = FixtureLLM()
    result = judge.validate_alignment(llm, ragas_dataset(rows[8:], "heldout"))
    assert result["agreement_rate"] == 0.75
    assert result["correlation"] == 0
    assert len(result["df"]) == 8
    assert len(llm.prompts) == 8


def test_native_align_legacy_embedding_wrapper_mismatch_is_exposed():
    class Legacy:
        def embed_query(self, text):
            return [1.0, 0.0]

    with pytest.raises(AttributeError, match="embed_query"):
        metric().align(ragas_dataset(make_cases()[:4], "train"), embedding_model=Legacy())


def test_native_empty_examples_changes_language_without_translation():
    class NoCalls:
        async def agenerate(self, *args):
            raise AssertionError("Native empty-example path must not call a model")

    prompt = ReportPrompt([])
    adapted = asyncio.run(prompt.adapt("chinese", NoCalls(), adapt_instruction=True))
    assert adapted.language == "chinese" and adapted.instruction == prompt.instruction


def test_native_translation_rejects_wrong_statement_count():
    class WrongCount:
        async def agenerate(self, prompt, response_model):
            return response_model(statements=[])

    with pytest.raises(ValueError, match="expected"):
        asyncio.run(ReportPrompt(make_cases()[:2]).adapt("chinese", WrongCount(), True))


def test_numeric_verdict_and_evidence_survive_native_adaptation():
    class IdentityTranslation:
        async def agenerate(self, prompt, response_model):
            statements = json.loads(prompt.split("Statements to translate:\n", 1)[1])
            return response_model(statements=statements)

    prompt = ReportPrompt(make_cases()[:2])
    adapted = asyncio.run(prompt.adapt("chinese", IdentityTranslation(), True))
    assert adapted.examples == prompt.examples
    assert adapted.output_model is TranslatedVerdict
    assert adapted.input_model.model_json_schema() == prompt.input_model.model_json_schema()


def test_structured_adapter_validates_native_categorical_schema():
    class Transport:
        def ask(self, prompt):
            return '{"reason":"fixture","value":2}'

    with pytest.raises(ValueError):
        StructuredJudge(Transport()).generate("test", TranslatedVerdict)


def test_equivalence_join_uses_ids_and_keeps_missing_variant_unscored():
    cases = make_cases()[8:]
    predictions = [
        {"id": "refund_correct", "prediction": "pass"},
        {"id": "refund_correct_long", "prediction": "fail"},
    ]
    diagnostics = equivalent_pairs(predictions, cases)
    assert diagnostics[0]["flipped"] is True
    assert diagnostics[1]["flipped"] is None
