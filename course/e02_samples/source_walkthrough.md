# e02 源码导读：从运行记录到 SDK 样本

[教材](README.zh.md) · [循环](code.py) · [工具](tools.py) · [转换](samples.py)

## 本课调用链

命令行入口仍在 [course/run.py](../run.py) 与 [course/grade.py](../grade.py)：

1. `course.run` 读取 `cases.jsonl` 中的任务和初始文件，初始化干净的工作目录，调用 [code.py](code.py) 中的 `agent_loop`。
2. `agent_loop` 沿 `agent_loop → execute → HANDLERS` 链路分发动作。[tools.py](tools.py) 中的 `execute` 将权限拒绝、参数非法和执行出错分别归类返回，循环再把结果同步写入 `run["events"]` 和 `messages`。
3. `course.grade` 根据 `run_id` 取出运行记录和工作目录，交给 [eval.py](eval.py) 做文件与事件核验，同时调用 [samples.py](samples.py) 中的 `to_deepeval` 把已有记录转换为 DeepEval 样本。

事件编号 `{step}.{index}` 标记单次运行内的模型步数和动作序号。一个用户任务往往包含多轮模型响应，把整次任务整理为单个端到端样本时，这些位置编号能完整保留执行顺序。

## 对照 Learn Claude Code

对照上游固定版本的 [s02_tool_use/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s02_tool_use/code.py) 和 [s03_permission/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s03_permission/code.py)，本课保留了最核心的两块机制：按名称查表分发工具，以及在文件读写前做路径边界检查。

这里使用 `resolve()` 配合 `is_relative_to()` 拦截相对路径和静态符号链接越界，作用域限定在具名文件工具 `read_file` 与 `write_file` 内，`bash` 继续复用第 1 课的教学执行器。

## 对应 DeepEval 的样本模型

[DeepEval 官方样本说明](https://deepeval.com/docs/evaluation-test-cases)用输入、实际输出和工具调用描述一次待测运行。对照固定版本的 [LLMTestCase 与 ToolCall](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/llm_test_case.py) 源码：

- `ToolCall` 记录单次工具调用的 `name`、`input_parameters` 和 `output`。
- `LLMTestCase` 通过 `input`、`actual_output` 和 `tools_called` 汇总整次任务的过程证据。

`to_deepeval` 按事件顺序构造 `tools_called`，并将包含状态的返回字典写入 `output`，便于后续区分成功、拒绝与报错。转换时刻意不填充 `expected_tools`，因为实际调用属于“待测行为”，预期工具列表需要从独立的题目定义中提供。

DeepEval 原生的 trace/span 追踪机制位于 [tracing.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/tracing/tracing.py)，本课先用轻量的 `{step}.{index}` 位置编号维护事件归属，完整的追踪与指标评估会在后续课程展开。

## 样本表示与任务评分的边界

导出 `LLMTestCase` 验证的是数据结构是否完整，外层记录依然保留 `run_id`、停止状态和原始消息历史。如果模型因步数超限或接口异常退出，`actual_output` 会记为空字符串，但外层状态仍如实反映 `step_limit` 或 `model_error`。

具体的任务成败由 [eval.py](eval.py) 里的 `evaluate` 独立检查磁盘文件和事件状态，把“数据格式转换”和“质量判分”两条线分开，后续接入各类 DeepEval 评分指标时就能直接复用同一份样本。

[样本与评测记录](assessment.md)
