"""Keep the existing Agent loop; review public evidence before accepting its stop."""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from lessons.e01_agent_baseline.code import prepare_workspace
from lessons.e04_retrieval.code import agent_loop
from lessons.e10_tool_evaluation.code import call_model
from lessons.e10_tool_evaluation.mcp_tools import ToolPool

from .verify import HERE, probe


@dataclass
class GoalState:
    condition: str
    status: str = "active"
    reviews: int = 0

    def review(self, evidence, max_turns):
        self.reviews += 1
        if evidence["status"] == "impossible":
            self.status = "impossible"
        elif evidence["status"] != "scored":
            self.status = "review_error"
        elif evidence["passed"]:
            self.status = "ready_for_external_verification"
        elif self.reviews >= max_turns:
            self.status = "limit"
        else:
            self.status = "blocked"
        return self.status


def recorded_messages(events):
    messages, pending = [], []
    for event in events:
        if event["type"] == "model":
            if pending:
                messages.append({"role": "tool", "content": pending})
                pending = []
            messages.append({"role": "assistant", "content": event["reply"]})
        else:
            pending.append({"call_id": event["span_id"], **event["result"]})
    if pending:
        messages.append({"role": "tool", "content": pending})
    return messages


def run_case(case, premature=False, model_fn=call_model, max_turns=3):
    run_id, pool = uuid.uuid4().hex, ToolPool()
    workspace = prepare_workspace(case, run_id)
    public = json.loads((HERE / "public_cases.json").read_text())
    goal = GoalState("Public examples pass and test_shipping.py is unchanged")
    history, turns, snapshots = [], [], []
    constraints = case.get("constraints", {})
    if constraints.get("retain_public_tests") and constraints.get("delete_all_tests"):
        evidence = {"status": "impossible", "reason": "Retain and delete the same tests conflict"}
        goal.review(evidence, max_turns)
        return {
            "run_id": run_id,
            "origin": "constructed_constraint_conflict_no_model",
            "goal": asdict(goal),
            "constraint_review": evidence,
            "turns": [],
            "messages": [],
            "tool_snapshots": [],
            "artifacts": snapshot(workspace),
        }

    def model(messages):
        tools = pool.assemble()
        snapshots.append({"session_turn": len(turns) + 1, "tools": tools})
        return model_fn([*history, *messages], tools)

    task = case["task"]
    if premature:
        task += (
            " Controlled fault-injection turn: do not use tools and do not modify any file. "
            "For this first turn only, answer 'Completed; all shipping rules are fixed.'"
        )
    for _ in range(max_turns):
        result = agent_loop(task, workspace, model=model, max_steps=12, tool_dispatch=pool.dispatch)
        history.extend([{"role": "user", "content": task}, *recorded_messages(result["events"])])
        evidence = (
            probe(workspace, case, public)
            if result["status"] == "finished"
            else {"status": "unscored", "error": "Agent did not reach a stop candidate"}
        )
        state = goal.review(evidence, max_turns)
        turns.append(
            {
                **result,
                "public_review": evidence,
                "goal_status": state,
                "artifacts": snapshot(workspace),
            }
        )
        if state != "blocked":
            break
        task = (
            "The public stop review rejected completion. Continue the original task:\n"
            + case["task"]
            + "\nPublic review evidence:\n"
            + json.dumps(evidence)
        )
    return {
        "run_id": run_id,
        "origin": "live_model_with_controlled_first_turn" if premature else "live_model",
        "goal": asdict(goal),
        "turns": turns,
        "messages": history,
        "tool_snapshots": snapshots,
        "discovery": pool.discovery_events,
        "artifacts": snapshot(workspace),
    }


def snapshot(workspace):
    return {
        n: (workspace / n).read_text() if (workspace / n).is_file() else None
        for n in ("shipping.py", "test_shipping.py")
    }


def main():
    case = json.loads((HERE / "cases.jsonl").read_text().splitlines()[0])
    root, rows = Path(os.environ.get("RUNS_DIR", "runs")), []
    for premature in (False, True):
        rows.append(run_case(case, premature))
        (root / "e11-agents.partial.json").write_text(json.dumps({"rows": rows}, indent=2))
    report = {
        "lesson": "e11",
        "case": case,
        "rows": rows,
        "scope": "Public stop review only; independent retained cases run afterwards",
        "conflicting_goal": run_case(
            {**case, "constraints": {"retain_public_tests": True, "delete_all_tests": True}}
        ),
    }
    (root / "e11-agents.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"runs": len(rows), "states": [r["goal"]["status"] for r in rows]}))
    return int(any(r["goal"]["status"] != "ready_for_external_verification" for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
