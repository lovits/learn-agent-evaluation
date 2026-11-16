"""Validate the lesson's course-authored fixtures before a replay."""

import json

from .knowledge import PROJECT, document

FIXTURES = PROJECT / "s07_faithfulness" / "fixtures.json"
LABELS = {"supported", "unsupported", "contradicted"}


def load_cases() -> list[dict]:
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    ids = set()
    for case in cases:
        if case["id"] in ids or not case["question"] or not case["answer"]:
            raise ValueError("样本 ID 必须唯一，问题和回答不能为空。")
        ids.add(case["id"])
        for claim in case["claims"]:
            if claim["label"] not in LABELS or not claim["text"] or not claim["reason"]:
                raise ValueError(f"样本 {case['id']} 存在无效教学标注。")
    return cases


def get_case(case_id: str) -> dict:
    for case in load_cases():
        if case["id"] == case_id:
            return case
    raise ValueError(f"未知样本：{case_id}")


def contexts(case: dict, *, frozen: bool, root=None) -> list[dict]:
    docs = [document(item["path"], root) for item in case["contexts"]]
    if frozen:
        for expected, actual in zip(case["contexts"], docs):
            if expected["sha256"] != actual["sha256"]:
                raise ValueError(
                    f"回放快照与知识库不一致：{actual['path']}。"
                    "回放不能沿用旧判定；请恢复示例文件，或配置模型运行 live。"
                )
    return docs
