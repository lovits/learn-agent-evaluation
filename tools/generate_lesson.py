"""Generate a selected lesson using pinned original PocketFlow tutorial nodes."""

import argparse
import json
import sys
import time
import types
from pathlib import Path

from model_backend import PROJECT, VENDOR, codex_completion, sha


def main():
    from pocketflow import Flow, Node

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lesson",
        choices=[
            "e01",
            "e02",
            "e03",
            "e04",
            "e05",
            "e06",
            "e07",
            "e08",
            "e09",
            "e10",
            "e11",
            "e12",
            "e13",
            "e14",
            "e15",
        ],
        default="e01",
    )
    args = parser.parse_args()
    lesson = args.lesson
    slug = "e01_agent_baseline" if lesson == "e01" else "e02_tools_traces"
    title = "最小编程Agent与第一份评测协议" if lesson == "e01" else "工具、权限、轨迹与统一评测样本"
    brief_path = "generation/lesson_brief.md" if lesson == "e01" else "generation/e02-brief.md"
    if lesson == "e03":
        slug, title, brief_path = "e03_judges", "规则评分与LLM裁判", "generation/e03-brief.md"
    if lesson == "e04":
        slug, title, brief_path = (
            "e04_retrieval",
            "知识库检索：精度、召回与排序",
            "generation/e04-brief.md",
        )
    if lesson == "e05":
        slug, title, brief_path = (
            "e05_faithfulness",
            "Faithfulness：回答是否忠于证据",
            "generation/e05-brief.md",
        )
    if lesson == "e06":
        slug, title, brief_path = (
            "e06_answer_quality",
            "答案相关性、正确性、完整性与拒答",
            "generation/e06-brief.md",
        )
    if lesson == "e07":
        slug, title, brief_path = (
            "e07_failure_diagnosis",
            "RAG故障定位：只改一个位置",
            "generation/e07-brief.md",
        )
    if lesson == "e08":
        slug, title, brief_path = (
            "e08_datasets",
            "评测数据集：从候选题到可审核样本",
            "generation/e08-brief.md",
        )
    if lesson == "e09":
        slug, title, brief_path = (
            "e09_comparison",
            "版本比较：先配对再看均值",
            "generation/e09-brief.md",
        )
    if lesson == "e10":
        slug, title, brief_path = (
            "e10_tool_evaluation",
            "工具、参数与MCP：分开看才评得准",
            "generation/e10-brief.md",
        )
    if lesson == "e11":
        slug, title, brief_path = (
            "e11_task_completion",
            "任务完成：先检查，再允许结束",
            "generation/e11-brief.md",
        )
    if lesson == "e12":
        slug, title, brief_path = (
            "e12_conversation",
            "多轮、压缩与记忆：约束还在吗",
            "generation/e12-brief.md",
        )
    if lesson == "e13":
        slug, title, brief_path = (
            "e13_planning",
            "计划、依赖与交接：拆开就能做完吗",
            "generation/e13-brief.md",
        )
    if lesson == "e14":
        slug, title, brief_path = (
            "e14_runtime",
            "后台、调度与效率：少几步就更好吗",
            "generation/e14-brief.md",
        )
    if lesson == "e15":
        slug, title, brief_path = (
            "e15_calibration",
            "裁判校准：分数对了，标准也对了吗",
            "generation/e15-brief.md",
        )
    private = PROJECT / "generation/private" / lesson
    private.mkdir(parents=True, exist_ok=True)
    brief = (PROJECT / brief_path).read_text()
    calls = []

    def call_llm(prompt, use_cache=False):
        started = time.monotonic()
        reply = codex_completion(brief + "\n\n" + prompt)
        index = len(calls) + 1
        (private / f"prompt-{index}.txt").write_text(prompt)
        (private / f"response-{index}.md").write_text(reply)
        calls.append(
            {
                "prompt_sha256": sha(prompt),
                "response_sha256": sha(reply),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        )
        return reply

    bridge = types.ModuleType("utils.call_llm")
    bridge.call_llm = call_llm
    sys.modules["utils.call_llm"] = bridge
    sys.path.insert(0, str(VENDOR))
    from nodes import CombineTutorial, FetchRepo, WriteChapters

    class BindLesson(Node):
        def post(self, shared, prep_res, exec_res):
            shared["abstractions"][0]["files"] = list(range(len(shared["files"])))

    shared = {
        "repo_url": None,
        "local_dir": str(PROJECT),
        "project_name": slug,
        "github_token": None,
        "output_dir": str(PROJECT / "generation/output"),
        "language": "Chinese",
        "use_cache": False,
        "max_file_size": 100000,
        "include_patterns": {
            *(
                f"lessons/{slug}/{name}"
                for name in (
                    "code.py",
                    "eval.py",
                    "cases.jsonl",
                    "run_summary.md" if lesson != "e01" else "example_report.json",
                    "source_walkthrough.md",
                    "exercises.md",
                    "solutions.md",
                )
            ),
            *(
                [f"lessons/{slug}/samples.py", f"lessons/{slug}/dataset_manifest.json"]
                if lesson == "e02"
                else []
            ),
            *(
                [
                    f"lessons/{slug}/verify.py",
                    "eval_course/knowledge.py",
                    "knowledge_base/e04/auth.md",
                    "knowledge_base/e04/limits.md",
                    "knowledge_base/e04/noise.md",
                ]
                if lesson == "e04"
                else []
            ),
            *([f"lessons/{slug}/reference.json"] if lesson == "e06" else []),
            *(["tools/refine_e03.py"] if lesson == "e03" else []),
            *(
                ["lessons/e04_retrieval/code.py", "references/e07-teaching-pattern.md"]
                if lesson == "e07"
                else []
            ),
            *(["references/e01-rewrite-plan.md"] if lesson == "e01" else []),
            *(
                [f"lessons/{slug}/dataset.py", "references/e08-reading.json"]
                if lesson == "e08"
                else []
            ),
            *(
                [f"lessons/{slug}/statistics.py", "references/e09-reading.json"]
                if lesson == "e09"
                else []
            ),
            *(
                [
                    f"lessons/{slug}/{name}"
                    for name in ("mcp_tools.py", "metrics.py", "micro_traces.json")
                ]
                + ["references/e10-reading.json"]
                if lesson == "e10"
                else []
            ),
            *(
                [
                    f"lessons/{slug}/{name}"
                    for name in ("verify.py", "runner.py", "metrics.py", "public_cases.json")
                ]
                + ["references/e11-reading.json", "knowledge_base/e11/shipping.md"]
                if lesson == "e11"
                else []
            ),
            "eval_course/records.py",
            *(
                [
                    f"lessons/{slug}/{name}"
                    for name in (
                        "context.py",
                        "memory.py",
                        "tools.py",
                        "context_controls.py",
                        "simulate.py",
                        "exposure.py",
                    )
                ]
                + [
                    "references/e12-reading.json",
                    "references/e12-diagram.json",
                    "knowledge_base/e12/shipping.md",
                ]
                if lesson == "e12"
                else []
            ),
            "references/versions.json",
            *(
                [
                    f"lessons/{slug}/{name}"
                    for name in ("state.py", "tools.py", "verify.py", "controls.py")
                ]
                + [
                    "tools/model_bridge.py",
                    "references/e13-reading.json",
                    "references/e13-diagram.json",
                    "knowledge_base/e13/shipping.md",
                ]
                if lesson == "e13"
                else []
            ),
            *(
                [
                    f"lessons/{slug}/{name}"
                    for name in (
                        "background.py",
                        "scheduler.py",
                        "cron.py",
                        "tools.py",
                        "resources.py",
                        "controls.py",
                    )
                ]
                + [
                    "tools/model_bridge.py",
                    "references/e14-reading.json",
                    "references/e14-diagram.json",
                    "references/e14-experiment-protocol.json",
                    "knowledge_base/e14/shipping.md",
                ]
                if lesson == "e14"
                else []
            ),
            "references/textbook-writing-standard.md",
            *(
                ["references/e15-reading.json", "references/e15-experiment-protocol.json"]
                if lesson == "e15"
                else []
            ),
        },
        "exclude_patterns": {
            ".git",
            ".venv",
            "__pycache__",
            "generation",
            "workspaces",
            "runs",
            "evaluation_private",
        },
        "abstractions": [{"name": title, "description": brief, "files": []}],
        "relationships": {
            "summary": (
                "固定任务，逐段加入资料、检索和生成故障开关，再沿阶段证据定位。"
                if lesson == "e07"
                else (
                    "以版本化参考答案和拒答政策，区分切题、正确、完整与语义相似。"
                    if lesson == "e06"
                    else "模型给动作，Docker里的循环执行Bash，独立容器核实结果。"
                )
            ),
            "details": [],
        },
        "chapter_order": [0],
        "chapters": [],
    }
    fetch, bind, write, combine = (
        FetchRepo(),
        BindLesson(),
        WriteChapters(max_retries=1),
        CombineTutorial(),
    )
    fetch >> bind >> write >> combine
    Flow(start=fetch).run(shared)
    result = {
        "generator": "The-Pocket/PocketFlow-Tutorial-Codebase-Knowledge",
        "upstream_commit": "05b24cbbb0fe409c5e23c9791f0342f07524ffdc",
        "backend": "local authenticated Codex CLI with tools disabled",
        "actual_model_calls": len(calls),
        "calls": calls,
        "nodes_run": [
            "FetchRepo",
            "BindLesson (fixed lesson adapter)",
            "WriteChapters",
            "CombineTutorial",
        ],
        "not_run": ["IdentifyAbstractions", "AnalyzeRelationships", "OrderChapters"],
        "reason": "The sixteen-lesson outline and current lesson are already fixed.",
        "input_manifest": [
            {"path": name, "sha256": sha(content)} for name, content in shared["files"]
        ],
        "brief_sha256": sha(brief),
        "raw_output_directory": str(Path(shared["final_output_dir"]).relative_to(PROJECT)),
    }
    (PROJECT / f"generation/{lesson}-provenance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {"actual_model_calls": len(calls), "output": shared["final_output_dir"]},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
