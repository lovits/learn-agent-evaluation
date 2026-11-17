"""Run the native user simulator against a real coding Agent; audit its coverage separately."""

import json
import os
import uuid
from pathlib import Path

from deepeval.dataset import ConversationalGolden
from deepeval.simulator import ConversationSimulator
from deepeval.simulator.controller.controller import expected_outcome_controller
from deepeval.simulator.controller.types import Decision
from deepeval.test_case import Turn

from lessons.e01_agent_baseline.code import prepare_workspace
from lessons.e03_judges.eval import Transport
from lessons.e11_task_completion.eval import CapturingDeepJudge

from .code import HERE, MODEL_STEPS_PER_STOP, Conversation
from .context import SupportModel

MAX_SIMULATED_USER_TURNS = 6

SCENARIO = (
    "You are testing a shipping coding Agent in three ordered user turns. First ask it to repair "
    "the v1 function using e11/shipping.md, preserve the exact signature "
    "shipping_fee(weight_grams, expedited=False) and test_shipping.py across future work, "
    "read diagnostics.log, run tests; mention only v1 values (cap5000, expedited300). "
    "After it finishes, ask for v2, changing expedited surcharge to the literal number 400. "
    "Only after v2 is answered, ask for v3, raising the cap to literal 6000, keeping +400. "
    "Do not combine the phases into one request. Do not solve the code or invent test results. "
    "Keep user messages concise; use digits for all numeric requirements."
)
OUTCOME = "All three ordered phases requested and implemented; final cap6000 and surcharge400; original public signature and test file retained."


def stop_after_one(simulated_user_turns):
    return Decision(
        should_end=simulated_user_turns >= 1,
        reason="Controlled simulator fault: end after one generated user turn",
    )


def coverage(versions):
    order = [versions.index(v) if v in versions else None for v in ("v1", "v2", "v3")]
    covered = all(i is not None for i in order)
    return {
        "observed_phases": versions,
        "all_phases_requested_in_order": covered and order == sorted(order),
        "expected_phases": ["v1", "v2", "v3"],
    }


def run_simulation(case, early):
    run_id, support, transport = uuid.uuid4().hex, SupportModel(), Transport()
    workspace = prepare_workspace(case, run_id)
    agent = Conversation(workspace, case, support, compact=True)
    model, observed = CapturingDeepJudge(transport), []
    current_version = "v1"

    def callback(input, turns, thread_id):
        nonlocal current_version
        text = input.replace(",", "")
        candidate = "v3" if "6000" in text else "v2" if "400" in text else "v1"
        current_version = max(current_version, candidate)
        observed.append(
            {"thread_id": thread_id, "sdk_turn_count": len(turns), "version": current_version}
        )
        result = agent.run_turn(input, current_version)
        return Turn(
            role="assistant", content=result["final_answer"] or "Agent error; see runtime report"
        )

    simulator = ConversationSimulator(
        model_callback=callback,
        simulator_model=model,
        async_mode=False,
        stopping_controller=stop_after_one if early else expected_outcome_controller,
    )
    golden = ConversationalGolden(
        scenario=SCENARIO, expected_outcome=OUTCOME, name="shipping-ordered-phases"
    )
    samples, error = [], None
    try:
        samples = simulator.simulate([golden], max_user_simulations=MAX_SIMULATED_USER_TURNS)
    except Exception as failure:  # noqa: BLE001 - retain the actual partial experiment
        error = f"{type(failure).__name__}: {failure}"
    return {
        "run_id": run_id,
        "variant": "controlled_early_stop" if early else "default_outcome_stop",
        "origin": "native_simulated_user_and_live_coding_agent",
        "scenario": SCENARIO,
        "expected_outcome": OUTCOME,
        "status": "error" if error else "completed",
        "error": error,
        "sample": samples[0].model_dump(mode="json") if samples else None,
        "agent_turns": agent.turns,
        "model_inputs": agent.inputs,
        "raw_agent_messages": agent.raw,
        "compaction_events": agent.compactor.events,
        "callback_observations": observed,
        "coverage_audit": coverage([r["version"] for r in observed]),
        "simulator_steps": model.steps,
        "simulator_calls": transport.calls,
        "support_steps": support.steps,
        "support_calls": support.transport.calls,
        "end_observation": {
            "user_turn_limit": MAX_SIMULATED_USER_TURNS,
            "actual_user_turns": len(observed),
            "forced_after_one": early,
            "outcome_decisions": [
                s["result"] for s in model.steps if s["schema"] == "ConversationCompletion"
            ],
        },
    }


def main():
    case = json.loads((HERE / "cases.jsonl").read_text())
    root, rows = Path(os.environ.get("RUNS_DIR", "runs")), []
    for early in (False, True):
        rows.append(run_simulation(case, early))
        (root / "e12-simulation.partial.json").write_text(
            json.dumps({"rows": rows}, ensure_ascii=False, indent=2)
        )
    result = {
        "lesson": "e12",
        "mode": "native_user_simulator_with_live_agent_callback",
        "rows": rows,
        "protocol": {
            "model_steps_per_stop": MODEL_STEPS_PER_STOP,
            "max_simulated_user_turns": MAX_SIMULATED_USER_TURNS,
        },
    }
    (root / "e12-simulation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"coverage": [(r["variant"], r["coverage_audit"]) for r in rows]}))
    return int(any(r["status"] == "error" for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
