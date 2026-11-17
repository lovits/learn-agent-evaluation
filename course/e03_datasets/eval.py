"""Check this teaching dataset's coverage and leakage; do not score the Agent."""


def check_dataset(rows):
    families = {
        split: {row["family"] for row in rows if row["split"] == split}
        for split in ["development", "holdout"]
    }
    return {
        "unique_ids": len({r["id"] for r in rows}) == len(rows),
        "unique_intents": len({(r["family"], r["intent"]) for r in rows}) == len(rows),
        "both_splits_present": all(families.values()),
        "families_disjoint": not families["development"] & families["holdout"],
        "coverage": {r["category"] for r in rows}
        >= {"normal", "error", "boundary", "insufficient"},
    }
