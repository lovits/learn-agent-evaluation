import asyncio
import json

import pytest

from lessons.e09_comparison.code import inspect, limited_dispatch, run_phase
from lessons.e09_comparison.statistics import choose, family_bootstrap, paired_rows


def row(identifier, family, stratum, k, repeat, passed):
    return {
        "case_id": identifier,
        "family": family,
        "stratum": stratum,
        "k": k,
        "repeat": repeat,
        "passed": passed,
        "elapsed_seconds": 2,
        "application_requests": 3,
    }


def test_repeats_stay_inside_matched_tasks_and_bootstrap_families():
    rows = [
        row("a", "one", "single", k, repeat, k == 2 and repeat == 1)
        for repeat in range(2)
        for k in (1, 2)
    ]
    pairs = paired_rows(rows)
    assert len(pairs) == 1 and pairs[0]["delta"] == 0.5
    interval = family_bootstrap(pairs)
    assert interval["families"] == 1 and interval["low"] is None
    pairs += [dict(pairs[0], case_id="b", family="two", delta=-0.5)]
    assert family_bootstrap(pairs) == family_bootstrap(pairs)
    assert family_bootstrap(pairs)["families"] == 2


@pytest.mark.parametrize("mode", ["missing", "duplicate"])
def test_incomplete_or_duplicate_pairs_are_rejected(mode):
    rows = [row("a", "one", "single", k, 0, True) for k in (1, 2)]
    if mode == "missing":
        rows.pop()
    else:
        rows.append(rows[0])
    with pytest.raises(ValueError):
        paired_rows(rows)


def test_positive_average_does_not_hide_a_stratum_regression():
    rows = []
    for i in range(4):
        for k in (1, 2):
            rows.append(
                row(
                    str(i),
                    str(i),
                    "common" if i < 3 else "critical",
                    k,
                    0,
                    (k == 2) if i < 3 else (k == 1),
                )
            )
    decision = choose(rows)
    assert decision["development_summary"]["mean_task_delta"] == 0.5
    assert decision["selected_k"] == 1
    assert decision["holdout_used_for_selection"] is False


@pytest.mark.parametrize("value", [True, 1.0])
def test_artifact_numeric_types_and_sources_are_checked(tmp_path, value):
    case = {"expected": {"max_bytes": 1}}
    path = tmp_path / "answer.json"
    path.write_text(json.dumps({"max_bytes": value, "sources": ["auth.md"]}))
    assert inspect(tmp_path, case, {"auth.md"})["passed"] is False
    path.write_text(json.dumps({"max_bytes": 1, "sources": ["invented.md"]}))
    assert inspect(tmp_path, case, {"auth.md"})["valid"] is False


def test_native_ragas_omitted_exception_is_detected():
    def broken(*args):
        raise RuntimeError("injected trial error")

    with pytest.raises(RuntimeError, match="omitted"):
        asyncio.run(run_phase([{"id": "a"}], repeats=1, runner=broken))


def test_k_changes_hit_count_and_rejects_query_changes(tmp_path):
    (tmp_path / "auth.md").write_text("POST upload API token")
    (tmp_path / "limits.md").write_text("POST upload API size limit")
    case = {"query": "POST upload API token size limit"}
    call = {"name": "search_knowledge", "arguments_json": json.dumps({"query": case["query"]})}
    snapshots = []
    for k in (1, 2):
        _, result = limited_dispatch(case, k, tmp_path, snapshots)(call, tmp_path, None)
        assert len(result["hits"]) == k
    call["arguments_json"] = json.dumps({"query": "different"})
    _, result = limited_dispatch(case, 2, tmp_path, snapshots)(call, tmp_path, None)
    assert result["status"] == "error"


def test_trial_preserves_version_labels_in_the_native_deepeval_sample(tmp_path, monkeypatch):
    from lessons.e09_comparison import code

    kb = tmp_path / "knowledge"
    kb.mkdir()
    (kb / "limits.md").write_text("The maximum is 1 byte.")
    monkeypatch.setenv("KNOWLEDGE_DIR", str(kb))
    monkeypatch.setenv("WORKSPACES_DIR", str(tmp_path / "workspaces"))
    case = {
        "id": "fixture",
        "family": "one",
        "split": "development",
        "stratum": "single",
        "task": "Write the maximum.",
        "expected": {"max_bytes": 1},
        "query": "maximum",
        "knowledge_paths": ["limits.md"],
    }
    calls = [
        {"name": "search_knowledge", "arguments_json": json.dumps({"query": "maximum"})},
        {
            "name": "write_file",
            "arguments_json": json.dumps(
                {
                    "path": "answer.json",
                    "content": json.dumps({"max_bytes": 1, "sources": ["limits.md"]}),
                }
            ),
        },
        {"name": "read_file", "arguments_json": json.dumps({"path": "answer.json"})},
    ]
    responses = iter(
        [{"reply": {"answer": "", "tool_calls": [call]}} for call in calls]
        + [{"reply": {"answer": "done", "tool_calls": []}}]
    )
    monkeypatch.setattr(code, "call_model", lambda messages: next(responses))
    result = code.execute_trial(case, 2, 1, 0)
    assert result["passed"] is True and result["application_requests"] == 4
    assert result["deepeval_sample"]["metadata"] == {
        "case_id": "fixture",
        "k": 2,
        "repeat": 1,
        "run_id": result["run_id"],
    }
    assert json.loads(result["deepeval_sample"]["actual_output"])["max_bytes"] == 1


def test_usage_keeps_cache_separate_and_missing_totals_unknown():
    from lessons.e09_comparison.eval import resources

    rows = [
        dict(
            row("a", "one", "single", 1, 0, True),
            events=[
                {
                    "type": "model",
                    "model": {
                        "usage": [
                            {"input_tokens": 100, "output_tokens": 20, "cached_input_tokens": 60}
                        ]
                    },
                }
            ],
        ),
        dict(row("a", "one", "single", 2, 0, True), events=[{"type": "model", "model": {}}]),
    ]
    result = resources(rows)
    assert result["1"]["reported_token_fields"]["input_tokens"]["sum"] == 100
    assert result["1"]["reported_token_fields"]["cached_input_tokens"]["sum"] == 60
    assert result["2"]["reported_token_fields"]["input_tokens"]["sum"] is None
    assert result["2"]["responses_without_usage"] == 1
