"""Model transport, Bash execution and fresh workspaces used by the lesson loop."""

import json
import os
import signal
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

PROJECT = Path(__file__).resolve().parent.parent
BLOCKED = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


def call_model(messages, tools=None):
    url = os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8766/next")
    request = Request(
        url,
        data=json.dumps({"messages": messages, "tools": tools}).encode(),
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
        if tools is None:
            if not isinstance(call.get("command"), str) or not call["command"].strip():
                raise ValueError("Bash action requires command")
        else:
            if not isinstance(call.get("name"), str) or not isinstance(
                json.loads(call["arguments_json"]), dict
            ):
                raise ValueError("Named action requires an argument object")
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


def prepare_workspace(case, run_id, folder=None):
    root = Path(folder or os.environ.get("WORKSPACES_DIR", PROJECT / "workspaces"))
    workspace = (root / run_id).resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    for name, content in case.get("files", {}).items():
        target = (workspace / name).resolve()
        if not target.is_relative_to(workspace):
            raise ValueError("样本文件不能越出练习目录。")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return workspace
