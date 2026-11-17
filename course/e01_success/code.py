"""The smallest loop: ask, execute Bash, return the result to the model."""

from eval_course.runtime import call_model, run_bash


def agent_loop(task, workspace, model=call_model, max_steps=8):
    messages = [{"role": "user", "content": task}]
    run = {"status": "step_limit", "final_answer": None, "events": []}
    for step in range(1, max_steps + 1):
        try:
            response = model(messages)
            reply = response["reply"]
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            run.update(status="model_error", error=str(error))
            break
        messages.append({"role": "assistant", "content": reply})
        if not reply["tool_calls"]:
            run.update(status="finished", final_answer=reply["answer"])
            break
        results = []
        for index, call in enumerate(reply["tool_calls"]):
            result = run_bash(call["command"], workspace)
            run["events"].append(
                {"id": f"{step}.{index}", "command": call["command"], "result": result}
            )
            results.append(result)
        messages.append({"role": "tool", "content": results})
    return run
