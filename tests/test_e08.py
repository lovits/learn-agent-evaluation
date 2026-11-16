import copy

import pytest

from lessons.e08_datasets.code import build_graph, candidate, seeds
from lessons.e08_datasets.dataset import audit, digest, question_key, structure_errors


def source(name, text):
    return {"id": name, "text": text, "sha256": digest(text)}


@pytest.fixture
def inputs():
    docs = [
        source("auth", "POST /upload uses Token."),
        source("limits", "POST /upload allows 42 bytes."),
    ]
    row = candidate("one", "Which header?", "Token", docs, "test_fixture", "single_hop")
    return docs, {d["id"]: d for d in docs}, row


def support(multi=False):
    return {"supported": True, "requires_multiple_sources": multi, "reason": "fixture, not a model"}


def test_stale_unknown_and_missing_sources_are_not_accepted(inputs):
    _, registry, row = inputs
    assert not structure_errors(row, registry)
    wrong = copy.deepcopy(row)
    wrong["evidence"][0]["sha256"] = "old-version"
    assert "stale_source" in structure_errors(wrong, registry)
    wrong["evidence"][0]["id"] = "unknown"
    assert "unknown_source" in structure_errors(wrong, registry)
    wrong["evidence"] = []
    assert "missing_evidence" in structure_errors(wrong, registry)


def test_duplicate_rejection_preserves_first_candidate_and_reason(inputs):
    _, registry, row = inputs
    duplicate = {**row, "id": "two", "question": " WHICH header!!! "}
    result = audit([row, duplicate], registry, {"one": support(), "two": support()})
    assert result[0]["review_state"] == "pending_human"
    assert result[1]["duplicate_of"] == "one"
    assert result[1]["errors"] == ["duplicate_question"]
    assert question_key("限额为42？") != question_key("限额为43？")


def test_duplicate_across_declared_families_quarantines_both(inputs):
    _, registry, row = inputs
    other = {**row, "id": "other", "family": "file_edit"}
    result = audit([row, other], registry, {"one": support(), "other": support()})
    assert all("cross_family_duplicate" in r["errors"] for r in result)
    assert not any(r["eligible_for_human_review"] for r in result)


def test_two_contexts_alone_do_not_establish_a_multi_hop_question(inputs):
    _, registry, row = inputs
    row["query_type"] = "multi_hop"
    result = audit([row], registry, {"one": support(multi=False)})[0]
    assert "multi_hop_not_established" in result["errors"]
    result = audit([row], registry, {"one": support(multi=True)})[0]
    assert result["review_state"] == "pending_human"


def test_support_rejection_and_missing_review_remain_distinct(inputs):
    _, registry, row = inputs
    rejected = audit([row], registry, {"one": {**support(), "supported": False}})[0]
    missing = audit([row], registry, {})[0]
    assert rejected["errors"] == ["reference_not_supported"]
    assert missing["errors"] == ["automated_review_missing"]
    assert rejected["reference"] == row["reference"]


def test_candidate_cannot_claim_a_generated_agent_response(inputs):
    _, registry, row = inputs
    row["actual_output"] = "claimed completion"
    assert "candidate_is_not_an_executed_run" in structure_errors(row, registry)


def test_rule_graph_uses_real_shared_endpoint_and_native_nodes(inputs):
    docs, _, _ = inputs
    graph = build_graph(docs)
    assert len(graph.nodes) == 2
    assert graph.nodes[0].properties["entities"] == ["POST /upload"]
    assert graph.relationships[0].type == "entities_overlap"
    assert graph.relationships[0].properties["overlapped_items"] == [
        ("POST /upload", "POST /upload")
    ]
    unrelated = source("other", "GET /health returns ready.")
    with pytest.raises(ValueError, match="No shared endpoint"):
        build_graph([docs[0], unrelated])


def test_authored_seed_splits_include_coding_contract_and_missing_information(inputs):
    docs, _, _ = inputs
    rows, extra_sources = seeds(docs)
    assert len(rows) == 3 and len(extra_sources) == 2
    assert any(r["answerable"] is False for r in rows)
    coding = next(r for r in rows if r["family"] == "file_edit")
    assert coding["acceptance_contract"]["expected_stdout"] == "48\n"
    assert all(r["actual_output"] is None and r["origin"] == "authored_seed" for r in rows)
