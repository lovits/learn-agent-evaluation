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
            "e16",
        ],
        default="e01",
    )
    args = parser.parse_args()
    lesson = args.lesson
    entry = next(
        row
        for row in json.loads((PROJECT / "curriculum.json").read_text())["lessons"]
        if row["id"] == lesson
    )
    if entry["implementation"] != "ready":
        parser.error("本课尚未按新大纲迁移代码；请先完成代码，再生成对应教材。")
    slug, title = entry["slug"], entry["title"]
    private = PROJECT / "generation/private" / lesson
    private.mkdir(parents=True, exist_ok=True)
    brief = (
        (PROJECT / "generation/textbook_prompt.md").read_text()
        + "\n\n"
        + (PROJECT / "references/textbook-writing-standard.md").read_text()
        + ("\n\n" + (PROJECT / "generation/lesson_brief.md").read_text() if lesson == "e01" else "")
        + "\n\n当前课程要求：\n"
        + json.dumps(entry, ensure_ascii=False, indent=2)
    )
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
            shared["repo_url"] = "https://github.com/lovits/learn-agent-evaluation"
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
            *(["lessons/e04_retrieval/code.py"] if lesson == "e07" else []),
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
            *(["eval_course/runtime.py"] if lesson == "e01" else []),
            *(
                [
                    "eval_course/tinyrag.py",
                    "eval_course/knowledge.py",
                    "vendor/tinyrag/VectorBase.py",
                ]
                if lesson in {"e04", "e07", "e09", "e16"}
                else []
            ),
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
            *(
                [
                    "integrated_agent/runtime.py",
                    "integrated_agent/scenario.py",
                    "integrated_agent/workflows.py",
                    "integrated_agent/traces.py",
                    "integrated_agent/architecture.md",
                    "integrated_agent/capabilities.md",
                    "references/e16-capability-contracts.json",
                    "references/e16-composed-v2-protocol.json",
                    "references/e16-metrics-v2-protocol.json",
                    "references/e16-diagram.json",
                ]
                if lesson == "e16"
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
