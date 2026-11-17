# e02 源码导读：工具事件怎样变成样本

[教材](README.zh.md) · [工具与循环](code.py) · [样本适配](samples.py)

## 从 dispatch 进入

```text
validate_call → permission → execute
                              ↓
                     event + Pre/Post hook
                              ↓
                       trace_errors
                              ↓
                       native_samples
```

`execute` 按工具名分支。上游 [s02](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s02_tool_use/code.py) 用 `TOOL_HANDLERS` 查表，分发职责相同；本课没有加入可选的读取行数参数。

[s03](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s03_permission/code.py) 在执行前检查权限；[s04](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s04_hooks/code.py) 提供 hook 接入点。本课直接记录这些位置，每个请求都有 Pre/Post 配对，包括参数错误与拒绝，便于追踪。

路径先 `resolve` 再检查边界，防止文件链接绕出工作区。Bash 保留自己的执行状态；拒绝和执行失败不能互相改写。

## 一条轨迹有三层身份

`run_id` 是整次任务；`model-N` 是一次模型响应；`model-N:tool-i` 是其中一个请求。`trace_errors` 按这些身份与原始动作核对结果顺序，同时检查 hook 覆盖。

关联正确只能证明记录自洽。若要判断操作是否达成目标，还要读取实际文件或业务状态。

## DeepEval 的嵌套类型要恢复

[样本文档](https://deepeval.com/docs/evaluation-test-cases)与 [llm_test_case.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/llm_test_case.py) 一起看。`ToolCall` 保存 `name`、`input_parameters` 与 `output`。固定版本的前置校验要求 `tools_called` 中已经是 `ToolCall` 实例，所以 JSON 恢复时，`restore_samples` 先恢复嵌套对象。

[ConversationalTestCase](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/conversational_test_case.py) 的 `Turn` 采用 user/assistant 角色。工具输出留在对应 assistant 的 `ToolCall.output`，不另造一个 tool 角色。

[原生 tracing](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/tracing/tracing.py) 则用 `parent_uuid` 挂接子节点，必要时修复暂时找不到父节点的 span。本课先用本地事件解释归属，原生 trace 在计划课接入。

## Ragas 的多轮样本保留消息顺序

[dataset_schema.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset_schema.py) 中，`SingleTurnSample` 保存一次问答；`MultiTurnSample` 保存 `HumanMessage`、`AIMessage` 和 `ToolMessage` 列表，并校验工具消息之前的调用关系。

[messages.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/messages.py) 的工具请求使用 `name/args`。独立关联 ID 放在消息 metadata，原始事件仍然保留；后续指标未必读取这个 metadata。

框架对象能成功构造，只表示结构符合要求。指标还可能要求 reference、检索证据或预期工具，参见[Ragas 样本概念](https://docs.ragas.io/en/stable/concepts/components/eval_sample/)。

## 转换时别提前丢信息

`native_samples` 保留所有请求及状态，包括无效和被拒绝的请求。不同评分器再按目的投影。评工具选择时看请求，评执行可靠性时看实际运行，评任务完成时看最终状态。

开发、校准和留出划分用于不同阶段；同一任务的近似变体应按题族隔离。数据集课会继续展开这件事。
