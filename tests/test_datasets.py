import copy

from course.e03_datasets.code import curate, dataset, load_candidates
from course.e03_datasets.eval import check_dataset
from eval_course.knowledge import PROJECT


def test_review_evidence_and_family_split_are_distinct():
    rows, audit = curate(load_candidates(), PROJECT / "knowledge_base")
    reasons = {r["id"]: r["decision"] for r in audit}
    assert reasons["auth-paraphrase"] == "duplicate_intent"
    assert reasons["pending"] == reasons["bad-reference"] == "not_approved"
    assert reasons["missing-quote"] == "missing_evidence"
    assert reasons["stale-source"] == "source_changed"
    assert reasons["generated-0"] == reasons["generated-2"] == "duplicate_intent"
    assert reasons["generated-1"] == "accepted"
    assert all(check_dataset(rows).values())
    for split in ["development", "holdout"]:
        for golden in dataset(rows, split).goldens:
            assert golden.actual_output is None
            assert golden.expected_output
            assert golden.additional_metadata["split"] == split
    crossed = copy.deepcopy(rows)
    next(r for r in crossed if r["id"] == "size-limit")["split"] = "development"
    assert not check_dataset(crossed)["families_disjoint"]


def test_document_changes_require_new_review(tmp_path):
    row = copy.deepcopy(load_candidates()[0])
    (tmp_path / "course").mkdir()
    (tmp_path / "course/upload.md").write_text("A changed policy")
    rows, audit = curate([row], tmp_path)
    assert not rows and audit[0]["decision"] == "source_changed"
    row["source"]["path"] = "../outside.md"
    assert curate([row], tmp_path)[1][0]["decision"] == "source_unavailable"
