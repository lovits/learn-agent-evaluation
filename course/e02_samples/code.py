"""The same loop, with named calls and records that retain their results."""

import json

from eval_course.runtime import call_model

from .tools import TOOLS, execute


def live_model(messages):
    return call_model(messages, tools=TOOLS)


def agent_loop(task, workspace, model=live_model, max_steps=8, execute_tool=execute):
    messages = [{"role": "user", "content": task}]
    run = {"status": "step_limit", "final_answer": None, "events": [], "messages": messages}
    for step in range(1, max_steps + 1):
        try:
            reply = model(messages)["reply"]
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            run.update(status="model_error", error=str(error))
            break
        messages.append({"role": "assistant", "content": reply})
        if not reply["tool_calls"]:
            run.update(status="finished", final_answer=reply["answer"])
            break
        results = []
        for index, call in enumerate(reply["tool_calls"]):
            arguments = json.loads(call["arguments_json"])
            result = execute_tool(call["name"], arguments, workspace)
            run["events"].append(
                {
                    "id": f"{step}.{index}",
                    "name": call["name"],
                    "arguments": arguments,
                    "result": result,
                }
            )
            results.append(result)
        messages.append({"role": "tool", "content": results})
    return run
