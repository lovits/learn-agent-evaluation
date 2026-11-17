import pytest

from course.e15_version_comparison.eval import compare, usage_summary


def test_pair_identity_keeps_errors_and_repeats_out_of_independent_sample_count():
    cases = [
        {"id": "a", "family": "A", "stratum": "cross"},
        {"id": "b", "family": "B", "stratum": "single"},
    ]
    rows = [
        {"case_id": c["id"], "repeat": i, "version": v, "quality": q}
        for c, i, v, q in [
            (cases[0], 0, "baseline", 0),
            (cases[1], 0, "candidate", 0),
            (cases[0], 0, "candidate", 1),
            (cases[1], 0, "baseline", 1),
            (cases[0], 1, "baseline", 0),
            (cases[0], 1, "candidate", 1),
            (cases[1], 1, "baseline", 1),
            (cases[1], 1, "candidate", None),
        ]
    ]
    result = compare(rows, cases)
    assert result["valid_pairs"] == 3 and result["pair_coverage"] == 0.75
    assert result["family_deltas"] == {"A": 1, "B": -1}
    assert result["family_weighted_delta"] == 0
    assert result["family_bootstrap_95_percentile"] == [-1, 1]
    assert result["stratum_deltas"] == {"cross": 1, "single": -1}
    with pytest.raises(ValueError, match="Duplicate"):
        compare(rows + rows[:1], cases)
    assert compare([], cases)["family_weighted_delta"] is None


def test_usage_excludes_controlled_steps_and_unknown_tokens_are_not_free():
    assert usage_summary([{"reply": {}}])["input_tokens"] is None
    result = usage_summary(
        [
            {"reply": {}},
            {
                "model": {
                    "usage": [{"input_tokens": 100, "output_tokens": 10, "cached_input_tokens": 20}]
                }
            },
        ]
    )
    assert result["model_calls"] == 1
    assert result["input_tokens"] == 100 and result["output_tokens"] == 10
    assert result["usd"] is None
    assert usage_summary([{"model": {"usage": []}}])["input_tokens"] is None
