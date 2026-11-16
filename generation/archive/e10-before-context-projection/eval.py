"""Native trace metrics plus read-only verification of actual exercise artifacts."""

import argparse
import ast
import json
import os
import re
from pathlib import Path

from .metrics import HERE, judge_metrics, live_projection, score_rules


def program_contract(text):
    """Accept straight-line integer multiplication with literals or named intermediates."""
    try:
        tree, env, printed = ast.parse(text), {}, []

        def value(node):
            if isinstance(node, ast.Constant) and type(node.value) is int:
                return node.value, [node.value]
            if isinstance(node, ast.Name):
                return env[node.id]
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                left, a = value(node.left)
                right, b = value(node.right)
                return left * right, a + b
            raise ValueError("Outside the straight-line multiplication contract")

        for statement in tree.body:
            if (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
            ):
                env[statement.targets[0].id] = value(statement.value)
            elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                call = statement.value
                if (
                    not isinstance(call.func, ast.Name)
                    or call.func.id != "print"
                    or len(call.args) != 1
                    or call.keywords
                ):
                    raise ValueError("Only one-argument print is accepted")
                printed.append(value(call.args[0]))
            else:
                raise ValueError("Outside the straight-line multiplication contract")
        return len(printed) == 1 and printed[0][0] == 48 and sorted(printed[0][1]) == [6, 8]
    except (SyntaxError, ValueError, TypeError, KeyError):
        return False


def verify_live(row, workspace_root):
    if not re.fullmatch(r"[a-f0-9]{32}", row["run_id"]):
        raise ValueError("Invalid run ID")
    workspace = workspace_root / row["run_id"]
    actual = {
        n: (workspace / n).read_text() if (workspace / n).is_file() else None
        for n in ("calculate.py", "result.txt")
    }
    events = [e for e in row["events"] if e["type"] == "tool"]
    names = [e["call"]["name"] for e in events]
    advertised = True
    for event in events:
        index = int(event["parent_id"].removeprefix("model-")) - 1
        visible = {t["name"] for t in row["tool_snapshots"][index]["tools"]}
        advertised &= event["call"]["name"] in visible
    checks = {
        "finished": row["status"] == "finished",
        "files_match_saved_snapshot": actual == row["artifacts"],
        "calculation_contract": actual["calculate.py"] is not None
        and program_contract(actual["calculate.py"]),
        "actual_result_file": actual["result.txt"] == "48\n",
        "successful_program_command": any(
            e["call"]["name"] == "bash"
            and "calculate.py" in json.loads(e["call"]["arguments_json"]).get("command", "")
            and e["result"].get("exit_code") == 0
            for e in events
        ),
        "only_advertised_tools_requested": advertised,
        "mcp_route_when_required": not row["mcp_enabled"]
        or (
            bool(row["discovery"])
            and "connect_mcp" in names
            and "mcp__docs__search" in names
            and names.index("connect_mcp") < names.index("mcp__docs__search")
            and "search_knowledge" not in names
        ),
    }
    return {
        "run_id": row["run_id"],
        "mcp_enabled": row["mcp_enabled"],
        "passed": all(checks.values()),
        "checks": checks,
        "attempted_tools": names,
        "attempt_count": len(names),
        "denied_count": sum(e["permission"]["decision"] == "deny" for e in events),
        "tool_error_count": sum(e["result"]["status"] != "ok" for e in events),
        "scope": "read-only straight-line calculation and recorded execution evidence; not arbitrary program equivalence",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()
    root = Path(os.environ.get("RUNS_DIR", "runs"))
    agents = json.loads((root / "e10-agents.json").read_text())
    controls = json.loads((HERE / "micro_traces.json").read_text())
    reference = controls[0]["expected"]
    rows = [*controls, *(live_projection(r, reference) for r in agents["rows"])]
    if args.judge:
        result = {"lesson": "e10", "mode": "native_llm_judges", **judge_metrics(rows)}
        (root / "e10-judges.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            json.dumps(
                {"judge_requests": len(result["calls"]), "metric_results": len(result["results"])}
            )
        )
        return 0
    scored = [score_rules(row) for row in rows]
    workspace_root = Path(os.environ.get("WORKSPACES_DIR", "workspaces"))
    live = [verify_live(row, workspace_root) for row in agents["rows"]]
    result = {
        "lesson": "e10",
        "mode": "native_rule_metrics_and_read_only_artifact_verification",
        "live": live,
        "metrics": scored,
        "passed": all(r["passed"] for r in live),
        "rule_metric_judge_requests": 0,
        "scope": "constructed controls teach metric boundaries; live projections are not whole-task quality scores",
    }
    (root / "e10-evaluation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "live_runs": len(live),
                "trace_inputs": len(scored),
                "native_rule_scores": len(scored) * 7,
            }
        )
    )
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
