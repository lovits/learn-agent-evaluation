"""Read-only native state contract for the predeclared composed teaching scenario.

This is a finite exercise grader. It does not treat arbitrary .git or memory
content as secure, nor certify general hostile-code containment.
"""

import json
import re
import subprocess
from pathlib import Path

from .scenario import IGNORE
from .verify import memory_state


def git(workspace, *args):
    return subprocess.run(
        ["git", "-c", f"safe.directory={workspace}", "-C", str(workspace), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip()


def read_json(path):
    if not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError("Missing or over-limit native state file: " + path.name)
    return json.loads(path.read_text())


def composed_state(workspace, case):
    workspace = Path(workspace).resolve(strict=True)
    problems = []
    symlinks = [str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_symlink()]
    if symlinks:
        return {
            "passed": False,
            "problems": ["Symlinks violate the exercise contract"],
            "symlinks": symlinks,
        }
    try:
        memory = memory_state(workspace)
        if not memory["passed"]:
            problems.append("Native memory records or index are invalid")
        if (workspace / ".gitignore").read_text() != IGNORE:
            problems.append("Instructor .gitignore was modified")
        if (workspace / "scheduled.txt").read_text() != "scheduled delivery observed":
            problems.append("Scheduled delivery artifact differs from the declared contract")
        if read_json(workspace / ".scheduled_tasks.json") != []:
            problems.append("Durable scheduled delivery remains pending")
        tasks = list((workspace / ".tasks").glob("task_*.json"))
        if len(tasks) != 1:
            problems.append("Expected exactly one native review task")
        for path in tasks:
            task = read_json(path)
            if (
                task.get("id") != path.stem
                or task.get("status") != "completed"
                or task.get("owner") != "reviewer"
                or task.get("worktree") is not None
                or task.get("blockedBy") != []
            ):
                problems.append("Review task is unfinished, misowned or still bound")
        if any((workspace / ".worktrees").iterdir()):
            problems.append("Native worktree lease was not released and removed")
        if any((workspace / ".mailboxes").iterdir()):
            problems.append("Undelivered native team messages remain")
        worktrees = git(workspace, "worktree", "list", "--porcelain")
        if worktrees.count("worktree ") != 1:
            problems.append("Git still registers an extra worktree")
        git(workspace, "fsck", "--strict", "--no-reflogs")
        branch_files = git(workspace, "ls-tree", "-r", "--name-only", "wt/review").splitlines()
        if set(branch_files) != set(case["files"]) | {".gitignore", "review.txt"}:
            problems.append("Preserved review branch contains unexpected files")
        branch_review = git(workspace, "show", "wt/review:review.txt")
        if not branch_review:
            problems.append("Preserved review branch has no actual review")
        for name in case["files"]:
            if (
                git(workspace, "show", "wt/review:" + name)
                != (workspace / name).read_text().strip()
            ):
                problems.append("Review branch differs from the repaired root source: " + name)
        store = workspace / ".workflow_runtime"
        run_id = (store / "last_run.txt").read_text().strip()
        if not re.fullmatch(r"wf_course-review_[0-9a-f]{16}", run_id):
            raise ValueError("Invalid native workflow run ID")
        snapshot = read_json(store / (run_id + ".json"))
        output = read_json(store / (run_id + ".output.json"))
        journal_path = store / (run_id + ".journal.jsonl")
        journal = [json.loads(line) for line in journal_path.read_text().splitlines()]
        if (
            snapshot.get("runId") != run_id
            or snapshot.get("workflowName") != "course-review"
            or snapshot.get("task", {}).get("status") != "completed"
            or snapshot.get("args", {}).get("files") != list(case["files"])
            or len(journal) != 3
            or len({r["key"] for r in journal}) != 3
            or any(set(r) != {"key", "value"} for r in journal)
            or not isinstance(output.get("issues"), list)
            or not all(isinstance(i, str) for i in output["issues"])
        ):
            problems.append("Native workflow snapshot/journal/output contract failed")
        allowed = set(case["files"]) | {
            ".gitignore",
            "scheduled.txt",
            ".scheduled_tasks.json",
            ".tasks/.lock",
        }
        allowed |= {str(p.relative_to(workspace)) for p in tasks}
        allowed |= {
            ".workflow_runtime/" + run_id + suffix
            for suffix in (".json", ".output.json", ".journal.jsonl", ".lock")
        }
        allowed.add(".workflow_runtime/last_run.txt")
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            relative = str(path.relative_to(workspace))
            if relative in allowed:
                continue
            if relative.startswith(".git/"):
                # Native Git objects are checked above; executable unsampled hooks are forbidden.
                if relative.startswith(".git/hooks/") and not path.name.endswith(".sample"):
                    problems.append("Unexpected Git hook: " + relative)
                continue
            if re.fullmatch(r".memory/[\w-]+\.md", relative):
                continue  # Its complete record/index format was checked independently above.
            if re.fullmatch(
                r"__pycache__/(shipping|checkout|test_shipping|test_checkout)\.cpython-\d+(?:\.opt-\d+)?\.pyc",
                relative,
            ):
                continue
            if re.fullmatch(r".transcripts/transcript_\d+\.jsonl", relative):
                for line in path.read_text().splitlines():
                    message = json.loads(line)
                    if message.get("role") not in {"user", "assistant"} or "content" not in message:
                        raise ValueError("Invalid native transcript message")
                continue
            problems.append("Unexpected exercise artifact: " + relative)
        return {
            "passed": not problems,
            "problems": problems,
            "memory": memory,
            "review_task_count": len(tasks),
            "workflow_journal_records": len(journal),
            "branch_review": branch_review,
            "semantic_review_correctness": None,
        }
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        problems.append(f"{type(error).__name__}: {error}")
        return {"passed": False, "problems": problems}
