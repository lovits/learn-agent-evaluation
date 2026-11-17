import copy

import pytest

from course.e10_rag_diagnosis.code import prepare, replay
from course.e10_rag_diagnosis.eval import first_gap, noise_fraction
from eval_course.knowledge import PROJECT


def test_first_gap_distinguishes_source_version_retrieval_and_assembly():
    source = {"path": "release", "sha256": "current"}
    docs, hits = [source], [{"path": "release"}]
    assert first_gap([], hits, hits, source) == "source_missing"
    assert first_gap([{"path": "release", "sha256": "old"}], hits, hits, source) == "source_version"
    assert first_gap(docs, [], [], source) == "retrieval_output"
    assert first_gap(docs, hits, [], source) == "context_assembly"
    assert first_gap(docs, hits, hits, source) is None


def test_controlled_changes_keep_raw_candidates_and_actual_context_distinct(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_DIR", str(PROJECT / "knowledge_base"))
    spec, _trace, rows = prepare()
    assert rows["baseline"]["first_evidence_gap"] is None
    for key, expected in [
        ("source_missing", "source_missing"),
        ("retrieval_miss", "retrieval_output"),
        ("assembly_drop", "context_assembly"),
        ("stale_source", "source_version"),
    ]:
        assert rows[key]["first_evidence_gap"] == expected
    assert any(p["path"] == spec["source"]["path"] for p in rows["retrieval_miss"]["native_hits"])
    assert rows["baseline"]["knowledge_version"] == rows["noise"]["knowledge_version"]
    assert len(rows["noise"]["contexts"]) == len(rows["baseline"]["contexts"]) + 1


def test_noise_fraction_uses_all_statements_and_exclusive_irrelevant_support():
    result = noise_fraction([True, False, False], [True, True, False], [False, True, True])
    assert result["relevant"] == result["irrelevant"] == pytest.approx(1 / 3)
    assert noise_fraction([], [], []) == {"relevant": None, "irrelevant": None}
    with pytest.raises(ValueError):
        noise_fraction([True], [], [])


def test_replay_replaces_evidence_without_mutating_the_original_trace(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_DIR", str(PROJECT / "knowledge_base"))
    spec, trace, rows = prepare()
    before = copy.deepcopy(trace)
    calls = []

    def model(messages, tools=None):
        calls.append((messages, tools))
        return {"reply": {"answer": "Controlled reply", "tool_calls": []}}

    monkeypatch.setattr("course.e10_rag_diagnosis.code.call_model", model)
    sample = replay(rows["assembly_drop"], trace, spec["policy"])
    assert trace == before
    assert calls[0][1] == {}
    assert sample.retrieval_context == rows["assembly_drop"]["contexts"]
    assert not any("python -m pytest" in text for text in sample.retrieval_context)
