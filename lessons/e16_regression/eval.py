"""Score a saved actual native trace with both pinned metric implementations."""

import argparse
import json
from pathlib import Path

from lessons.e05_faithfulness.eval import evaluate
from lessons.e10_tool_evaluation.metrics import score_rules

from .code import sha, trace_digest, trace_samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.read_text()
    saved = json.loads(source)
    samples = trace_samples(saved)
    output = {
        "lesson": "e16",
        "origin": "new_native_metric_scoring_of_a_saved_live_integration_trace",
        "source_report_sha256": sha(source),
        "native_trace_sha256": trace_digest(saved),
        "samples": samples,
        "tool_results": [],
        "faithfulness_results": [],
        "agent_new_requests": 0,
        "judge_model_id": None,
        "cost": None,
        "status": "started",
        "judge_requests": 0,
        "metric_errors": 0,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as handle:
        handle.write(json.dumps(output, ensure_ascii=False, indent=2) + "\n")

    def save():
        temporary = args.report.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )
        temporary.replace(args.report)

    try:
        for sample in samples["tools"]:
            output["tool_results"].append(score_rules(sample))
            save()
        for sample in samples["faithfulness"]:
            result = evaluate(sample)
            output["faithfulness_results"].append(result)
            output["judge_requests"] += len(result["calls"])
            output["metric_errors"] += sum(
                v.get("status") == "error" for v in result["metrics"].values()
            )
            save()
        output["status"] = "returned"
    except Exception as error:  # noqa: BLE001 - save partial scores, never fabricate zero or pass
        output["status"] = "error"
        output["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        save()
    print(
        json.dumps(
            {
                "report": str(args.report),
                "status": output["status"],
                "judge_requests": output["judge_requests"],
                "metric_errors": output["metric_errors"],
            }
        )
    )
    return int(output["status"] != "returned" or output["metric_errors"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
