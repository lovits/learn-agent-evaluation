"""Independent deterministic verification; run after the Agent, with private criteria mounted."""

import argparse
import ast
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval_course.records import report_path, save


def check_rule(rule, tools, workspace):
    kind = rule["kind"]
    if kind == "successful_stdout_contains":
        return any(
            t["result"]["exit_code"] == 0 and rule["value"] in t["result"]["stdout"] for t in tools
        )
    if kind == "error_contains":
        return any(
            t["result"]["exit_code"] not in (0, None) and rule["value"] in t["result"]["stderr"]
            for t in tools
        )
    target = (workspace / rule["path"]).resolve()
    if not target.is_relative_to(workspace) or not target.is_file():
        return False
    if kind == "file_sha256":
        return hashlib.sha256(target.read_bytes()).hexdigest() == rule["value"]
    if kind == "python_ast":
        try:
            return ast.dump(ast.parse(target.read_text())) == ast.dump(ast.parse(rule["source"]))
        except (SyntaxError, UnicodeError):
            return False
    raise ValueError(f"未知验收规则：{kind}")


def evaluate(report, criteria, workspace):
    workspace = Path(workspace).resolve()
    tools = [e for e in report["events"] if e["type"] == "bash"]
    checks = [
        {"name": "model_stopped", "passed": report["status"] == "finished"},
        {"name": "bash_was_executed", "passed": bool(tools)},
    ]
    for rule in criteria["checks"]:
        checks.append({"name": rule["name"], "passed": check_rule(rule, tools, workspace)})
    return {
        "run_id": report["run_id"],
        "lesson": "e01",
        "mode": report["mode"],
        "case_id": report["case_id"],
        "passed": all(c["passed"] for c in checks),
        "score": sum(c["passed"] for c in checks) / len(checks),
        "checks": checks,
        "interpretation": "确定性任务合同验收；不评分最终解释的语义，也不是通用代码正确性证明。",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    report = json.loads(report_path(f"e01-{args.run_id}.json").read_text())
    criteria_file = Path(os.environ.get("CRITERIA_FILE", "/verification/e01.json"))
    criteria = json.loads(criteria_file.read_text())
    workspace = Path(os.environ.get("WORKSPACES_DIR", ROOT / "workspaces")) / args.run_id
    grade = evaluate(report, criteria[report["case_id"]], workspace)
    grade["criteria_sha256"] = hashlib.sha256(criteria_file.read_bytes()).hexdigest()
    print(json.dumps(grade, ensure_ascii=False, indent=2))
    print("已保存：", save(grade, prefix="grade-e01"))
    return 0 if grade["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
