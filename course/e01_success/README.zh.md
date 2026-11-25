# e01: 定义成功：模型停下了，任务就完成了吗？

`e01` → [e02](../e02_samples/README.zh.md) → e03 → … → e16

> *“模型不再调用工具，只代表这一轮停下了；任务是否完成，要看留下的结果。”*
>
> **评测层：成功条件。** 用最小循环让模型真正执行命令，再用独立评分函数核对运行记录与磁盘文件。

## 问题

给大模型布置一个很小的编程任务：“在当前目录创建 `hello.py`，内容只有 `print("Hello, World!")`，并运行它。”

如果没有外层循环替模型执行命令，模型输出一段代码或一句“已完成”就停了，目录里什么也不会留下。即便接上了 Bash，只看模型最后一句话依然靠不住：它可能只跑了一条 `echo "Hello, World!"` 凑出终端输出，却根本没写 `hello.py`；也可能创建了文件，但打印内容写错了。

评测 Agent 的第一步，就是把“让模型干活”和“检查干得对不对”拆成两件独立的事。

## 解决方案

先搭一个最小的模型与工具循环（Harness），让模型提出的 Bash 命令在工作目录里真正跑起来，并把终端输出喂回下一轮消息；循环结束后，再由独立的 `evaluate` 函数读取执行轨迹和磁盘上的 `hello.py` 逐项核对。

![模型与工具之间的循环](https://lovits.github.io/learn-agent-evaluation/diagrams/e01-agent-loop.svg?v=b196d8cfa092)

循环与评分器读取不同的信号，承担不同的职责：

| 阶段 | 观察对象 | 回答的问题 |
|---|---|---|
| Agent 循环 | 模型响应里还有没有 `tool_calls` | 当前轮次要不要继续执行命令？ |
| 独立评分器 | 停止状态、命令退出码与 `stdout`、磁盘文件语法树 | 用户要求的任务真的做对了吗？ |

![运行记录、产物与独立评分](https://lovits.github.io/learn-agent-evaluation/diagrams/e01-evaluation-path.svg?v=98527c6d0fb5)

这套切分也是 DeepEval 的基本组织方式：任务输入与预期结果属于题目定义（`Golden`），一次运行产生的输出与轨迹属于待测样本（`LLMTestCase`），通过与否则由独立的评估逻辑（`evaluate`）判定。

## 工作原理

### 最小 Agent 循环

打开 [code.py](code.py)，整个循环不到三十行，分四步运转。

**第 1 步**：把任务放进消息列表，同时初始化一份运行记录 `run`。默认状态先设为 `step_limit`，防止模型一直调工具停不下来时被误判为正常结束。

```python
messages = [{"role": "user", "content": task}]
run = {"status": "step_limit", "final_answer": None, "events": []}
```

**第 2 步**：在 `max_steps` 步数上限内请求模型，把模型回复追加进 `messages`。如果模型调用本身报错，记录 `model_error` 并退出循环。

```python
response = model(messages)
reply = response["reply"]
messages.append({"role": "assistant", "content": reply})
```

**第 3 步**：检查模型这轮有没有提出工具调用。没有调用时，把状态更新为 `finished`，记下最终回答并结束循环。

```python
if not reply["tool_calls"]:
    run.update(status="finished", final_answer=reply["answer"])
    break
```

注意这里的 `status="finished"` 只说明模型主动停下了。此时循环既没检查 `hello.py` 是否存在，也没核对过终端输出。

**第 4 步**：模型要求执行命令时，逐条调用 `run_bash`，把进程真实返回的 `stdout`、`stderr` 和 `exit_code` 同时写入两处：`run["events"]` 留给外部评分器查账，`messages` 送回给模型继续下一轮推理。

```python
results = []
for index, call in enumerate(reply["tool_calls"]):
    result = run_bash(call["command"], workspace)
    run["events"].append(
        {"id": f"{step}.{index}", "command": call["command"], "result": result}
    )
    results.append(result)
messages.append({"role": "tool", "content": results})
```

### 独立评分函数

循环退出后，[eval.py](eval.py) 接手检查。它不采信 `final_answer` 里的口头声明，直接核对三项客观证据：

```python
def evaluate(run, workspace, case):
    target = workspace / "hello.py"
    try:
        correct_file = target.resolve().is_relative_to(workspace.resolve()) and ast.dump(
            ast.parse(target.read_text())
        ) == ast.dump(ast.parse('print("Hello, World!")'))
    except (OSError, SyntaxError, UnicodeError):
        correct_file = False
    checks = {
        "model_stopped": run["status"] == "finished",
        "output_observed": any(
            e["result"]["exit_code"] == 0 and "Hello, World!" in e["result"]["stdout"]
            for e in run["events"]
        ),
        "requested_file": correct_file,
    }
    return {"passed": all(checks.values()), "checks": checks}
```

把常见的假阳性放进这三条规则里走一遍，就能看出逐项拆开检查的作用：

- 模型一上来直接回复“已完成”：`model_stopped` 为真，但 `events` 为空、文件不存在，后两项直接拦住。
- 模型只执行 `echo 'Hello, World!'`：终端确实出现了目标字符串，`output_observed` 为真，但磁盘上没有合规的 `hello.py`，`requested_file` 为假。
- 模型写的是单引号 `print('Hello, World!')` 或顺手加了一行注释：`ast.parse` 比较的是抽象语法树，引号风格和注释不会误伤正确实现。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `agent_loop` | [code.py](code.py) | 循环请求模型、分发 Bash 命令、回填结果并记录退出状态 |
| `run_bash` | [runtime.py](../../eval_course/runtime.py) | 在独立工作目录执行命令，捕获 `stdout`、`stderr` 与退出码 |
| `run["events"]` | 运行记录 | 按 `{step}.{index}` 顺序保存每次实际执行的命令与返回结果 |
| `evaluate` | [eval.py](eval.py) | 独立核对停止状态、终端输出与磁盘文件，汇总 `passed` 与分项结果 |

## 试一下

运行本课的 `hello` 任务：

```sh
python -m course.run e01 --case hello
```

动手验证三个问题：

1. 如果模型第一轮就返回空 `tool_calls` 和一句 `"已完成"`，`run["status"]` 是什么，`evaluate` 里的哪几项会失败？
2. 正常跑通一次后，手动把工作区里的 `hello.py` 改成 `print("wrong")`，再用旧运行记录重跑评分。`output_observed` 和 `requested_file` 分别会给出什么结果？
3. 把 `hello.py` 改成单引号并加上一行 `# greeting` 注释，看看 `ast.dump(ast.parse(...))` 为什么依然判为通过。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

现在 Agent 只有一个 `bash` 工具，读写文件全靠拼 Shell 命令字符串。一旦两次运行都回答“完成”，其中一次成功写入、另一次因为路径越界被拦截，光靠原始命令字符串很难做细粒度分析，也没法直接喂给 DeepEval 的工具评测指标。

下一课 `e02` 引入具名文件工具与路径权限检查，并把一次运行的事件轨迹正式转换为 DeepEval 的 `LLMTestCase` 与 `ToolCall` 样本。
