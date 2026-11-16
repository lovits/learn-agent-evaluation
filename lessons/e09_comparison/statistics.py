"""Paired summaries; repeats stay inside tasks, and tasks stay inside families."""

import random
from collections import defaultdict
from statistics import mean


def paired_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["case_id"], row["k"]].append(row)
    ids = sorted({r["case_id"] for r in rows})
    result = []
    for identifier in ids:
        left, right = grouped[identifier, 1], grouped[identifier, 2]
        if not left or not right or {r["repeat"] for r in left} != {r["repeat"] for r in right}:
            raise ValueError("Missing matched case/version/repeat")
        if len({r["repeat"] for r in left}) != len(left) or len(
            {r["repeat"] for r in right}
        ) != len(right):
            raise ValueError("Duplicate case/version/repeat")
        result.append(
            {
                "case_id": identifier,
                "family": left[0]["family"],
                "stratum": left[0]["stratum"],
                "baseline": mean(r["passed"] for r in left),
                "candidate": mean(r["passed"] for r in right),
                "delta": mean(r["passed"] for r in right) - mean(r["passed"] for r in left),
                "latency_delta_seconds": mean(r["elapsed_seconds"] for r in right)
                - mean(r["elapsed_seconds"] for r in left),
                "application_requests_delta": mean(r["application_requests"] for r in right)
                - mean(r["application_requests"] for r in left),
                "repeats_per_version": len(left),
            }
        )
    return result


def family_bootstrap(pairs, seed=9, resamples=2000):
    if not pairs:
        raise ValueError("Cannot bootstrap an empty comparison")
    groups = defaultdict(list)
    for row in pairs:
        groups[row["family"]].append(row["delta"])
    values = [mean(v) for v in groups.values()]
    if len(values) < 2:
        return {
            "low": None,
            "high": None,
            "families": len(values),
            "reason": "fewer than two independent family units",
        }
    rng = random.Random(seed)
    draws = sorted(mean(rng.choices(values, k=len(values))) for _ in range(resamples))
    return {
        "low": draws[int(0.025 * (resamples - 1))],
        "high": draws[int(0.975 * (resamples - 1))],
        "families": len(values),
        "method": "percentile family-cluster bootstrap",
        "seed": seed,
        "resamples": resamples,
        "scope": "teaching illustration; two public synthetic families do not support population claims",
    }


def summarize(rows):
    pairs = paired_rows(rows)
    strata = defaultdict(list)
    for row in pairs:
        strata[row["stratum"]].append(row["delta"])
    return {
        "pairs": pairs,
        "mean_task_delta": mean(r["delta"] for r in pairs),
        "strata_delta": {k: mean(v) for k, v in strata.items()},
        "family_bootstrap": family_bootstrap(pairs),
        "failure_rate": {
            str(k): 1 - mean(r["passed"] for r in rows if r["k"] == k) for k in (1, 2)
        },
    }


def choose(development, minimum_effect=0.1):
    summary = summarize(development)
    adopt = summary["mean_task_delta"] >= minimum_effect and all(
        v >= 0 for v in summary["strata_delta"].values()
    )
    return {
        "selected_k": 2 if adopt else 1,
        "minimum_effect": minimum_effect,
        "rule": "development task success delta >= minimum_effect; no observed stratum regression; otherwise prefer baseline",
        "development_summary": summary,
        "holdout_used_for_selection": False,
    }
