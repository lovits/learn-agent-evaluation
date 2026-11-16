"""Run the five live Docker tasks, then grade them in separate offline containers."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime

from model_backend import PROJECT

sys.path.insert(0, str(PROJECT))
from eval_course.records import save
from lessons.e02_tools_traces.code import load_cases


def docker(args):
    result = subprocess.run(
        [shutil.which("docker") or "docker", *args],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stdout[-2500:] + result.stderr[-1500:])
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--publish-example", action="store_true", help="更新随教材发布的固定示例报告"
    )
    args = parser.parse_args()
    image = json.loads(docker(["image", "inspect", "learn-agent-evaluation:local"]))[0]
    rows = []
    for case in load_cases():
        print("Running live task:", case["id"], flush=True)
        text = docker(["compose", "run", "--rm", "-T", "course", "run-e02", "--case", case["id"]])
        summary = next(
            json.loads(line) for line in text.splitlines() if line.startswith('{"run_id"')
        )
        run_id = summary["run_id"]
        docker(
            [
                "compose",
                "--profile",
                "verify-e02",
                "run",
                "--rm",
                "-T",
                "verifier",
                "verify-e02",
                "--run-id",
                run_id,
            ]
        )
        report = json.loads((PROJECT / f"runs/e02-{run_id}.json").read_text())
        grade = json.loads((PROJECT / f"runs/grade-e02-{run_id}.json").read_text())
        rows.append({"report": report, "grade": grade})
        print(case["id"], "PASS" if grade["passed"] else "FAIL", run_id, flush=True)
    result = {
        "run_id": uuid.uuid4().hex,
        "lesson": "e02",
        "mode": "live_codex_bridge",
        "created_at": datetime.now(UTC).isoformat(),
        "image_id": image["Id"],
        "platform": image["Os"] + "/" + image["Architecture"],
        "summary": {
            "tasks": len(rows),
            "passed": sum(r["grade"]["passed"] for r in rows),
            "model_requests": sum(
                e["type"] == "model" for r in rows for e in r["report"]["events"]
            ),
            "tool_attempts": sum(e["type"] == "tool" for r in rows for e in r["report"]["events"]),
        },
        "implementation": [
            {"path": name, "sha256": hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()}
            for name in [
                "lessons/e02_tools_traces/code.py",
                "lessons/e02_tools_traces/eval.py",
                "lessons/e02_tools_traces/cases.jsonl",
                "lessons/e02_tools_traces/samples.py",
            ]
        ],
        "rows": rows,
        "not_measured": ["最终解释语义质量", "通用编码能力", "模型费用金额", "未返回的确切模型ID"],
    }
    filename = save(result, prefix="e02-suite")
    if args.publish_example:
        (PROJECT / "lessons/e02_tools_traces/example_report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
    print(json.dumps({"summary": result["summary"], "report": str(filename)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
