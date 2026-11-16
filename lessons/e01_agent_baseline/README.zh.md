# 第1课：一个循环、一个Bash，再加独立验收

## 问题

我们从创建一个文件开始：

> 创建 `hello.py`，内容只包含一条 `print("Hello, World!")` 语句，然后使用 `python3` 运行它，报告实际结果。

如果把这句话直接发给模型，它可能回复：“已经创建并运行，输出是 `Hello, World!`。”要验收这次任务，还得检查：

- `hello.py` 是否真的存在；
- 文件是否真的只有一条 `print`；
- `python3 hello.py` 是否真的执行过。

模型可以写出这段回答，却没有因此创建任何文件。我们得给它接上执行环境，让它提出的命令真正跑起来。等它说“完成”以后，再由独立验收器检查文件和执行记录。

这一课就把这条路径接通：

> 用户任务 → 模型提出动作 → Harness 执行 Bash → 结果返回模型 → 模型停止 → 验收器独立检查

这里的 Harness 可以理解为执行框架。它负责循环、运行命令和保存记录，它和模型一起组成这里的 Agent。

## 解决方案

先把模型和执行环境分开。模型入口运行在宿主机，只负责生成结构化动作；课程中的 Harness 运行在 Docker 中，真正执行 Bash。

[![Agent执行循环](images/agent-loop.png)](images/agent-loop.png)

沿着图中的箭头走一遍：

1. `call_model` 把当前消息交给模型；
2. 模型返回 `tool_calls`；
3. 有动作就交给 `run_bash`；
4. Bash 的真实结果写回 `messages`；
5. 模型再次判断要继续行动，还是给出最终回答。

以创建并运行 `hello.py` 为例，模型可能先返回这样的动作：

```json
{
  "tool_calls": [
    {"command": "printf '%s\n' 'print(\"Hello, World!\")' > hello.py && python3 hello.py"}
  ],
  "answer": ""
}
```

这段 JSON 本身仍然没有创建文件。只有 Harness 把其中的 `command` 交给 Bash，动作才真正发生。执行结果可能包含：

```json
{
  "stdout": "Hello, World!\n",
  "stderr": "",
  "exit_code": 0,
  "status": "ok"
}
```

这份结果随后回到消息历史。在这个例子里，模型看到输出后就可以停止调用工具，回答任务已经完成。

到这里，我们只知道 Agent 主动停下来了。文件是否符合要求，还要交给独立验收器检查。

## 工作原理

下面沿着一次运行读几段代码。片段都摘自 [`code.py`](code.py) 或 [`eval.py`](eval.py) 的函数内部；片段省略了部分日志、异常记录和返回字段。运行时使用链接中的完整文件。

**第1步：先把用户任务放进消息历史**

Agent 需要一份模型能够看到的历史。最开始只有用户任务：

```python
def agent_loop(task, workspace, model=call_model,
               max_steps=8, tool_timeout=10):
    messages = [
        {"role": "user", "content": task}
    ]
    events = []
```

`messages` 是对话工作区。之后模型的动作、最终回答和工具结果都会追加到这里。此时还没有任何命令，也没有假设任务已经完成。

`events` 用途不同：它保存可供报告与验收读取的过程记录。可以把 `messages` 看成模型的工作记忆，把 `events` 看成实验的流水账。

**第2步：向模型取得下一步动作**

接下来调用 `model(messages)`，取出结构化回复，再把助手消息加入历史：

```python
response = model(messages)
reply = response["reply"]
messages.append({"role": "assistant", "content": reply})
```

Learn Claude Code 的原版 `s01` 使用 Anthropic 的 `tool_use` 与 `tool_result`。本课为了复用宿主机已有登录，改用 JSON 中的 `tool_calls` 和 `answer` 传递动作。

Codex CLI 在这里自身工具关闭，只负责生成动作。它不会直接接触练习目录；Bash 交给 Docker 中的 Harness 执行。

**第3步：没有动作时停止循环**

拿到回复后，先看 `tool_calls` 是否为空：

```python
events.append({
    "type": "model",
    "step": step,
    "reply": reply,
    "model": response.get("model", {}),
})
if not reply["tool_calls"]:
    return {"status": "finished",
            "final_answer": reply["answer"],
            "events": events}
```

`finished` 只表示模型没有继续请求工具，也就是“模型主动停了”。它不表示文件正确，更不表示任务已经通过独立验收。

原版循环使用 `while True`。本课使用 `for step in range(1, max_steps + 1)` 加入运行预算：预算耗尽返回 `step_limit`，模型传输或动作结构出错返回 `model_error`。异常分支的完整处理见[源码导读](source_walkthrough.md)。

**第4步：命令真正执行在这里**

如果存在工具动作，Harness 调用 `run_bash`：

```python
with subprocess.Popen(
    command,
    shell=True,
    executable="/bin/bash",
    cwd=workspace,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
) as process:
    stdout, stderr = process.communicate(timeout=timeout)
```

最关键的一行是 `cwd=workspace`。它让命令在本次任务的练习目录中运行，因此写入 `hello.py`、执行 `python3 hello.py` 都会作用于真实工作区。

函数还会保存 `stdout`、`stderr`、`exit_code` 和 `status`。命令超时、输出截断与教学阻断词表的实现没有在这里展开，可在[完整执行代码](code.py)和[源码导读](source_walkthrough.md)中查看。

**第5步：把真实结果还给模型**

一次响应可以包含多个 Bash 动作。Harness 依次执行并收集结果：

```python
results = []
for index, call in enumerate(reply["tool_calls"]):
    result = run_bash(
        call["command"], workspace,
        timeout=tool_timeout,
    )
    events.append({"type": "bash", "step": step,
                   "index": index, "command": call["command"],
                   "result": result})
    results.append(result)
```

执行结束后，结果作为工具消息追加到历史：

```python
messages.append({
    "role": "tool",
    "content": results,
})
```

下一轮模型看到的不再是自己猜测的输出，而是 Bash 返回的真实 `stdout`、`stderr` 和退出码。它可以据此修正命令，也可以停止并回答。

每次运行都会创建新的 `workspace`，避免上一次留下的 `hello.py` 让下一次任务误通过。这是实验目录隔离，不是内核级安全隔离。

**第6步：把“停止”交给独立验收器复查**

Agent 结束后，`code.py` 的 `main` 把 `events` 连同 `run_id` 保存为运行报告。批处理入口 `tools/run_e01.py` 再启动独立的 `eval.py`。验收器读取 `events` 和只读工作区，按照私有任务标准判断 `passed`。

[![独立验收代码结构](images/evaluation-path.png)](images/evaluation-path.png)

`evaluate` 先确认模型正常停止，而且确实执行过 Bash：

```python
workspace = Path(workspace).resolve()
tools = [
    e for e in report["events"]
    if e["type"] == "bash"
]
checks = [
    {"name": "model_stopped",
     "passed": report["status"] == "finished"},
    {"name": "bash_was_executed",
     "passed": bool(tools)},
]
```

然后逐条调用 `check_rule`，最后汇总所有结果：

```python
for rule in criteria["checks"]:
    checks.append({
        "name": rule["name"],
        "passed": check_rule(rule, tools, workspace),
    })
return {
    "run_id": report["run_id"],
    "passed": all(c["passed"] for c in checks),
    "checks": checks,
}
```

对 `create_and_run`，验收器既检查成功执行记录中是否出现 `Hello, World!`，也用 Python AST 检查 `hello.py` 是否只有约定的单条 `print`。AST 比字符串逐字比较更合适：它接受单双引号、注释和普通空白变化，但拒绝额外语句。

私有标准只挂载给验收容器。验收器读取记录和文件，不调用模型，也不重新运行生成的程序。这里检查的是一个明确的小任务；这些规则能说明什么、还漏掉什么，见[源码导读](source_walkthrough.md)。

再看另一条任务：`command_error` 要求运行原脚本并如实观察错误，而不是修复脚本。因此 Bash 的非零退出和任务 `passed` 可以同时出现，因为这条任务需要的就是错误记录。

DeepEval 和 Ragas 也把待测对象的输出与评分结果分开保存。本课先用文件和执行记录把这个区别跑通，再到[源码导读](source_walkthrough.md)对照两者的文档与源码；本课尚未调用它们的原生评分器。

## 相对一次模型问答的变更

普通问答的终点是“模型生成了一段文字”。现在多了一条执行回路和一次独立验收：

- Harness 接收模型动作，在真实工作区执行 Bash；
- 工具结果回到 `messages`，让模型基于事实继续；
- `events` 保存动作与结果，形成可检查轨迹；
- 独立验收器不相信最终回答，而是检查轨迹和文件；
- `finished` 来自 `agent_loop` 的判停，`passed` 来自 `evaluate` 的规则验收。

这几步让我们能检查具体的文件任务。最终解释讲得好不好、换一类编程题还能不能做好，需要另外设计样本和评分方法。

如果想看实际发生过什么，可以打开[首次运行记录](run_summary.md)，再对照[完整示例报告](example_report.json)。这次改写沿用那份历史记录，没有重新测量 Agent。

## 试一下

先在宿主机终端启动模型桥，并保持进程运行：

```bash
python3 tools/model_bridge.py
```

另开一个终端，构建并启动课程环境：

```bash
docker compose up --build -d
```

运行创建并执行 `hello.py` 的单任务：

```bash
docker compose run --rm -T course run --case create_and_run
```

命令会返回一个由 32 个十六进制字符组成的 `run_id`。把下面的 `实际run_id` 完整替换成刚返回的编号，不要原样复制占位词：

```bash
docker compose --profile verify run --rm -T verifier verify \
  --run-id 实际run_id
```

运行报告在 `e01-实际run_id.json`，独立验收报告在 `grade-e01-实际run_id.json`。前者回答“Agent 做了什么”，后者回答“这些事实是否满足任务要求”。

批量运行四条公开任务时使用：

```bash
python3 tools/run_e01.py
```

不要添加 `--publish-example`，这样会保留教材中固定的历史示例报告。课程页面可在浏览器打开：

```text
http://localhost:8765/lesson
```

阅读报告时，先追三个具体问题：

1. 模型返回的动作在哪一刻由 JSON 变成了真实 Bash 命令？
2. Bash 的真实 `stdout` 和 `stderr` 怎样进入下一轮 `messages`？
3. `finished` 来自哪个函数的判停，`passed` 又来自哪个函数的汇总？

接着可以完成[练习](exercises.md)，再对照[参考答案](solutions.md)。需要追异常、预算和验收规则时看[源码导读](source_walkthrough.md)；需要查看首次保存的真实轨迹时看[历史示例报告](example_report.json)。本次图文改写的检查另见[验收记录](../../docs/e01-rewrite-validation.md)。

## 接下来

现在这个 Agent 已经能创建文件、运行程序并接受独立验收，但读写文件仍然要靠模型拼 Bash。下一课要解决的新问题是：怎样把这些意图变成具名工具，再进一步讨论权限和轨迹。
