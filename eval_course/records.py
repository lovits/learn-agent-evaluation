"""Persist experiment records using names that cannot escape the results directory."""

import json
import os
import re
from pathlib import Path

from .knowledge import PROJECT

NAME = re.compile(r"(?:(?:grade-)?e(?:0[1-9]|1[0-6])|e(?:0[1-9]|1[0-6])-suite)-[0-9a-f]{32}\.json")


def report_root():
    return Path(os.environ.get("RUNS_DIR", PROJECT / "runs"))


def report_path(name, folder=None):
    root = Path(folder or report_root()).resolve()
    target = (root / name).resolve()
    if not NAME.fullmatch(name) or not target.is_relative_to(root):
        raise ValueError("无效的实验文件名。")
    return target


def save(report, prefix="e01", folder=None):
    target = report_path(f"{prefix}-{report['run_id']}.json", folder)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return target
