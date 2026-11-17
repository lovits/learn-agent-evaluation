"""e04 adds only on-demand knowledge search to the previous visible loop."""

import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from eval_course.knowledge import catalog, search
from lessons.e01_agent_baseline.code import prepare_workspace
from lessons.e02_tools_traces.code import dispatch as previous_dispatch

HERE = Path(__file__).parent


def search_knowledge(query, root=None):
    return [
        {**d, "id": d["path"]}
        for d in search(query, limit=3, root=root)
    ]


def dispatch(call, workspace, approve=lambda n, a: False):
    if call.get("name") != "search_knowledge":
        return previous_dispatch(call, workspace, approve)
    try:
        args = json.loads(call["arguments_json"])
        if (
            not isinstance(args, dict)
            or set(args) != {"query"}
            or not isinstance(args["query"], str)
        ):
            raise ValueError("search_knowledge requires a string query")
        hits = search_knowledge(args["query"])
        return {"decision": "allow", "reason": "read_only_knowledge"}, {
            "status": "ok",
            "hits": hits,
            "output": json.dumps(hits, ensure_ascii=False),
        }
    except (ValueError, TypeError, KeyError, OSError) as error:
        return {"decision": "not_executed", "reason": "knowledge_error"}, {
            "status": "error",
            "output": str(error),
        }


def call_model(messages):
    request = Request(
        os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8766/next"),
        data=json.dumps({"lesson": "e04", "messages": messages}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=200) as response:
        return json.load(response)


def agent_loop(
    task,
    workspace,
    model=call_model,
    max_steps=8,
    approve=lambda n, a: False,
    tool_dispatch=dispatch,
):
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
            policy, result = tool_dispatch(call, workspace, approve)
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


def main():
    case = json.loads((HERE / "cases.jsonl").read_text().splitlines()[0])
    run_id = uuid.uuid4().hex
    workspace = prepare_workspace(case, run_id)
    result = agent_loop(case["task"], workspace)
    docs = [{"id": d["path"], "sha256": d["sha256"]} for d in catalog()]
    report = {
        "lesson": "e04",
        "run_id": run_id,
        "mode": "live_agent",
        "created_at": datetime.now(UTC).isoformat(),
        "case": case,
        "documents": docs,
        **result,
    }
    report["notes"] = (
        (workspace / "upload_notes.txt").read_text()
        if (workspace / "upload_notes.txt").is_file()
        else None
    )
    path = Path(os.environ.get("RUNS_DIR", "runs")) / "e04-agent.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report": str(path), "status": result["status"]}))
    return int(result["status"] != "finished")


if __name__ == "__main__":
    raise SystemExit(main())
