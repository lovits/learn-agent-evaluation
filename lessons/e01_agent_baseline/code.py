"""e01: one loop, Bash, and the evidence needed to judge a file task."""

import argparse
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval_course.records import save
from eval_course.runtime import call_model, prepare_workspace, run_bash

CASES = Path(__file__).with_name("cases.jsonl")


def load_cases():
    return [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]


def agent_loop(task, workspace, model=call_model, max_steps=8, tool_timeout=10):
    messages = [{"role": "user", "content": task}]
    run = {"status": "step_limit", "final_answer": None, "events": []}
    for step in range(1, max_steps + 1):
        try:
            response = model(messages)
            reply = response["reply"]
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            run.update(status="model_error", error=str(error))
            break
        run["events"].append(
            {"type": "model", "step": step, "reply": reply, "model": response.get("model", {})}
        )
        messages.append({"role": "assistant", "content": reply})
        if not reply["tool_calls"]:
            run.update(status="finished", final_answer=reply["answer"])
            break
        results = []
        for index, call in enumerate(reply["tool_calls"]):
            result = run_bash(call["command"], workspace, timeout=tool_timeout)
            run["events"].append(
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
    return run


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
