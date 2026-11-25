# e02: 一次运行，一份样本：怎么把动作过程留给评测？

[e01](../e01_success/README.zh.md) → `e02` → [e03](../e03_datasets/README.zh.md) → … → e16

> *“只看最终回答，分不清哪次成功写入、哪次被权限拦下；要把动作名字、参数和执行结果一起留成样本。”*
>
> **评测层：运行样本。** 给工具调用命名并校验路径权限，把每次执行记录转换进 DeepEval 的 `LLMTestCase` 与 `ToolCall`。

## 问题

上一课能让 Agent 创建文件，也能核对文件是否符合要求。现在把两次运行摆在一起：它们最后都回答“完成”，其中一次正确写入，另一次写入因为路径越界被拒绝。

只看最终回答看不出差别。要评价 Agent 的执行过程，就需要把每一步调了什么工具、传了什么参数、实际执行是成功还是被拦截，按顺序完整留下来，并转换成评测框架能直接读取的样本结构。

## 解决方案

把零散的 Shell 命令升级为具名工具，在执行前做路径权限检查，把工具名、参数和带状态的返回结果写入同一条事件记录，再由独立的转换函数把这份记录导出为 DeepEval 的 `LLMTestCase`。

![模型与工具之间的循环](https://lovits.github.io/learn-agent-evaluation/diagrams/e02-agent-loop.svg?v=7009ab402637)

循环与转换各自负责不同环节，评分器则从同一份运行记录和磁盘产物取证：

![运行记录、产物与独立评分](https://lovits.github.io/learn-agent-evaluation/diagrams/e02-evaluation-path.svg?v=88f185703e0b)

## 工作原理

### 从命令到具名动作

上一课读文件靠拼接 `cat source.txt`。换成具名工具后，模型的意图可以直接表达为结构化调用：

```python
{"name": "read_file", "arguments": {"path": "source.txt"}}
```

本课保留 `bash`，再加入 `read_file` 和 `write_file`。虽然这两个操作都能用 Bash 完成，但具名参数让运行记录更易解读，也给文件路径权限留出了明确的检查入口。模型负责提出动作，实际执行结果仍由执行框架决定。

### 工具分发

[tools.py](tools.py) 用一张处理函数映射表分发工具调用：

```python
HANDLERS = {
    "bash": run_bash,
    "read_file": read_file,
    "write_file": write_file,
}
```

执行时按名字查表并解包参数：

```python
output = HANDLERS[name](workspace=workspace, **arguments)
```

工具定义向模型声明可用的名字和参数结构，处理函数负责在工作目录内执行。循环里的“请求、执行、回填、判停”保持不变，完整代码见 [code.py](code.py)。

模型返回的参数以 `arguments_json` 字符串传输，进入循环后通过 `json.loads` 还原成字典。运行记录直接保存还原后的参数字典，后续分析时不用再从命令字符串里反推意图。

### 执行前校验权限与状态分级

具名文件工具执行前，先解析目标路径是否落在工作目录以内：

```python
target = (workspace / path).resolve()
if not target.is_relative_to(workspace.resolve()):
    raise PermissionError("Path is outside the workspace")
```

因此 `write_file("../outside.txt", ...)` 在写入磁盘前就会被拦截。这条路径边界约束作用于具名文件工具，`bash` 沿用上一课的教学执行器。

[execute](tools.py) 会把每次调用的返回归类为明确的状态：

| 状态 | 发生了什么 |
|---|---|
| `ok` | 工具正常执行并返回结果 |
| `denied` | 权限检查拒绝，动作未执行 |
| `invalid` | 工具名或参数不符合接口定义 |
| `error` | 执行过程中出错，例如目标文件不存在 |

`bash` 还会按需返回 `blocked` 或 `timeout`。这些状态全部由执行框架写入，模型在最终回复里说“写好了”，也不会改变记录里的 `denied`。

### 把动作与结果写入同一条事件

循环每执行完一个动作，立刻把它记入 `run["events"]`：

```python
run["events"].append(
    {
        "id": f"{step}.{index}",
        "name": call["name"],
        "arguments": arguments,
        "result": result,
    }
)
```

`step` 表示第几次模型响应，`index` 表示这一批工具调用里的序号，两者组合标识单次动作的位置；外层的 `run_id` 标识整次运行，公开任务的 `id` 在报告中记为 `case_id`。同一任务重复执行时，每次都会分配新的 `run_id`。

按发生顺序保存下来的事件列表，就是轨迹的最小形态。工具返回同时回填给模型上下文：`run["events"]` 记录真实发生的执行过程，`messages` 记录模型在每一轮实际看到的反馈。

### 从运行记录导出 DeepEval 样本

[samples.py](samples.py) 专门负责把已保存的运行记录转换成 DeepEval 的 `LLMTestCase`：

```python
LLMTestCase(
    input=run["task"],
    actual_output=run["final_answer"] or "",
    tools_called=[
        ToolCall(name=e["name"], input_parameters=e["arguments"], output=e["result"])
        for e in run["events"]
    ],
)
```

每条事件里的 `result`（包含 `ok`、`denied`、`error` 等状态）都原样写入 `ToolCall.output`。因此 `tools_called` 反映的是“模型提出并经过执行框架处理的完整调用列表”，判断动作是否真正成功需要结合 `output` 里的状态字段来看。

样本对象承担的是“结构化输入”的职责：构造 `LLMTestCase` 校验字段格式，而任务是否通过仍由独立评分逻辑判定。外层记录继续保留 `run_id` 和运行状态；当模型没有给出最终回答时，`actual_output` 保持空字符串。

## 本课变化

| 部分 | e01 | e02 |
|---|---|---|
| 动作形态 | 原始 Bash 命令字符串 | 具名工具与结构化参数 |
| 执行方式 | 直接调用 `run_bash` | 查表分发，文件工具校验目录边界 |
| 运行记录 | 命令文本与返回结果 | 调用位置、工具名、参数字典与带状态的结果 |
| 评测样本 | 仅保留课程内部运行字典 | 从同一运行记录导出 DeepEval `LLMTestCase` 与 `ToolCall` |

[eval.py](eval.py) 继续独立核对工作区文件和关键事件：先检查模型正常停止、存在工具调用、目标文件内容正确等通用条件，再按任务类型核验是否观察到成功读取或权限拒绝，同时把导出好的样本附在返回结构中。

## 试一下

运行本课的 `copy` 任务：

```sh
python -m course.run e02 --case copy
```

动手验证四个问题：

1. 运行 `copy` 任务（读取 `source.txt`、写入 `result.txt` 再读回），沿着 `run["events"]` 找出三个动作的参数和结果。
2. 运行 `denied` 任务，观察 `write_file` 越界写入被拒绝后再写目录内文件。记录里的哪些字段说明“尝试过”，哪些字段说明“没有执行”？
3. 设想去掉某条事件的 `result`，只留下任务和最终回答。哪些检查还能做，哪些判断已经失去证据？
4. 同一任务运行两次，对比 `case_id`、`run_id` 和事件 `id` 各自标识什么层级。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

现在我们已经能把单次运行沉淀成标准的 `LLMTestCase` 样本。但只跑一两条临时题目，很难判断改动到底让 Agent 变好了还是退步了。

下一课 `e03` 转向评测集本身：挑选值得反复运行的任务，用 DeepEval 的 `Golden` 与 `EvaluationDataset` 管理题目、参考信息与数据划分。
