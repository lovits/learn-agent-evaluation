import json

import numpy as np
import pytest

from lessons.e03_judges.eval import Transport
from lessons.e04_retrieval.code import agent_loop
from lessons.e04_retrieval.eval import ModernJudge
from lessons.e07_failure_diagnosis.code import (
    EXPECTED,
    QUERY,
    diagnose,
    fault_dispatch,
    inspect_artifact,
)


@pytest.mark.parametrize(
    "case_id", ["baseline", "drop_doc", "drop_hit", "add_old", "add_noise", "bad_prompt"]
)
def test_faults_have_distinct_stage_evidence(tmp_path, case_id):
    corpus = tmp_path / "corpus"
    (corpus / "e04").mkdir(parents=True)
    (corpus / "e04/auth.md").write_text("POST upload API token X-Project-Token")
    if case_id != "drop_doc":
        (corpus / "e04/limits.md").write_text("POST upload API size limit 1048576 HTTP 413")
    retrievals = []
    execute = fault_dispatch(case_id, corpus, retrievals)
    call = {"name": "search_knowledge", "arguments_json": json.dumps({"query": QUERY})}
    replies = iter([{"tool_calls": [call], "answer": ""}, {"tool_calls": [], "answer": "done"}])
    record = agent_loop(
        "query", tmp_path, model=lambda m: {"reply": next(replies)}, tool_dispatch=execute
    )
    assert record["status"] == "finished" and len(retrievals) == 1
    before, after = [{d["id"] for d in retrievals[0][k]} for k in ("before", "after")]
    if case_id == "drop_doc":
        assert "e04/limits.md" not in before
    elif case_id == "drop_hit":
        assert "e04/limits.md" in before and "e04/limits.md" not in after
    elif case_id in ("add_old", "add_noise"):
        assert after - before == {f"e07/{case_id}.md"}
    else:
        assert before == after
    denied, result = execute(
        {**call, "arguments_json": '{"query":"different"}'}, tmp_path, lambda n, a: False
    )
    assert denied["decision"] == "not_executed" and result["status"] == "error"


def test_diagnosis_uses_observations_not_injected_fault_label(tmp_path):
    path = tmp_path / "upload_notes.json"
    path.write_text(json.dumps({**EXPECTED, "sources": ["e04/auth.md", "e04/limits.md"]}))
    good = inspect_artifact(tmp_path)
    ids = ["e04/auth.md", "e04/limits.md"]
    assert diagnose(ids, ids, good) == "no_observed_task_failure"
    assert diagnose(ids[:1], ids[:1], good) == "knowledge_gap"
    assert diagnose(ids, ids[:1], good) == "retrieval_gap"
    path.write_text(json.dumps({**EXPECTED, "max_bytes": True, "sources": []}))
    assert diagnose(ids, ids, inspect_artifact(tmp_path)) == "artifact_error"


def test_grading_projection_preserves_endpoint_and_scope_of_missing_values():
    from lessons.e07_failure_diagnosis.eval import REFERENCE, response_text

    text = response_text({**EXPECTED, "max_bytes": None})
    assert "POST /upload" in REFERENCE and "POST /upload" in text
    assert "unknown from the retrieved evidence" in text
    assert "None" not in text and "no maximum" not in text


@pytest.mark.parametrize("mode,expected", [("relevant", 1 / 3), ("irrelevant", 1 / 3)])
def test_native_noise_modes_and_exclusivity(mode, expected):
    from ragas.metrics.collections import NoiseSensitivity

    metric = NoiseSensitivity(llm=ModernJudge(Transport()), mode=mode)
    # Two reference statements, three answer statements, two contexts.
    answers = {
        "retrieved2ground_truth": np.array([[1, 0], [0, 0]], dtype=bool),
        "retrieved2answer": np.array([[1, 0], [1, 1], [0, 1]], dtype=bool),
        "ground_truth2answer": np.array([[1, 0, 0]], dtype=bool),
    }
    assert metric._compute_score(answers) == pytest.approx(expected)
    # The second erroneous claim is supported by both contexts; exclude it from irrelevant.
    assert answers["retrieved2answer"][1].all()
