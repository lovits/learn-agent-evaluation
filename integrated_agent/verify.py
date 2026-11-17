"""Independent foundation acceptance: business artifacts and native memory state have distinct contracts."""

import argparse
import json
import re
import tempfile
from pathlib import Path

import yaml

from lessons.e13_planning.verify import files_at, verify


def memory_state(workspace):
    root = workspace / ".memory"
    if not root.exists():
        return {"passed": True, "records": [], "index_matches_records": True}
    if not root.is_dir():
        return {
            "passed": False,
            "records": [],
            "invalid_entries": [".memory is not a directory"],
            "index_matches_records": False,
        }
    records, problems, lines = [], [], []
    for path in sorted(root.iterdir()):
        if path.name == "MEMORY.md":
            continue
        if path.is_symlink() or not path.is_file() or not re.fullmatch(r"[\w-]+\.md", path.name):
            problems.append(path.name)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            problems.append(path.name)
            continue
        parts = text.split("---", 2) if text.startswith("---\n") else []
        if len(parts) != 3:
            problems.append(path.name)
            continue
        try:
            metadata = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            metadata = None
        if (
            not isinstance(metadata, dict)
            or not isinstance(metadata.get("type"), str)
            or metadata.get("type") not in {"user", "feedback", "project", "reference"}
            or any(
                not isinstance(metadata.get(k), str) or not metadata[k].strip()
                for k in ("name", "description")
            )
            or not parts[2].strip()
        ):
            problems.append(path.name)
            continue
        name = " ".join(metadata["name"].split())
        description = " ".join(metadata["description"].split())
        lines.append(f"- [{name}]({path.name}) - {description}")
        records.append({"filename": path.name, "metadata": metadata, "body": parts[2].strip()})
    expected = "\n".join(lines) + ("\n" if lines else "")
    index = root / "MEMORY.md"
    matches = (index.read_text(encoding="utf-8") if index.is_file() else "") == expected
    return {
        "passed": not problems and matches,
        "records": records,
        "invalid_entries": problems,
        "index_matches_records": matches,
    }


def grade_foundation(workspace, case, criteria):
    workspace = Path(workspace).resolve(strict=True)
    symlinks = [str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_symlink()]
    if symlinks:
        return {
            "profile": "foundation",
            "passed": False,
            "symlinks": symlinks,
            "behavior": None,
            "reason": "Symlinks violate this exercise's workspace contract",
        }
    state = memory_state(workspace)
    modules = "|".join(re.escape(Path(n).stem) for n in case["files"] if n.endswith(".py"))
    unexpected = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace)
        if str(relative) in case["files"]:
            continue
        if len(relative.parts) == 2 and relative.parts[0] == ".memory":
            continue  # Its complete file and index contract is checked above.
        if (
            len(relative.parts) == 2
            and relative.parts[0] == "__pycache__"
            and re.fullmatch(rf"(?:{modules})\.cpython-\d+(?:\.opt-\d+)?\.pyc", path.name)
        ):
            continue
        unexpected.append(str(relative))
    actual = files_at(workspace, case["files"])
    with tempfile.TemporaryDirectory() as directory:
        clean = Path(directory)
        for name, text in actual.items():
            if text is not None:
                (clean / name).write_text(text, encoding="utf-8")
        behavior = verify(clean, case, criteria)
    return {
        "profile": "foundation",
        "origin": "actual_read_only_workspace_and_bounded_behavior_execution",
        "passed": behavior["passed"] is True and state["passed"] and not unexpected,
        "behavior": behavior,
        "memory_state": state,
        "unexpected_files": sorted(unexpected),
        "symlinks": [],
        "full_17_mechanism_acceptance": False,
    }


def grade_composed(workspace, case, criteria):
    from .state import composed_state

    workspace = Path(workspace).resolve(strict=True)
    state = composed_state(workspace, case)
    if state.get("symlinks"):
        return {"profile": "composed", "passed": False, "state": state, "behavior": None}
    actual = files_at(workspace, case["files"])
    with tempfile.TemporaryDirectory() as directory:
        clean = Path(directory)
        for name, text in actual.items():
            if text is not None:
                (clean / name).write_text(text, encoding="utf-8")
        behavior = verify(clean, case, criteria)
    return {
        "profile": "composed",
        "origin": "actual_read_only_native_state_and_bounded_independent_behavior_execution",
        "passed": state["passed"] and behavior["passed"],
        "state": state,
        "behavior": behavior,
        "full_17_mechanism_acceptance": False,
        "scope": "One composed scenario; all-mechanism acceptance also requires the separate capability contracts and failure controls.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--case", type=Path, default=Path(__file__).parent / "cases/foundation.json"
    )
    parser.add_argument("--criteria", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--profile", choices=["foundation", "composed"], default="foundation")
    args = parser.parse_args()
    if args.report.resolve().is_relative_to(args.workspace.resolve()):
        parser.error("Verification report must remain outside the application workspace")
    grader = grade_composed if args.profile == "composed" else grade_foundation
    result = grader(
        args.workspace, json.loads(args.case.read_text()), json.loads(args.criteria.read_text())
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "report": str(args.report),
                "passed": result["passed"],
                "full_17_mechanism_acceptance": False,
            }
        )
    )
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
