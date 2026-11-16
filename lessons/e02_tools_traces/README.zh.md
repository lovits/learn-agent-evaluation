# 第2课：给动作命名，再把每次调用记清楚

## 问题

第1课已经把模型提出的 Bash 动作交给执行器运行。这一课继续复用其中两个函数：

- `prepare_workspace`：为每次实验准备独立工作目录；
- `run_bash`：在工作目录中执行命令，保留 `stdout`、`stderr`、`exit_code` 和超时状态。

这一课换成修改现有程序。工作目录里有一个 `calculate.py`：

```python
print(6 * 7)
```

我们希望 Agent 找到这个文件，把 `6 * 7` 改成 `6 * 8`，运行程序，再把实际输出写入 `result.txt`。完成后应当得到：

```text
48
```

只用 Bash 当然也能完成，例如调用 `sed`、`python3` 和重定向。但这样留下的记录只是一串命令。评测程序很难直接回答：模型是否先读了文件？修改的是哪一处？写文件和执行程序分别成功了吗？

我们给读、写、修改和查找各加一个具名工具，让参数直接表达操作意图；运行程序继续交给 Bash。这样可以分别检查读取、修改和执行的结果。

工具一多，还会出现两个新问题。第一，某些动作不应直接执行，例如读取工作目录外的 `/etc/hostname`。第二，同一轮可能连续调用两次 `read_file`，仅凭工具名无法知道哪个返回值属于哪个请求。我们需要在执行前判断权限，并为每次调用分配唯一的关联标识。

完整实现见 [code.py](code.py)，五条任务见 [cases.jsonl](cases.jsonl)。

## 解决方案

本课把一次动作拆成四层：

```text
模型给出调用
    → 参数校验
    → 权限判断
    → 工具执行
    → 记录结果
```

例如，修改 `calculate.py` 时，模型给出工具名和一组 JSON 参数：

```json
{
  "name": "edit_file",
  "arguments_json": "{\"path\":\"calculate.py\",\"old_text\":\"6 * 7\",\"new_text\":\"6 * 8\"}"
}
```

运行时先检查三个必需参数是否齐全、是否都是字符串。随后解析路径，确认它仍在本次工作目录内。只有参数和权限都通过，才会真正读取并改写文件。

同一轮的每个工具请求还会分配一个 `call_id`，结果返回时带上相同标识。执行前后各记一条 hook 事件，之后就能追查：这个结果属于哪次模型响应、哪个工具请求，以及动作停在了哪一步。

## 工作原理

下面沿着“把42改成48”这条数据流读代码。片段均有省略，用来说明接入点，不能单独作为程序入口运行。

**第1步：声明工具及必需参数**

运行时需要先知道每个工具接受哪些参数：

```python
TOOL_SPEC = {
    "bash": {"command": "str"},
    "read_file": {"path": "str"},
    "write_file": {"path": "str", "content": "str"},
    "edit_file": {"path": "str", "old_text": "str", "new_text": "str"},
    "glob": {"pattern": "str"},
}
```

`validate_call` 解析 `arguments_json`，要求参数集合与声明完全一致，并要求所有值都是字符串。假如 `read_file` 收到 `{}`，它不会进入权限检查或文件读取，而是在执行前返回：

```json
{
  "status": "invalid_arguments",
  "output": "Expected arguments: path"
}
```

`None`、漏参和多传参数都会在这一层被识别。之后再查工具错误时，就能先区分参数是否有效。

**第2步：由 dispatch 分发到本地实现**

本课的本地 `execute` 按工具名使用条件分支：

```python
if name == "bash":
    result = run_bash(args["command"], workspace)
    return {**result, "output": result["stdout"] + result["stderr"]}
if name == "glob":
    paths = sorted(
        str(p.relative_to(workspace))
        for p in workspace.glob(args["pattern"])
        if p.resolve().is_relative_to(workspace)
    )
    return {"status": "ok", "output": "\n".join(paths[:200])}
```

文件工具也在同一个函数中分支处理。`edit_file` 最关键的一行是：

```python
path.write_text(text.replace(args["old_text"], args["new_text"], 1), encoding="utf-8")
```

末尾的 `1` 表示只替换第一处。若 `old_text` 为空或根本不存在，工具抛出 `ValueError`，原文件不会被写入。`glob` 先排序，再截取前200项，避免一次结果无限增长。

读上游时留意这一处实现差异。原版 s02 使用 `TOOL_HANDLERS` 查表；本课的 `execute` 是按 `name` 判断。两者的源码对应关系放在 [源码导读](source_walkthrough.md)。

**第3步：执行前检查 permission**

文件路径在真正访问前解析：

```python
path = (workspace / args["path"]).resolve()
if not path.is_relative_to(workspace):
    return "deny", "outside_workspace"
return "allow", "workspace_policy"
```

因此，直接填写 `/etc/hostname`，或通过符号链接绕向目录外，都会得到 `denied`。Bash 另有拒绝词和危险命令规则。普通动作返回 `decision="allow"`；命中硬拒绝规则时返回 `decision="deny"`。

需要人工确认的规则稍有不同：

```python
return ("allow" if approve(name, args) else "deny"), "approval_required"
```

`approval_required` 是原因 `reason`，不是第三种 `decision`。实际决定仍然只有 `allow` 或 `deny`。批量实验的批准回调固定返回拒绝，不会弹出交互确认框。

这些规则只是教学策略，不能保证隔离任意 Bash。这套实验还依赖 Docker 的运行安排：工具在容器内执行，宿主机 Codex 只返回动作；登录凭据不放入容器，Agent 镜像也不包含私有验收标准。

**第4步：用 call_id 和 hook 记录父子关系**

模型的第几次响应决定 `model_id`，响应内第几个动作决定 `call_id`：

```python
model_id = f"model-{step}"
call_id = f"{model_id}:tool-{index}"
hooks.append({"phase": "PreToolUse", "span_id": call_id})
policy, result = dispatch(call, workspace, approve)
```

工具事件把调用、权限和结果放在一起：

```python
events.append({
    "type": "tool",
    "span_id": call_id,
    "parent_id": model_id,
    "call": call,
    "permission": policy,
    "result": result,
})
```

随后写入 `PostToolUse`，并将同一个 `call_id` 随结果返回模型。重复的工具名不足以完成关联：两次 `read_file` 可能读取不同文件，也可能一次成功、一次报错。关联必须依靠顺序、父节点和调用标识。

参数错误、权限拒绝、执行错误和超时也不能混为一类：

- `invalid_arguments`：参数校验失败，尚未检查权限；
- `denied`：权限层拒绝，没有进入工具实现；
- `error`：已经执行工具，但文件异常、`ValueError` 或 Bash 非零退出；
- `timeout`：命令超过第1课执行器的时间限制；
- `ok`：工具按合同完成。

Bash 还可能保留第1课执行器给出的 `blocked`。读报告时也要保留它与其他状态的区别，不把它改写成 `ok` 或普通 `error`。

**第5步：用 trace_errors 检查内部一致性**

记录完成后，[samples.py](samples.py) 根据模型声明的工具顺序生成预期队列：

```python
pending = [
    (f"{model_id}:tool-{i}", model_id, c)
    for i, c in enumerate(event["reply"]["tool_calls"])
]
```

每遇到一个工具事件，就比较 `span_id`、`parent_id` 和原始调用：

```python
actual = (event["span_id"], event["parent_id"], event["call"])
if not pending or actual != pending.pop(0):
    errors.append("tool_result_order_or_owner")
```

它还能发现 `missing_tool_result` 和 `hook_coverage`：前者表示调用缺少结果，后者表示 Pre/Post/Stop 记录缺失或状态不一致。

这项检查核对的是记录内部的关系。有人同时改掉调用、结果和 hook，仍可能形成一份自洽的假记录；只改 `stdout` 内容，也不一定会触发关联错误。因此，轨迹检查之后还要由独立验收器读取实际文件、输出和退出码。

**第6步：构造四种 SDK 样本并独立验收**

先看 DeepEval 单轮样本怎样接收已检查的事实。这里摘出 `native_samples` 内的一次构造：

```python
LLMTestCase(
    input=report["task"],
    actual_output=report["final_answer"],
    expected_output=reference,
    tools_called=list(deep_tools.values()),
    metadata=metadata,
)
```

DeepEval 单轮样本使用 `input`、`actual_output`、`expected_output`、`retrieval_context` 四个基础字段，并用 `tools_called` 保存工具调用。Ragas 对应 `user_input`、`response`、`reference`、`retrieved_contexts`；多轮样本使用 `HumanMessage`、`AIMessage` 和 `ToolMessage` 保存交互顺序。

同一份轨迹还会生成 DeepEval `ConversationalTestCase`、Ragas `SingleTurnSample` 和 `MultiTurnSample`。单轮视图保留任务输入与最终回答，多轮视图保留每次模型响应和工具返回。`finished` 仍只是 Agent 停止，任务通过要另看独立验收。

四种对象都要经过构造、JSON 导出和恢复。恢复时如何重建 DeepEval 的嵌套 `ToolCall`、Ragas 怎样在 metadata 保存关联 ID，以及空值和检索字段的处理，见[源码导读](source_walkthrough.md)。样本结构通过校验后，后续课程才能按指标检查所需字段；本课不调用语义裁判。

独立验收器的判定条件是：任务必须 `finished`，轨迹内部一致，指定工具状态满足，指定文件或 `stdout`、`exit_code` 满足，而且四种 SDK 样本都能构造并恢复。任一检查失败，该任务就不通过。

## 相对上一课的变更

本课保留第1课的工作目录准备和 Bash 执行，没有改写它们。新增内容集中在动作分发、执行前权限、轨迹和样本转换。

| 方面 | 第1课 | 本课 |
|---|---|---|
| 动作 | 只有 Bash | Bash 加四种文件工具 |
| 参数 | Bash 命令 | 按工具声明必需字符串参数 |
| 权限 | 执行器自身限制 | dispatch 内执行前增加 allow/deny 判断 |
| 关联 | 一次动作结果 | `run_id`、父子 span、`call_id` |
| 记录 | 基本运行结果 | Pre/Post hook、权限与工具状态 |
| 验收 | 任务输出 | 文件、输出、轨迹与四种 SDK 样本 |

上游 s02 的处理器表、s03 的交互批准和 s04 的通用 hook，与本课实现有明确差异，详见[源码对应](source_walkthrough.md)。数据的开发、校准和留出划分见[数据集清单](dataset_manifest.json)。本课只使用五条开发任务；其余两类未执行，不计入历史通过率。

## 试一下

先在宿主机启动模型桥：

```sh
python3 tools/model_bridge.py
```

另开终端执行：

```sh
docker compose up --build -d
docker compose run --rm -T course run-e02 --case edit_and_run
docker compose --profile verify run --rm -T verifier verify-e02 --run-id 实际run_id
python3 tools/run_e02.py
```

第二条命令会输出实际 `run_id`。把它原样填入验收命令。重跑默认在 `runs` 中创建新报告，不会覆盖固定示例。

工具在 Docker 容器内执行，宿主机 Codex 只负责返回动作。独立 verifier 断网运行，工作目录只读，并通过私有挂载读取验收标准；凭据和私有标准不会进入 Agent 容器。本课的知识库仍然不参与检索。

第一次保存的实验中，修改任务实际输出48，权限任务保留被拒绝的调用，错误任务则留下预期的异常。完整五条任务、工具状态和 SDK 往返结果放在[历史运行摘要](run_summary.md)与[固定报告](example_report.json)。本次重写沿用它们，没有重新测量 Agent。

错误任务的成功条件正是观察到文件异常和脚本非零退出，同时保留原脚本。读报告时先看任务要求，再判断 `error` 是否属于预期结果。

运行后，可以在报告中回答三个观察题：

1. `edit_file` 的 `parent_id` 指向哪个 `model-N`？它的 Pre/Post hook 是否使用相同 `span_id`？
2. `invalid_arguments`、`denied` 和 `error` 分别停在哪一层？哪些状态实际进入了 `execute`？
3. 把两个工具事件交换后，`trace_errors` 会报告什么？为什么它仍不能证明任意 `stdout` 为真？

接着做[练习](exercises.md)，完成后再看[参考答案](solutions.md)。需要追踪完整实现时，按[工具与循环](code.py)、[轨迹和样本适配](samples.py)、[独立验收](eval.py)的顺序阅读；框架字段、源码版本和边界说明都在[源码导读](source_walkthrough.md)。

## 接下来

现在，我们可以沿一份记录找到具体调用、权限决定与返回结果，并把它转成两个框架的样本。第3课开始给这些样本评分：先用规则检查明确条件，再让 LLM 裁判判断解释的含义，并检查两种方法为什么会给出不同结论。
