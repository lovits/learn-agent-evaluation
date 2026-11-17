"""Instructor controls: real processes/state/native SDKs, zero model requests."""

import json
import os
import shlex
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

from langchain_core.outputs import LLMResult
from ragas.cost import CostCallbackHandler, TokenUsage
from ragas.run_config import RunConfig, add_retry

from .background import BackgroundManager, file_hashes
from .scheduler import Scheduler


def python_command(source):
    return shlex.quote(sys.executable) + " -c " + shlex.quote(source)


def native_ragas_controls():
    attempts = []

    def operation():
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            raise TimeoutError("instructor-injected transient failure; no provider called")
        return "second attempt returned"

    config = RunConfig(timeout=1, max_retries=2, max_wait=0, exception_types=(TimeoutError,))
    result = add_retry(operation, config)()
    started = time.monotonic()
    unbounded = add_retry(lambda: (time.sleep(1.05), "returned")[1], config)()
    elapsed = time.monotonic() - started
    # Explicitly constructed token metadata and instructor prices, not a bill.
    callback = CostCallbackHandler(lambda response: TokenUsage(**response.llm_output["usage"]))
    for usage in (
        {"input_tokens": 1000, "output_tokens": 100, "model": "illustrative-model"},
        {"input_tokens": 500, "output_tokens": 50, "model": "illustrative-model"},
    ):
        callback.on_llm_end(LLMResult(generations=[], llm_output={"usage": usage}))
    totals = callback.total_tokens()
    cost = callback.total_cost(cost_per_input_token=2e-6, cost_per_output_token=4e-6)
    return {
        "origin": "instructor_fixture_executing_native_ragas_helpers_not_a_provider_request",
        "retry_attempts": attempts,
        "result": result,
        "timeout_field_seconds": config.timeout,
        "function_elapsed_seconds": elapsed,
        "function_returned_without_automatic_timeout": unbounded == "returned",
        "token_totals": totals.model_dump(),
        "illustrative_cost_units": cost,
        "prices": {"input_per_token": 2e-6, "output_per_token": 4e-6},
        "price_origin": "instructor_defined_example_not_market_prices_or_subscription_bill",
        "real_bill": None,
        "model_requests": 0,
        "passed": attempts == [1, 2]
        and unbounded == "returned"
        and totals.input_tokens == 1500
        and totals.output_tokens == 150
        and abs(cost - 0.0036) < 1e-12,
    }


def run():
    with tempfile.TemporaryDirectory() as folder:
        workspace = Path(folder)
        (workspace / "source.py").write_text("version1\n")
        manager = BackgroundManager(workspace, ["source.py"])
        try:
            pending = manager.start(
                python_command(
                    "from pathlib import Path; import time\n"
                    "while not Path('release').exists(): time.sleep(0.01)\n"
                    "print('actual background result')"
                ),
                3,
            )
            main_can_continue = manager.wait(pending["id"], 0)["status"] == "running"
            (workspace / "release").write_text("instructor parent work\n")
            manager.wait(pending["id"], 3)
            delivered = manager.collect()
            no_duplicate = manager.collect() == []
            timeout = manager.start(python_command("import time; time.sleep(5)"), 0.05)
            failed = manager.start(python_command("raise SystemExit(7)"), 2)
            manager.wait(timeout["id"], 2)
            manager.wait(failed["id"], 2)
            manager.collect()
            (workspace / "source.py").write_text("version2\n")
            stale = delivered[0]["final_hashes"] != file_hashes(workspace, ["source.py"])
        finally:
            manager.close()
        scheduler = Scheduler(workspace)
        before = datetime.fromisoformat("2026-11-16T09:00:00+08:00")
        definition = scheduler.create("1 9 * * *", "run tests", False, True)
        early = scheduler.poll(before)
        due = scheduler.poll(before + timedelta(minutes=1))
        duplicate = scheduler.poll(before + timedelta(minutes=1))
        offered = scheduler.take()
        scheduler.restore(offered)
        restarted = Scheduler(workspace)
        reoffered = restarted.take()
        restarted.acknowledge(reoffered)
        native = native_ragas_controls()
        checks = {
            "main_continued_while_background_pending": main_can_continue,
            "actual_background_completed": delivered[0]["result"]["stdout"]
            == "actual background result\n",
            "one_notification": no_duplicate,
            "actual_timeout_distinct_from_nonzero_exit": manager.jobs[timeout["id"]]["status"]
            == "timeout"
            and manager.jobs[failed["id"]]["result"]["exit_code"] == 7,
            "old_receipt_not_current_source": stale,
            "no_early_or_same_minute_duplicate_schedule": early == []
            and len(due) == 1
            and duplicate == [],
            "failed_delivery_and_restart_reoffer_pending": reoffered == offered
            and reoffered[0]["id"] == definition["id"],
            "one_shot_removed_only_after_model_receipt_ack": Scheduler(workspace).list() == [],
            "native_ragas_fixture_passed": native["passed"],
        }
        return {
            "lesson": "e14",
            "origin": "instructor_protocol_controls_with_actual_processes_and_state_operations",
            "model_requests": 0,
            "clock_origin": "explicit_controlled_datetime_not_wall_clock_waiting",
            "checks": checks,
            "passed": all(checks.values()),
            "background_jobs": list(manager.jobs.values()),
            "background_events": manager.events,
            "schedule_events": scheduler.events,
            "restart_events": restarted.events,
            "native_ragas": native,
        }


def main():
    result = run()
    path = Path(os.environ.get("RUNS_DIR", "runs")) / "e14-controls.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "model_requests": 0}))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
