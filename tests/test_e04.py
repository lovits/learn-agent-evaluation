import json

import pytest

from eval_course.knowledge import document
from lessons.e04_retrieval.code import dispatch, search_knowledge
from lessons.e04_retrieval.eval import ranking


def test_order_matters_while_precision_and_recall_stay():
    good = ranking(["a", "b", "x"], ["a", "b"])
    late = ranking(["x", "a", "b"], ["a", "b"])
    assert good["precision"] == late["precision"] == pytest.approx(2 / 3)
    assert good["recall"] == late["recall"] == 1
    assert good["ap_retrieved"] == 1 and late["ap_retrieved"] == pytest.approx(7 / 12)
    assert good["ndcg"] > late["ndcg"]


def test_all_relevant_does_not_mean_complete():
    result = ranking(["a"], ["a", "b"])
    assert result["precision"] == result["ap_retrieved"] == 1
    assert result["recall"] == result["ap_reference"] == 0.5
    assert ranking([], ["a"])["recall"] == 0
    with pytest.raises(ValueError):
        ranking(["a"], [])
    assert ranking(["a", "a"], ["a", "b"]) == result


def test_mount_changes_are_read_without_rebuilding(tmp_path):
    p = tmp_path / "api.md"
    p.write_text("upload limit 10")
    first = search_knowledge("upload", tmp_path)[0]
    p.write_text("upload limit 20")
    second = search_knowledge("upload", tmp_path)[0]
    assert first["sha256"] != second["sha256"] and "20" in second["text"]
    assert search_knowledge("unfindable", tmp_path) == []


def test_knowledge_link_cannot_escape(tmp_path):
    outside = tmp_path.parent / "outside-e04.txt"
    outside.write_text("private")
    (tmp_path / "link.md").symlink_to(outside)
    with pytest.raises(ValueError):
        document("link.md", tmp_path)
    with pytest.raises(ValueError):
        document("../outside-e04.txt", tmp_path)


def test_tool_search_validation_and_trace_loop(tmp_path, monkeypatch):
    from lessons.e04_retrieval.code import agent_loop

    monkeypatch.setenv("KNOWLEDGE_DIR", str(tmp_path))
    (tmp_path / "api.md").write_text("upload max 10")
    call = {"name": "search_knowledge", "arguments_json": json.dumps({"query": "upload"})}
    _, result = dispatch(call, tmp_path)
    assert result["status"] == "ok" and result["hits"][0]["id"] == "api.md"
    replies = iter([{"tool_calls": [call], "answer": ""}, {"tool_calls": [], "answer": "max 10"}])
    record = agent_loop("find upload max", tmp_path, model=lambda m: {"reply": next(replies)})
    from lessons.e02_tools_traces.samples import trace_errors

    assert record["status"] == "finished" and not trace_errors(record)
    _, bad = dispatch({"name": "search_knowledge", "arguments_json": "{}"}, tmp_path)
    assert bad["status"] == "error"


def test_native_metric_payloads_have_different_verdict_shapes():
    from deepeval.metrics import ContextualPrecisionMetric, ContextualRelevancyMetric
    from deepeval.metrics.contextual_precision.schema import ContextualPrecisionVerdict
    from deepeval.metrics.contextual_relevancy.schema import (
        ContextualRelevancyVerdict,
        ContextualRelevancyVerdicts,
    )

    from lessons.e03_judges.eval import DeepJudge, Transport

    precision = ContextualPrecisionMetric(
        model=DeepJudge(Transport()), async_mode=False, include_reason=False
    )
    precision.verdicts = [ContextualPrecisionVerdict(verdict="yes", reason="ok")]
    relevance = ContextualRelevancyMetric(
        model=DeepJudge(Transport()), async_mode=False, include_reason=False
    )
    relevance.verdicts_list = [
        ContextualRelevancyVerdicts(
            verdicts=[ContextualRelevancyVerdict(statement="a", verdict="yes", reason="ok")]
        )
    ]
    assert precision._calculate_score() == 1 and relevance._calculate_score() == 1


def test_search_prompt_does_not_inherit_fault_injection(monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "tools"))
    import model_bridge

    assert "deliberate fault injection" not in model_bridge.E04_INSTRUCTION
    e04_names = model_bridge.E04_SCHEMA["properties"]["tool_calls"]["items"]["properties"]["name"][
        "enum"
    ]
    e02_names = model_bridge.E02_SCHEMA["properties"]["tool_calls"]["items"]["properties"]["name"][
        "enum"
    ]
    assert "search_knowledge" in e04_names and "search_knowledge" not in e02_names
