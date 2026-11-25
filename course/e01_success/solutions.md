# e01 参考解释

1. `run_bash` 返回结果字典后，`code.py` 先通过 `run["events"].append(...)` 把命令与结果存进运行记录，供外部评分器检查；同批工具全部执行完后，再通过 `messages.append({"role": "tool", "content": results})` 把结果喂回消息列表，模型在下一轮请求时才能看到上一步的终端输出。
2. `reply["tool_calls"]` 为空时，循环会正常将 `status` 设为 `"finished"` 并退出，因此 `model_stopped` 这一项为 `True`。但因为没有任何实际命令输出，磁盘上也没有 `hello.py`，`output_observed` 和 `requested_file` 均为 `False`，最终 `all(checks.values())` 返回 `False`。
3. `evaluate` 每次都会重新读取工作目录里当前的 `hello.py`。把文件改错后，即便历史事件里的 `stdout` 仍保留着正确输出，`requested_file` 也会变成 `False`，总评不通过。而单引号与双引号在 Python 中生成相同的字符串常量，注释也不会进入抽象语法树，所以 `ast.dump(ast.parse(...))` 比对结果不变，依然判为通过。
4. 不能一刀切地要求退出码为 `0`。成功条件始终由用户的任务目标决定：当任务本身就是排查报错时，触发并捕获真实的非零退出码与 `stderr` 反而是完成任务的必要证据。工具报错代表那条命令在环境中执行失败，Agent 任务失败则代表最终没有达成用户的目标。
