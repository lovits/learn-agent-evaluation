# e02 源码导读：从运行记录到 SDK 样本

[教材](README.zh.md) · [循环](code.py) · [工具](tools.py) · [转换](samples.py)

## 本课调用链

`agent_loop → execute → HANDLERS` 执行动作。`execute` 将拒绝、参数错误和执行错误分别返回，循环把结果同时写入事件和工具消息。`to_deepeval` 只读取已有记录，生成一份 DeepEval 样本。

事件编号标记一次运行内的模型步和动作位置。一个用户任务可以触发多次模型响应；以整次任务作为单个端到端样本，并不要求 Agent 只调用一次模型。

## Learn Claude Code：分发与权限

固定版本的 [s02](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s02_tool_use/code.py) 用工具表分发调用，[s03](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s03_permission/code.py) 在执行前处理权限。

本课取其中最小部分：三个处理函数、文件路径检查和事件列表。没有独立审批系统，也没有完整追踪平台。`resolve` 后检查目录范围可识别静态符号链接越界，但不提供并发攻击下的文件系统隔离；Bash 也不受这个文件函数约束。

## DeepEval：调用记录保留在哪里

[官方样本说明](https://deepeval.com/docs/evaluation-test-cases)给出输入、实际输出和工具字段。核对固定版本的 [LLMTestCase 与 ToolCall](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/llm_test_case.py)：`ToolCall` 保存名字、输入参数和输出，`LLMTestCase.tools_called` 携带调用列表。

`to_deepeval` 将实际事件逐条转换。没有写入 `expected_tools`，因为实际调用不能同时充当参考调用。工具输出中的状态是本课显式编码的内容，不代表所有原生指标都会自动判断权限和执行成败。工具质量一课会检查相应指标究竟读了哪些字段。

原生 trace 入口见 [tracing.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/tracing/tracing.py)。本课位置编号只承担轻量归属，没有冒充框架的 trace/span 对象。

## Ragas：样本为何需要过程信息

[官方样本说明](https://docs.ragas.io/en/stable/concepts/components/eval_sample/)区分单轮问答与多轮过程。固定版本的 [dataset_schema.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset_schema.py) 定义样本字段与消息校验；[messages.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/messages.py) 将 AI 调用与工具反馈分开表示。

这里借它理解一个原则：评测过程，需要保留过程证据。只有任务与最终回答，就无法判断中间是否被拒绝、调用是否出错。本课用原始消息与事件保存这些证据，实际接入只使用 DeepEval。

## 转换没有改变哪些事实

外层仍保留 `run_id`、运行状态和原始事件。停止或模型错误不会因为成功创建了 SDK 对象就变成任务完成。没有最终回答时使用空字符串，是满足文本视图的表示方式；评测选择仍应检查外层状态。

本课实际调用了 SDK 构造和校验，没有运行 LLM 裁判或框架质量指标。文件任务由 [evaluate](eval.py) 独立检查；样本表示与质量评分的边界在这里可以直接看见。

任务入口在 [course.run](../run.py)，它读取本课样本、创建本次目录并调用循环；[course.grade](../grade.py) 根据运行编号读取结果，再进入本课评分函数。

[样本与评测记录](assessment.md)
