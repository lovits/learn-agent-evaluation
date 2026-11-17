# e01: 定义成功

[课程](../../README.md) · **e01** → [e02 保存一次运行](../../docs/curriculum.md#02-保存一次运行)

> 模型停止了，还要看它留下了什么。

## 问题

让 Agent 创建 `hello.py`，文件里只有一条 `print("Hello, World!")`，然后运行它。

模型回答“已经完成”。你打开目录，文件却不存在。

这里有两个问题。首先，模型需要工具才能真正操作文件。其次，即使模型调用过工具，我们仍要判断结果是否满足任务。一次模型回复，把这两件事都遮住了。

本课先接上最小执行循环，再给它一个独立的评分器。

## 解决方案

模型提出动作，执行框架运行 Bash，把真实结果交回模型。这个负责调用、执行和回填的框架，就是 Harness。

![模型与 Bash 之间的循环](images/agent-loop.png)

循环结束后，评分器读取实际文件和工具记录，按任务条件判断是否完成。

![运行与独立评分的代码关系](images/evaluation-path.png)

模型负责选择下一步。循环负责让动作发生。评分器负责判断发生的事是否符合要求。

## 工作原理

### 1. 从任务开始

[code.py](code.py) 的 `agent_loop` 先建立消息列表：

```python
messages = [{"role": "user", "content": task}]
```

`messages` 是模型接下来会看到的内容。最初只有任务；执行过工具以后，里面会有真实结果。

模型通过 `model(messages)` 返回下一步。这里用一个小 JSON 结构表示动作：

```json
{
  "tool_calls": [{"command": "python3 hello.py"}],
  "answer": ""
}
```

模型接口只生成动作，命令由 Docker 里的课程 Agent 执行。Learn Claude Code 原版使用 `tool_use` / `tool_result`；本课用 JSON 适配本机已登录的模型，循环的职责相同。

### 2. 没有动作，就停下

收到响应以后，先把它加入历史，再看是否还有工具调用。下面是函数中的关键分支：

```python
reply = response["reply"]
messages.append({"role": "assistant", "content": reply})
if not reply["tool_calls"]:
    run.update(status="finished", final_answer=reply["answer"])
    break
```

`finished` 只表示模型结束了本次工作。模型第一轮就说“完成”，也会走到这里。这个状态还没有检查文件。

`run` 的初始状态设为 `step_limit`。只有模型正常停止，才改为 `finished`；循环用完步数时保留原状态，模型调用失败则改为 `model_error`。这样，每一种结束方式都有明确含义。

### 3. 执行动作，保留结果

有动作时，就逐条交给 Bash。循环中的执行与回填部分是：

```python
results = []
for index, call in enumerate(reply["tool_calls"]):
    result = run_bash(call["command"], workspace, timeout=tool_timeout)
    # 完整函数在这里把命令和 result 加入 events。
    results.append(result)
messages.append({"role": "tool", "content": results})
```

`run_bash` 在本次练习目录中执行命令，返回 `stdout`、`stderr`、`exit_code` 和执行状态。下一轮模型能看到真实输出或报错，再决定继续、修正或停止。

`messages` 用于继续工作，`events` 保存实际发生的过程。评分器读 `events`，不会把回答里的“我运行过了”转换成一条执行记录。

每次任务从新目录开始，避免上次留下的 `hello.py` 混进本次结果。模型连接、进程超时和目录准备放在 [runtime.py](../../eval_course/runtime.py)，核心循环保留在本课。先看清循环，再按需要读这些细节。

### 4. 从真实结果判断完成

现在转到 [eval.py](eval.py)。它读取运行记录与工作目录，先检查循环是否结束、是否执行过 Bash，再检查当前任务的规则：

```python
tools = [e for e in report["events"] if e["type"] == "bash"]
checks = [
    {"name": "model_stopped", "passed": report["status"] == "finished"},
    {"name": "bash_was_executed", "passed": bool(tools)},
]
for rule in criteria["checks"]:
    checks.append({"name": rule["name"], "passed": check_rule(rule, tools, workspace)})
```

`create_and_run` 要求两类证据：成功命令的输出包含 `Hello, World!`，以及实际 `hello.py` 的语法树符合指定的单条 `print`。

语法树检查接受引号、注释和普通空白变化。它只检查这个小任务的代码结构，不能证明任意两个程序功能等价。输出包含指定文字，也不能单独证明所有行为正确。因此评分器把几条条件放在一起，按当前任务解释。

### 5. 把评分和解释留下来

汇总取决于两个判断，下面省略了返回值中的标识字段：

```python
return {
    # 省略运行标识与说明字段。
    "passed": all(c["passed"] for c in checks),
    "score": sum(c["passed"] for c in checks) / len(checks),
    "checks": checks,
}
```

对应返回值保存在 `evaluate` 的结果中。`score` 是本次规则的通过比例，方便找到缺项；只有全部条件满足，`passed` 才为真。这不是“Agent 能力的百分比”。

只回复“完成”、没有动作也没有文件的记录，可以是 `finished`，评分仍会失败。

再看一个相反的例子：`command_error` 的任务是运行原脚本并观察错误。脚本非零退出，正好提供了任务要求的证据。工具是否成功和任务是否完成，要根据用户目标分别判断。

## 变更内容

| 部分 | 作用 |
|---|---|
| `agent_loop` | 请求模型，执行动作，回填结果，直到停止 |
| `run_bash` | 让动作发生，并保留输出、错误和退出码 |
| 新练习目录 | 保存本次任务的初始文件与产物 |
| `evaluate` / `check_rule` | 按任务规则读取实际证据，给出逐项判断 |

本课使用自己的规则评分器。DeepEval、Ragas 对任务、运行和评价的分工见[源码导读](source_walkthrough.md)；原生样本接口从下一课开始接入。

## 试一试

让 AI 按项目配置准备环境，然后执行一条任务：

```sh
docker compose run --rm -T course run --case create_and_run
```

用返回的 `run_id` 交给独立评分入口。下面的 `RUN_ID` 要换成刚刚返回的编号：

```sh
docker compose --profile verify run --rm -T verifier verify --run-id RUN_ID
```

沿着这一轮记录回答三个问题：

1. 哪条消息第一次让模型看到了真实命令结果？
2. `finished` 和 `passed` 分别由哪段代码决定？
3. 如果删掉 `hello.py`，模型的完成回答是否还能让评分通过？

再试 `command_error`，想一想：为什么工具报错，这次任务仍可能完成？

[练习](exercises.md) · [参考解释](solutions.md) · [源码导读](source_walkthrough.md)

下一课保存完整的任务、动作和结果，让同一次运行可以成为 DeepEval 与 Ragas 的评测样本。
