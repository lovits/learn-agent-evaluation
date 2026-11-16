"""Generate only lesson e01 using pinned original PocketFlow tutorial nodes."""

import json
import sys
import time
import types

from model_backend import PROJECT, VENDOR, codex_completion, sha


def main():
    from pocketflow import Flow, Node

    private = PROJECT / "generation/private/e01"
    private.mkdir(parents=True, exist_ok=True)
    brief = (PROJECT / "generation/lesson_brief.md").read_text()
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
        "project_name": "e01_agent_baseline",
        "github_token": None,
        "output_dir": str(PROJECT / "generation/output"),
        "language": "Chinese",
        "use_cache": False,
        "max_file_size": 100000,
        "include_patterns": {
            "lessons/e01_agent_baseline/code.py",
            "lessons/e01_agent_baseline/eval.py",
            "lessons/e01_agent_baseline/cases.jsonl",
            "lessons/e01_agent_baseline/example_report.json",
            "lessons/e01_agent_baseline/source_walkthrough.md",
            "lessons/e01_agent_baseline/exercises.md",
            "lessons/e01_agent_baseline/solutions.md",
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
        "abstractions": [
            {"name": "最小编程Agent与第一份评测协议", "description": brief, "files": []}
        ],
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
            "BindLesson (approved e01 adapter)",
            "WriteChapters",
            "CombineTutorial",
        ],
        "not_run": ["IdentifyAbstractions", "AnalyzeRelationships", "OrderChapters"],
        "reason": "The sixteen-lesson outline and current lesson are already fixed.",
        "input_manifest": [
            {"path": name, "sha256": sha(content)} for name, content in shared["files"]
        ],
        "brief_sha256": sha(brief),
        "raw_output_directory": shared["final_output_dir"],
    }
    (PROJECT / "generation/e01-provenance.json").write_text(
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
