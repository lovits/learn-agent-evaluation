"""e02: named tools, permission decisions and correlated execution spans."""

import argparse
import json
import os
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from eval_course.records import save
from lessons.e01_agent_baseline.code import prepare_workspace, run_bash

HERE = Path(__file__).parent
TOOL_SPEC = {
    "bash": {"command": "str"},
    "read_file": {"path": "str"},
    "write_file": {"path": "str", "content": "str"},
    "edit_file": {"path": "str", "old_text": "str", "new_text": "str"},
    "glob": {"pattern": "str"},
}


def load_cases():
    return [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines()]


def call_model(messages):
    request = Request(
        os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8766/next"),
        data=json.dumps({"lesson": "e02", "messages": messages}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=200) as response:
        return json.load(response)


def validate_call(call):
    name = call["name"]
    if name not in TOOL_SPEC:
        raise ValueError("Unknown tool: " + name)
    args = json.loads(call["arguments_json"])
    if not isinstance(args, dict) or set(args) != set(TOOL_SPEC[name]):
        raise ValueError("Expected arguments: " + ", ".join(TOOL_SPEC[name]))
    if not all(isinstance(value, str) for value in args.values()):
        raise ValueError("All arguments must be strings.")
    return name, args


def permission(name, args, workspace, approve):
    if name == "bash":
        command = args["command"]
        if any(
            word in command for word in ("rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if=")
        ):
            return "deny", "deny_list"
        destructive = re.search(r"(?:^|[;&|()\n])\s*(?:rm|del)(?=\s|$)", command)
        if destructive or any(word in command for word in ("> /etc/", "chmod 777")):
            return ("allow" if approve(name, args) else "deny"), "approval_required"
    elif name in ("read_file", "write_file", "edit_file"):
        path = (workspace / args["path"]).resolve()
        if not path.is_relative_to(workspace):
            return "deny", "outside_workspace"
    elif name == "glob" and (
        Path(args["pattern"]).is_absolute() or ".." in Path(args["pattern"]).parts
    ):
        return "deny", "outside_workspace"
    return "allow", "workspace_policy"


def execute(name, args, workspace):
    if name == "bash":
        result = run_bash(args["command"], workspace)
        return {**result, "output": result["stdout"] + result["stderr"]}
    if name == "glob":
        paths = sorted(
            str(p.relative_to(workspace))
            for p in workspace.glob(args["pattern"])
            if p.resolve().is_relative_to(workspace)
        )
        return {"status": "ok", "output": "\n".join(paths[:200])}
    path = (workspace / args["path"]).resolve()
    if name == "read_file":
        output = path.read_text(encoding="utf-8")
    elif name == "write_file":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        output = "Wrote " + args["path"]
    else:
        text = path.read_text(encoding="utf-8")
        if not args["old_text"] or args["old_text"] not in text:
            raise ValueError("old_text not found or empty")
        path.write_text(text.replace(args["old_text"], args["new_text"], 1), encoding="utf-8")
        output = "Edited " + args["path"]
    return {"status": "ok", "output": output[:50000], "truncated": len(output) > 50000}


def dispatch(call, workspace, approve=lambda name, args: False):
    try:
        name, args = validate_call(call)
    except (ValueError, KeyError, TypeError) as error:
        return {"decision": "not_checked", "reason": "invalid_arguments"}, {
            "status": "invalid_arguments",
            "output": str(error),
        }
    decision, reason = permission(name, args, workspace, approve)
    policy = {"decision": decision, "reason": reason}
    if decision == "deny":
        return policy, {"status": "denied", "output": "Permission denied: " + reason}
    try:
        return policy, execute(name, args, workspace)
    except (OSError, ValueError) as error:
        return policy, {"status": "error", "output": str(error), "error_type": type(error).__name__}


def agent_loop(task, workspace, model=call_model, max_steps=8, approve=lambda n, a: False):
    messages = [{"role": "user", "content": task}]
    events, hooks = [], []
    hooks.append({"phase": "UserPromptSubmit", "span_id": "agent"})
    status, answer = "step_limit", None
    for step in range(1, max_steps + 1):
        try:
            response = model(messages)
            reply = response["reply"]
            if not isinstance(reply["answer"], str) or not isinstance(reply["tool_calls"], list):
                raise TypeError("Invalid model response")
            if len(reply["tool_calls"]) > 8:
                raise ValueError("Too many tool calls")
        except (ValueError, TypeError, KeyError, RuntimeError, OSError) as error:
            status, answer = "model_error", str(error)
            break
        model_id = f"model-{step}"
        events.append(
            {
                "type": "model",
                "span_id": model_id,
                "parent_id": "agent",
                "reply": reply,
                "model": response.get("model", {}),
            }
        )
        messages.append({"role": "assistant", "content": reply})
        if not reply["tool_calls"]:
            status, answer = "finished", reply["answer"]
            break
        results = []
        for index, call in enumerate(reply["tool_calls"]):
            call_id = f"{model_id}:tool-{index}"
            hooks.append({"phase": "PreToolUse", "span_id": call_id})
            start = time.monotonic()
            policy, result = dispatch(call, workspace, approve)
            events.append(
                {
                    "type": "tool",
                    "span_id": call_id,
                    "parent_id": model_id,
                    "call": call,
                    "permission": policy,
                    "result": result,
                    "elapsed_seconds": round(time.monotonic() - start, 6),
                }
            )
            hooks.append({"phase": "PostToolUse", "span_id": call_id, "status": result["status"]})
            results.append({"call_id": call_id, **result})
        messages.append({"role": "tool", "content": results})
    hooks.append({"phase": "Stop", "span_id": "agent", "status": status})
    return {"status": status, "final_answer": answer, "events": events, "hooks": hooks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=[c["id"] for c in load_cases()])
    args = parser.parse_args(argv)
    case = next(c for c in load_cases() if c["id"] == args.case)
    run_id = uuid.uuid4().hex
    workspace = prepare_workspace(case, run_id)
    result = agent_loop(case["task"], workspace)
    import hashlib

    report = {
        "run_id": run_id,
        "lesson": "e02",
        "schema_version": "e02.v1",
        "dataset_sha256": hashlib.sha256((HERE / "cases.jsonl").read_bytes()).hexdigest(),
        "split": "development",
        "case_id": case["id"],
        "task": case["task"],
        "created_at": datetime.now(UTC).isoformat(),
        "mode": "live_codex_bridge",
        **result,
    }
    path = save(report, prefix="e02")
    print(json.dumps({"run_id": run_id, "status": result["status"], "report": str(path)}))
    return 0 if result["status"] == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
