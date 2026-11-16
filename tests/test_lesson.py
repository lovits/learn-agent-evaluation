import asyncio
import hashlib
import json
import shutil

import pytest

from eval_course.data import contexts, get_case
from eval_course.knowledge import PROJECT, document, search
from eval_course.runner import run, save, score_case


@pytest.mark.parametrize(
    "name,expected",
    [
        ("supported", (1, 1, 1)),
        ("unsupported", (1, 0, 0)),
        ("contradicted", (0, 0, 0)),
        ("mixed", (2 / 3, 1 / 3, 1 / 3)),
        ("no_claims", (1, 1, None)),
    ],
)
def test_actual_sdks_replay_known_verdicts(name, expected):
    row = asyncio.run(score_case(get_case(name), root=PROJECT / "knowledge_base"))
    for key, value in zip(("deepeval_default", "deepeval_penalize_ambiguous", "ragas"), expected):
        actual = row["metrics"][key]["score"]
        assert actual is None if value is None else actual == pytest.approx(value)
    schemas = [call["schema"] for call in row["metrics"]["ragas"]["calls"]]
    assert schemas[0] == "StatementGeneratorOutput"
    if name != "no_claims":
        assert schemas[1] == "NLIStatementOutput"


def test_changed_evidence_cannot_reuse_frozen_verdicts(tmp_path):
    shutil.copytree(PROJECT / "knowledge_base", tmp_path / "kb")
    policy = tmp_path / "kb/policies/refund_policy.md"
    policy.write_text(policy.read_text() + "\n所有运费都由商家承担。\n")
    with pytest.raises(ValueError, match="快照与知识库不一致"):
        contexts(get_case("unsupported"), frozen=True, root=tmp_path / "kb")
    current = contexts(get_case("unsupported"), frozen=False, root=tmp_path / "kb")
    assert "所有运费" in current[0]["text"]


def test_knowledge_read_and_search_use_current_mount(tmp_path):
    (tmp_path / "policy.md").write_text("退货运费由商家承担。", encoding="utf-8")
    assert search("退货运费", root=tmp_path)[0]["path"] == "policy.md"
    (tmp_path / "policy.md").write_text("所有退款需审核。", encoding="utf-8")
    assert not search("运费", root=tmp_path)


def test_knowledge_cannot_escape_mount(tmp_path):
    (tmp_path / "escape.md").symlink_to(PROJECT / "README.md")
    with pytest.raises(ValueError, match="挂载目录内"):
        document("escape.md", tmp_path)
    with pytest.raises(ValueError, match="挂载目录内"):
        document("../secret.md", tmp_path)


def test_nan_is_persisted_as_null_with_reason(tmp_path):
    report = run("replay", "no_claims", root=PROJECT / "knowledge_base")
    filename = save(report, tmp_path)
    text = filename.read_text()
    assert "NaN" not in text
    data = json.loads(text)
    metric = data["rows"][0]["metrics"]["ragas"]
    assert metric["score"] is None
    assert metric["status"] == "not_scored"
    assert metric["not_scored_reason"]
    assert data["mode"] == "replay"


def test_reference_files_match_fixed_snapshot_manifest():
    rows = json.loads((PROJECT / "references/sources.json").read_text())
    for row in rows:
        assert hashlib.sha256((PROJECT / row["path"]).read_bytes()).hexdigest() == row["sha256"]


def test_invalid_mode_does_not_silently_fall_back_to_replay():
    with pytest.raises(ValueError, match="mode"):
        run("not-live")
