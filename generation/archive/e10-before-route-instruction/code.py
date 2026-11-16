"""Keep the known Agent loop; provide its model and dispatcher a dynamic tool pool."""

import json
import os
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from lessons.e01_agent_baseline.code import prepare_workspace
from lessons.e04_retrieval.code import agent_loop

from .mcp_tools import ToolPool

HERE = Path(__file__).parent


def call_model(messages, tools):
    request = Request(
        os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8766/next"),
        data=json.dumps({"lesson": "e10", "messages": messages, "tools": tools}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=200) as response:
        return json.load(response)


def run_case(case, enabled):
    pool, snapshots = ToolPool(enabled=enabled), []

    def model(messages):
        tools = pool.assemble()
        snapshots.append({"model_turn": len(snapshots) + 1, "tools": tools})
        return call_model(messages, tools)

    run_id = uuid.uuid4().hex
    workspace = prepare_workspace(case, run_id)
    result = agent_loop(
        case["task"], workspace, model=model, max_steps=10, tool_dispatch=pool.dispatch
    )
    return {
        "run_id": run_id,
        "mcp_enabled": enabled,
        "task": case["task"],
        "tool_snapshots": snapshots,
        "discovery": pool.discovery_events,
        **result,
        "artifacts": {
            name: (workspace / name).read_text() if (workspace / name).is_file() else None
            for name in ("calculate.py", "result.txt")
        },
    }


def main():
    case = json.loads((HERE / "cases.jsonl").read_text().splitlines()[0])
    root = Path(os.environ.get("RUNS_DIR", "runs"))
    rows = []
    for enabled in (False, True):
        rows.append(run_case(case, enabled))
        (root / "e10-agents.partial.json").write_text(
            json.dumps({"complete": False, "rows": rows}, ensure_ascii=False, indent=2) + "\n"
        )
    report = {
        "lesson": "e10",
        "mode": "live_agent",
        "case": case,
        "rows": rows,
        "mcp_transport": "in_process_teaching_stand_in_like_upstream_s14",
    }
    (root / "e10-agents.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"runs": len(rows), "statuses": [r["status"] for r in rows]}))
    return int(any(r["status"] != "finished" for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
