"""Review candidates, keep their sources, and split by a reviewed task family."""

import json
import uuid
from pathlib import Path

from deepeval.dataset import EvaluationDataset, Golden

from eval_course.knowledge import document
from eval_course.records import save

HOLDOUT_FAMILIES = {"upload-size"}


def curate(candidates, root=None):
    rows, audit, seen = [], [], set()
    for candidate in candidates:
        reason = "accepted"
        review = candidate["review"]
        key = (candidate["family"], candidate["intent"])
        if review["decision"] != "accept" or not review.get("reviewer"):
            reason = "not_approved"
        else:
            source = candidate["source"]
            try:
                doc = document(source["path"], root)
            except (OSError, ValueError):
                doc = None
            if doc is None:
                reason = "source_unavailable"
            elif doc["sha256"] != source["sha256"]:
                reason = "source_changed"
            elif candidate["answerable"] and (
                not candidate["quote"] or candidate["quote"] not in doc["text"]
            ):
                reason = "missing_evidence"
            elif key in seen:
                reason = "duplicate_intent"
            else:
                seen.add(key)
                rows.append(
                    {
                        **candidate,
                        "context": doc["text"],
                        "split": (
                            "holdout" if candidate["family"] in HOLDOUT_FAMILIES else "development"
                        ),
                    }
                )
        audit.append({"id": candidate["id"], "decision": reason})
    return rows, audit


def dataset(rows, split):
    return EvaluationDataset(
        goldens=[
            Golden(
                input=row["task"],
                expected_output=row["reference"],
                context=[row["context"]],
                source_file=row["source"]["path"],
                additional_metadata={
                    k: row[k] for k in ["id", "family", "intent", "category", "split", "source"]
                },
            )
            for row in rows
            if row["split"] == split
        ]
    )


def load_candidates():
    return [
        json.loads(line)
        for line in Path(__file__).with_name("cases.jsonl").read_text().splitlines()
    ]


def main():
    from .eval import check_dataset

    rows, audit = curate(load_candidates())
    report = {
        "run_id": uuid.uuid4().hex,
        "kind": "dataset_audit",
        "audit": audit,
        "checks": check_dataset(rows),
        "datasets": {
            split: [golden.model_dump(mode="json") for golden in dataset(rows, split).goldens]
            for split in ["development", "holdout"]
        },
    }
    path = save(report, prefix="e03-suite")
    print(json.dumps({"path": str(path), "checks": report["checks"]}, ensure_ascii=False))
    return 0 if all(report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
