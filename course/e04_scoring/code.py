"""Score controlled answers or one real Agent run with the same criteria."""

import argparse
import json
import uuid
from pathlib import Path

from deepeval.test_case import LLMTestCase

from course.e02_samples.code import agent_loop
from course.e02_samples.samples import to_deepeval
from eval_course.judge import JudgeModel
from eval_course.knowledge import document
from eval_course.records import save
from eval_course.runtime import prepare_workspace

from .eval import UploadContract, explanation_metric, score, set_scores

TASK = (
    "读取 upload.md，仅返回一个 JSON 对象，不加 Markdown。字段必须为 required_header "
    "（上传 token 请求头名称）、max_bytes（最大字节数整数）和 explanation "
    "（说明超限会怎样，以及发送前应做什么）。"
)
REFERENCE = "文件大于 1048576 字节时返回 HTTP 413；发送前先检查文件大小。"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-agent", action="store_true")
    args = parser.parse_args()
    run_id = uuid.uuid4().hex
    model = JudgeModel()
    report = {
        "run_id": run_id,
        "rows": [],
        "set_example": set_scores(["header", "extra"], ["header", "limit", "status"]),
    }
    if args.live_agent:
        source = document("course/upload.md")
        workspace = prepare_workspace({"files": {"upload.md": source["text"]}}, run_id)
        run = {"run_id": run_id, "task": TASK, "mode": "live_model", **agent_loop(TASK, workspace)}
        report["agent_run"] = run
        report["source"] = {k: source[k] for k in ["path", "sha256"]}
        sample = to_deepeval(run)
        sample.expected_output = REFERENCE
        samples = [("live", "live_agent", sample)]
    else:
        rows = [
            json.loads(line)
            for line in Path(__file__).with_name("cases.jsonl").read_text().splitlines()
        ]
        samples = [
            (
                r["id"],
                r["origin"],
                LLMTestCase(input=TASK, actual_output=r["answer"], expected_output=REFERENCE),
            )
            for r in rows
        ]
    for case_id, origin, sample in samples:
        report["rows"].append(
            {
                "id": case_id,
                "origin": origin,
                "sample": sample.model_dump(mode="json"),
                "rules": score(UploadContract(), sample),
                "judge": score(explanation_metric(model), sample),
            }
        )
    report["judge_calls"] = model.calls
    print(save(report, prefix="e04-suite"))
    return 0 if all(r["judge"]["status"] == "ok" for r in report["rows"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
