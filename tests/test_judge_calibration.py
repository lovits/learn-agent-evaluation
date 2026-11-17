import json

from course.e14_judge_calibration.eval import (
    development_examples,
    reconcile,
    revised_metric,
    sample_for,
    summarize,
)
from eval_course.judge import JudgeModel
from eval_course.knowledge import PROJECT


def cases():
    return [
        json.loads(line)
        for line in (PROJECT / "course/e14_judge_calibration/cases.jsonl").read_text().splitlines()
    ]


def test_disagreement_requires_adjudication_not_a_forced_vote():
    assert reconcile(True, True) is True
    assert reconcile(False, False) is False
    assert reconcile(True, False) is None
    assert reconcile(True, False, False) is False
    assert reconcile(None, True) is None


def test_confusion_denominators_keep_errors_and_unlabelled_coverage_visible():
    rows = [
        {
            "case": {"reference_label": reference, "human_label": None},
            "result": {"status": status, "passed": predicted},
        }
        for reference, predicted, status in [
            (True, True, "ok"),
            (False, False, "ok"),
            (False, True, "ok"),
            (True, False, "ok"),
            (True, None, "error"),
            (None, True, "ok"),
        ]
    ]
    result = summarize(rows)
    assert [result[k] for k in ["tp", "fp", "tn", "fn"]] == [1, 1, 1, 1]
    assert result["agreement"] == 0.5
    assert result["false_accept_rate"] == 0.5
    assert result["false_reject_rate"] == 0.5
    assert result["evaluation_coverage"] == 4 / 5
    assert result["reference_label_coverage"] == 5 / 6
    assert result["human_label_coverage"] == 0
    assert summarize([])["agreement"] is None


def test_few_shots_use_only_development_families_and_samples_hide_labels():
    data = cases()
    dev = {c["family"] for c in data if c["split"] == "dev"}
    held = {c["family"] for c in data if c["split"] == "holdout"}
    assert not dev & held
    examples = development_examples(data)
    assert len(examples) == 2
    assert all("Atlas" in e["input"] for e in examples)
    metric = revised_metric(JudgeModel(), examples)
    assert metric.threshold == 1
    assert metric.score_range == (0, 1)
    assert all(r.model_dump() for r in metric.rubric)
    prompt = "\n".join(metric.evaluation_steps)
    assert "Boreal" not in prompt and "Cedar" not in prompt
    assert "reference_label" not in sample_for(data[0]).model_dump()
