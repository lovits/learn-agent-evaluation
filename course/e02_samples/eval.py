"""Check task evidence while keeping sample export separate from scoring."""

from .samples import export


def evaluate(run, workspace, case):
    target = (workspace / case["output_path"]).resolve()
    checks = {
        "model_stopped": run["status"] == "finished",
        "tool_observed": bool(run["events"]),
        "requested_file": target.is_relative_to(workspace.resolve())
        and target.is_file()
        and target.read_text() == case["output_content"],
    }
    if case.get("expect_denied"):
        checks["denial_observed"] = any(e["result"]["status"] == "denied" for e in run["events"])
    else:
        checks["read_observed"] = any(
            e["name"] == "read_file" and e["result"]["status"] == "ok" for e in run["events"]
        )
    return {"passed": all(checks.values()), "checks": checks, "samples": export(run)}
