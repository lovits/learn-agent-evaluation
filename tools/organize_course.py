"""Organize reviewed lessons with the pinned PocketFlow tutorial nodes."""

import json
import re
import sys
import types
from pathlib import Path
from urllib.parse import unquote, urlparse

from model_backend import PROJECT, VENDOR, sha
from pocketflow import Flow, Node


def main():
    # The source nodes import a model helper even when only organizing files.
    bridge = types.ModuleType("utils.call_llm")

    def no_model(*args, **kwargs):
        raise RuntimeError("This flow organizes reviewed chapters without model calls")

    bridge.call_llm = no_model
    sys.modules["utils.call_llm"] = bridge
    sys.path.insert(0, str(VENDOR))
    from nodes import CombineTutorial, FetchRepo

    def chapter(path, text):
        def link(match):
            image, label, href = match.groups()
            parsed = urlparse(href)
            if parsed.scheme or not parsed.path:
                return match.group(0)
            target = (PROJECT / path).parent / unquote(parsed.path)
            relative = target.resolve().relative_to(PROJECT).as_posix()
            url = "https://github.com/lovits/learn-agent-evaluation/blob/main/" + relative
            if image:
                url += "?raw=true"
            if parsed.fragment:
                url += "#" + parsed.fragment
            return f"{image}[{label}]({url})"

        return re.sub(r"(!?)\[([^\]]*)\]\(([^)]+)\)", link, text)

    class BindCourse(Node):
        def post(self, shared, prep_res, exec_res):
            files = dict(shared["files"])
            course = json.loads(files["curriculum.json"])
            shared["abstractions"] = [
                {"name": row["title"], "description": row["core_question"]}
                for row in course["lessons"]
            ]
            shared["chapters"] = [
                chapter(row["textbook"], files[row["textbook"]])
                + "\n\n"
                + chapter(row["source_walkthrough"], files[row["source_walkthrough"]])
                for row in course["lessons"]
            ]
            shared["chapter_order"] = list(range(len(course["lessons"])))
            shared["relationships"] = {
                "summary": course["title"],
                "details": [
                    {"from": i, "to": i + 1, "label": "继续"}
                    for i in range(len(course["lessons"]) - 1)
                ],
            }

    shared = {
        "repo_url": None,
        "local_dir": str(PROJECT),
        "project_name": "course",
        "output_dir": str(PROJECT / "generation/output"),
        "include_patterns": {
            "curriculum.json",
            "README.md",
            "references/versions.json",
            "references/textbook-writing-standard.md",
            "lessons/*/README.zh.md",
            "lessons/*/source_walkthrough.md",
            "lessons/*/*.py",
            "eval_course/knowledge.py",
            "eval_course/tinyrag.py",
        },
        "exclude_patterns": {".git", ".venv", "__pycache__", "runs", "workspaces"},
        "max_file_size": 200000,
    }
    fetch, bind, combine = FetchRepo(), BindCourse(), CombineTutorial()
    fetch >> bind >> combine
    Flow(start=fetch).run(shared)
    output = Path(shared["final_output_dir"])
    provenance = {
        "generator": "PocketFlow-Tutorial-Codebase-Knowledge",
        "upstream_commit": "05b24cbbb0fe409c5e23c9791f0342f07524ffdc",
        "nodes_run": ["FetchRepo", "BindCourse (reviewed content)", "CombineTutorial"],
        "actual_model_calls": 0,
        "input_sha256": {name: sha(text) for name, text in shared["files"]},
        "lesson_count": len(shared["chapters"]),
        "output_directory": str(output.relative_to(PROJECT)),
    }
    (output / "organization.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
