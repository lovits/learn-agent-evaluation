"""Local Codex model transport; it has no access to the student's workspace."""

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
VENDOR = PROJECT / "vendor/pocketflow_tutorial"
DISABLED = [
    "shell_tool",
    "multi_agent",
    "plugins",
    "apps",
    "browser_use",
    "computer_use",
    "workspace_dependencies",
    "image_generation",
    "in_app_browser",
    "skill_search",
    "code_mode_host",
]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def complete(prompt, schema=None, timeout=1200):
    if not shutil.which("codex"):
        raise RuntimeError("请在宿主机安装并登录 Codex CLI。")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="course-model-") as folder:
        root = Path(folder)
        output = root / "reply.txt"
        args = [
            "codex",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--json",
            "-C",
            folder,
            "-o",
            str(output),
        ]
        for feature in DISABLED:
            args.extend(["--disable", feature])
        if schema:
            path = root / "schema.json"
            path.write_text(json.dumps(schema))
            args.extend(["--output-schema", str(path)])
        args.append("-")
        try:
            result = subprocess.run(
                args,
                input="Do not use tools. Return only the requested output.\n" + prompt,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Codex模型等待超时；未切换成预设输出。") from None
        if result.returncode or not output.is_file():
            raise RuntimeError("Codex 模型调用失败；请检查本机登录状态。未替换为预设输出。")
        events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        forbidden = {
            "command_execution",
            "file_change",
            "mcp_tool_call",
            "web_search",
            "collab_tool_call",
        }
        if any(e.get("item", {}).get("type") in forbidden for e in events):
            raise RuntimeError("模型传输层意外调用工具，本次响应不用于课程Agent。")
        usage = [e["usage"] for e in events if e.get("type") == "turn.completed" and "usage" in e]
        model = re.search(r"^model:\s*(\S+)", result.stderr, re.MULTILINE)
        return {
            "text": output.read_text(),
            "usage": usage,
            "reported_model": model.group(1) if model else None,
            "model_selection": "Codex CLI default; user config ignored",
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "transport_tool_events": 0,
            "prompt_sha256": sha(prompt),
        }


def codex_completion(prompt):
    return complete(prompt)["text"]
