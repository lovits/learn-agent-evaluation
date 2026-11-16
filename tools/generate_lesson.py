"""Run pinned PocketFlow tutorial nodes with the approved curriculum and a model adapter."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
VENDOR = PROJECT / "vendor/pocketflow_tutorial"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def codex_completion(prompt):
    if not shutil.which("codex"):
        raise RuntimeError("此主机未安装 Codex CLI；可选择 --backend openai。")
    with tempfile.TemporaryDirectory(prefix="eval-course-generation-") as tmp:
        output = Path(tmp) / "chapter.md"
        args = [
            "codex",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "-C",
            tmp,
            "-o",
            str(output),
            "-",
        ]
        instruction = "Do not use tools or access files. Return only the requested chapter.\n"
        result = subprocess.run(
            args,
            check=False,
            input=instruction + prompt,
            capture_output=True,
            text=True,
            timeout=1200,
        )
        if result.returncode or not output.exists():
            raise RuntimeError("Codex 生成失败。请先检查 codex login status；未采用伪造输出。")
        return output.read_text(encoding="utf-8")


def openai_completion(prompt):
    from eval_course.judges import LiveJSON

    model = LiveJSON()
    reply = model.client.chat.completions.create(
        model=model.model,
        messages=[{"role": "user", "content": prompt}],
    )
    return reply.choices[0].message.content or ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["codex", "openai"], default="codex")
    args = parser.parse_args()
    sys.path.insert(0, str(PROJECT))
    output = PROJECT / "generation/output"
    private = PROJECT / "generation/private"
    private.mkdir(parents=True, exist_ok=True)
    calls = []

    def call_llm(prompt, use_cache=True):
        # No transcript cache: each successful build records a real model invocation.
        started = time.time()
        result = codex_completion(prompt) if args.backend == "codex" else openai_completion(prompt)
        index = len(calls) + 1
        (private / f"prompt-{index}.txt").write_text(prompt, encoding="utf-8")
        (private / f"response-{index}.md").write_text(result, encoding="utf-8")
        calls.append(
            {
                "prompt_sha256": sha(prompt),
                "response_sha256": sha(result),
                "elapsed_seconds": round(time.time() - started, 2),
            }
        )
        return result

    # Keep upstream nodes byte-for-byte unchanged; replace only their model transport.
    bridge = types.ModuleType("utils.call_llm")
    bridge.call_llm = call_llm
    sys.modules["utils.call_llm"] = bridge
    sys.path.insert(0, str(VENDOR))
    from nodes import CombineTutorial, FetchRepo, WriteChapters
    from pocketflow import Flow, Node

    class BindLesson(Node):
        def post(self, shared, prep_res, exec_res):
            shared["abstractions"][0]["files"] = list(range(len(shared["files"])))
            shared["input_manifest"] = [
                {"path": name, "sha256": sha(content)} for name, content in shared["files"]
            ]

    brief = (PROJECT / "generation/lesson_brief.md").read_text(encoding="utf-8")
    shared = {
        "repo_url": None,
        "local_dir": str(PROJECT),
        "project_name": "s07_faithfulness",
        "github_token": None,
        "output_dir": str(output),
        "language": "Chinese",
        "use_cache": False,
        "max_file_size": 100000,
        "include_patterns": {
            "s07_faithfulness/code.py",
            "s07_faithfulness/fixtures.json",
            "eval_course/runner.py",
            "eval_course/judges.py",
            "knowledge_base/policies/*.md",
            "references/upstream/*",
            "references/versions.json",
        },
        "exclude_patterns": {
            ".git",
            ".venv",
            "__pycache__",
            "generation",
            "runs",
            "vendor",
            "tests",
            "secrets",
        },
        "abstractions": [
            {"name": "Faithfulness：回答真的被证据支持吗", "description": brief, "files": []}
        ],
        "relationships": {
            "summary": "以证据支持关系连接知识、实现、实验与验收的单课样章。",
            "details": [],
        },
        "chapter_order": [0],
        "chapters": [],
    }
    fetch, bind = FetchRepo(), BindLesson()
    write, combine = WriteChapters(max_retries=1), CombineTutorial()
    fetch >> bind >> write >> combine
    Flow(start=fetch).run(shared)
    provenance = {
        "generator": "The-Pocket/PocketFlow-Tutorial-Codebase-Knowledge",
        "upstream_commit": "05b24cbbb0fe409c5e23c9791f0342f07524ffdc",
        "backend": args.backend,
        "actual_model_calls": len(calls),
        "calls": calls,
        "nodes_run": [
            "FetchRepo",
            "BindLesson (curriculum adapter)",
            "WriteChapters",
            "CombineTutorial",
        ],
        "not_run": ["IdentifyAbstractions", "AnalyzeRelationships", "OrderChapters"],
        "reason": "The approved 24-lesson curriculum already fixes this one lesson and its order.",
        "input_manifest": shared["input_manifest"],
        "brief_sha256": sha(brief),
        "raw_output_directory": "generation/output/s07_faithfulness",
    }
    (PROJECT / "generation/provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"actual_model_calls": len(calls), "output": shared["final_output_dir"]},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
