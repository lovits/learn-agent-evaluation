# e02: 评测样本 — 把一次调用记完整

[课程](../../README.md) · [上一课](../e01_agent_baseline/README.zh.md) · [下一课](../e03_judges/README.zh.md) · [源码导读](source_walkthrough.md)

> 工具名说明意图，调用记录说明实际发生了什么。

## 一串 Bash 不容易评价

工作区里有 `calculate.py`：

```python
print(6 * 7)
```

任务是把它改成 `6 * 8`，运行，再把输出写到 `result.txt`。

一串 Bash 可以做完这些事。但若要评价“读了哪个文件、改了什么、哪一步被拒绝”，我们需要更明确的动作。因此加入 `read_file`、`write_file`、`edit_file` 和 `glob`，执行程序仍交给 Bash。

循环继续负责调用工具。本课关注怎样把这些动作留下来，形成后续评分器能读懂的样本。

## 工具定义先说清参数

[`TOOL_SPEC`](code.py) 声明每种工具需要什么：

```python
TOOL_SPEC = {
    "bash": {"command": "str"},
    "read_file": {"path": "str"},
    "write_file": {"path": "str", "content": "str"},
    "edit_file": {"path": "str", "old_text": "str", "new_text": "str"},
    "glob": {"pattern": "str"},
}
```

`validate_call` 解析参数并检查字段和类型。之后 `dispatch` 检查权限，最后才进入 `execute`。

```text
工具请求 → 参数校验 → 权限判断 → 执行 → 返回结果
```

读文件时，路径先解析再判断是否仍在工作目录内。`edit_file` 找到旧文本后只替换第一处；找不到就返回错误，不静默写入。

## 拒绝和报错发生在不同位置

| 状态 | 发生了什么 |
|---|---|
| `invalid_arguments` | 参数不符合工具定义 |
| `denied` | 权限不允许，工具没有执行 |
| `error` | 进入工具后出现异常或命令非零退出 |
| `timeout` | 执行超过时间限制 |
| `ok` | 工具按约定返回 |

少传 `path` 与读取不存在的文件，不该记成同一种错误。前者要修调用参数，后者可能需要先查文件。

权限判断还区分硬拒绝和需要批准的动作。批准回调返回允许或拒绝；`approval_required` 只是说明为什么进入批准分支。Bash 的教学规则覆盖有限，完整执行边界还依赖容器配置。

## 两次 read_file 怎样区分

同一轮可能读两个文件。工具名相同，结果却属于不同请求。运行时为模型响应和工具调用分配关联 ID：

```python
model_id = f"model-{step}"
call_id = f"{model_id}:tool-{index}"
hooks.append({"phase": "PreToolUse", "span_id": call_id})
policy, result = dispatch(call, workspace, approve)
```

随后事件一起保存：

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

`span_id` 标识这次调用，`parent_id` 指向提出它的模型响应；`run_id` 区分整次任务。前后 hook 让我们知道动作停在哪一层。

[`trace_errors`](samples.py) 按请求顺序核对结果及 hook。缺结果、错归属、交换顺序都可以发现。它检查记录内部是否一致；实际文件是否正确，仍需另行读取。

## 同一份事实，两套样本

把任务输入与最终回答投影成单轮样本，把交互顺序投影成多轮样本：

| 内容 | DeepEval | Ragas |
|---|---|---|
| 用户任务 | `input` | `user_input` |
| 实际回答 | `actual_output` | `response` |
| 参考答案 | `expected_output` | `reference` |
| 检索证据 | `retrieval_context` | `retrieved_contexts` |
| 工具请求 | `ToolCall` | `AIMessage.tool_calls` |
| 多轮交互 | `ConversationalTestCase` | `MultiTurnSample` |

例如 DeepEval 的单轮构造：

```python
LLMTestCase(
    input=report["task"],
    actual_output=report["final_answer"],
    expected_output=reference,
    tools_called=list(deep_tools.values()),
    metadata=metadata,
)
```

文件读取输出属于工具结果，不能为了填字段放进检索证据。还没有参考答案时保留空值；具体指标需要哪些字段，要按它自己的要求检查。

## 试一下

沿一次 `edit_file` 调用找出参数、权限、父节点和返回结果。然后交换两次工具结果，看看轨迹检查能发现什么。

再读一份被拒绝的请求：它应保留在原始轨迹里。后面统计工具质量时，要先决定评价的是请求、实际执行，还是成功执行。

[工具代码](code.py) · [样本转换](samples.py) · [练习](exercises.md) · [参考答案](solutions.md)

## 接下来

现在一次任务已经能变成结构清楚的样本。下一课开始定义评分标准：哪些条件可以用规则判断，哪些需要理解自然语言。
