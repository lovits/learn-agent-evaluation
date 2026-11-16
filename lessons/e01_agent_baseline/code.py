"""e01: ask the model, execute Bash, append results, repeat until the model stops."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval_course.records import save

CASES = Path(__file__).with_name("cases.jsonl")
BLOCKED = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


def load_cases():
    return [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]


def call_model(messages):
    url = os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8766/next")
    request = Request(
        url,
        data=json.dumps({"messages": messages}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=200) as response:
        value = json.load(response)
    if not isinstance(value, dict) or not isinstance(value.get("reply"), dict):
        raise TypeError("模型返回了无效的动作结构。")
    reply = value["reply"]
    if (
        not isinstance(reply.get("answer"), str)
        or not isinstance(reply.get("tool_calls"), list)
        or len(reply["tool_calls"]) > 8
    ):
        raise ValueError("模型返回了无效的动作结构。")
    for call in reply["tool_calls"]:
        if (
            not isinstance(call, dict)
            or not isinstance(call.get("command"), str)
            or not call["command"].strip()
        ):
            raise ValueError("Bash动作缺少command。")
    return value


def run_bash(command, workspace, timeout=10):
    if any(word in command for word in BLOCKED):
        return {
            "stdout": "",
            "stderr": "Command blocked by the teaching deny list.",
            "exit_code": None,
            "status": "blocked",
        }
    with subprocess.Popen(
        command,
        shell=True,
        executable="/bin/bash",
        cwd=workspace,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        start_new_session=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            status = "ok" if process.returncode == 0 else "error"
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
            status = "timeout"
    return {
        "stdout": stdout[:50000],
        "stderr": stderr[:50000],
        "exit_code": process.returncode,
        "status": status,
        "truncated": len(stdout) > 50000 or len(stderr) > 50000,
    }


def agent_loop(task, workspace, model=call_model, max_steps=8, tool_timeout=10):
    messages = [{"role": "user", "content": task}]
    events = []
    for step in range(1, max_steps + 1):
        try:
            response = model(messages)
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            return {
                "status": "model_error",
                "final_answer": None,
                "error": str(error),
                "events": events,
            }
        reply = response["reply"]
        events.append(
            {"type": "model", "step": step, "reply": reply, "model": response.get("model", {})}
        )
        messages.append({"role": "assistant", "content": reply})
        if not reply["tool_calls"]:
            return {"status": "finished", "final_answer": reply["answer"], "events": events}
        results = []
        for index, call in enumerate(reply["tool_calls"]):
            result = run_bash(call["command"], workspace, timeout=tool_timeout)
            events.append(
                {
                    "type": "bash",
                    "step": step,
                    "index": index,
                    "command": call["command"],
                    "result": result,
                }
            )
            results.append(result)
        messages.append({"role": "tool", "content": results})
    return {"status": "step_limit", "final_answer": None, "events": events}


def prepare_workspace(case, run_id, folder=None):
    root = Path(folder or os.environ.get("WORKSPACES_DIR", ROOT / "workspaces"))
    workspace = (root / run_id).resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    for name, content in case.get("files", {}).items():
        target = (workspace / name).resolve()
        if not target.is_relative_to(workspace):
            raise ValueError("样本文件不能越出练习目录。")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return workspace


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--case", choices=[c["id"] for c in load_cases()])
    group.add_argument("--task")
    args = parser.parse_args(argv)
    case = (
        next(c for c in load_cases() if c["id"] == args.case)
        if args.case
        else {"id": "custom", "task": args.task}
    )
    run_id = uuid.uuid4().hex
    workspace = prepare_workspace(case, run_id)
    started = time.monotonic()
    try:
        result = agent_loop(case["task"], workspace)
    except (ValueError, KeyError, OSError) as error:
        print(f"模型或执行失败：{error}", file=sys.stderr)
        return 1
    report = {
        "run_id": run_id,
        "lesson": "e01",
        "mode": "live_codex_bridge",
        "case_id": case["id"],
        "task": case["task"],
        "workspace_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        **result,
    }
    path = save(report)
    print(
        json.dumps(
            {"run_id": run_id, "status": result["status"], "report": str(path)}, ensure_ascii=False
        )
    )
    print(result["final_answer"] or result.get("error") or "达到步数上限；不记为成功。")
    return 0 if result["status"] == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
