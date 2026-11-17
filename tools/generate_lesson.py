"""Generate a draft with pinned PocketFlow nodes; published lessons stay separate."""

import argparse
import hashlib
import json
import sys
import time
import types

from model_backend import PROJECT, VENDOR, codex_completion


def main():
    from pocketflow import Flow, Node

    parser = argparse.ArgumentParser(description=__doc__)
    entries = json.loads((PROJECT / "curriculum.json").read_text())["lessons"]
    parser.add_argument("lesson", choices=[r["id"] for r in entries])
    args = parser.parse_args()
    entry = next(r for r in entries if r["id"] == args.lesson)
    folder = PROJECT / "generation/private" / args.lesson
    folder.mkdir(parents=True, exist_ok=True)
    brief = (
        (PROJECT / "references/textbook-writing-standard.md").read_text()
        + "\n"
        + (PROJECT / "generation/textbook_prompt.md").read_text()
        + "\n"
        + json.dumps(entry, ensure_ascii=False)
    )
    style = (
        PROJECT.parent
        / "learn-claude-code"
        / ("s01_agent_loop" if args.lesson == "e01" else "s02_tool_use")
        / "README.zh.md"
    )
    brief += "\n讲法参考，省略其中所有安装与环境准备内容：\n" + style.read_text()
    calls = []

    def call_llm(prompt, **kwargs):
        started = time.monotonic()
        reply = codex_completion(brief + "\n" + prompt)
        calls.append(
            {
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "response_sha256": hashlib.sha256(reply.encode()).hexdigest(),
                "seconds": round(time.monotonic() - started, 2),
            }
        )
        (folder / "draft.md").write_text(reply)
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
        "project_name": args.lesson,
        "output_dir": str(folder),
        "language": "Chinese",
        "use_cache": False,
        "include_patterns": {f"course/{entry['slug']}/*", "eval_course/runtime.py"},
        "exclude_patterns": {"__pycache__"},
        "max_file_size": 100000,
        "abstractions": [
            {"name": entry["title"], "description": entry["core_question"], "files": []}
        ],
        "chapter_order": [0],
        "chapters": [],
        "relationships": {"summary": entry["core_question"], "details": []},
    }
    fetch, bind, write, combine = (
        FetchRepo(),
        BindLesson(),
        WriteChapters(max_retries=1),
        CombineTutorial(),
    )
    fetch >> bind >> write >> combine
    Flow(start=fetch).run(shared)
    record = {
        "generator": "PocketFlow-Tutorial-Codebase-Knowledge",
        "upstream_commit": "05b24cbbb0fe409c5e23c9791f0342f07524ffdc",
        "nodes_run": ["FetchRepo", "BindLesson", "WriteChapters", "CombineTutorial"],
        "actual_model_calls": len(calls),
        "calls": calls,
        "input_sha256": {p: hashlib.sha256(s.encode()).hexdigest() for p, s in shared["files"]},
        "note": "Raw draft is reviewed and condensed; final textbook is in course/. The agreed outline is not model-reordered.",
    }
    (PROJECT / f"generation/{args.lesson}-provenance.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
