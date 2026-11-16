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
    parser.add_argument("--lesson", choices=["e01", "e02", "e03"], default="e01")
    args = parser.parse_args()
    lesson = args.lesson
    slug = "e01_agent_baseline" if lesson == "e01" else "e02_tools_traces"
    title = "最小编程Agent与第一份评测协议" if lesson == "e01" else "工具、权限、轨迹与统一评测样本"
    brief_path = "generation/lesson_brief.md" if lesson == "e01" else "generation/e02-brief.md"
    if lesson == "e03":
        slug, title, brief_path = "e03_judges", "规则评分与LLM裁判", "generation/e03-brief.md"
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
                    "run_summary.md" if lesson in ("e02", "e03") else "example_report.json",
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
            "eval_course/records.py",
            "references/versions.json",
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
            "summary": "模型给动作，Docker里的循环执行Bash，独立容器核实结果。",
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
