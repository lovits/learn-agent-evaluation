# e01 源码导读：完成声明与完成证据

[教材](README.zh.md) · [循环](code.py) · [评分](eval.py)

## 本课调用链

命令行入口在 [course/run.py](../run.py) 与 [course/grade.py](../grade.py)：

1. `course.run` 从 `cases.jsonl` 读取题目描述，创建干净的本次工作目录，防止上一轮残留文件污染当前结果，随后调用 [code.py](code.py) 中的 `agent_loop`。
2. `agent_loop` 维护两份列表：`messages` 负责把工具返回送回模型上下文，驱动下一轮推理；`events` 按 `{step}.{index}` 保存每次命令与结果，留给外部评分读取。
3. 底层的模型请求、子进程超时与输出截断封装在 [runtime.py](../../eval_course/runtime.py) 的 `call_model` 与 `run_bash` 中。`run_bash` 内置的基础危险词拦截仅用于教学防呆，专门的目录边界会在第 2 课交给具名文件工具处理。
4. `course.grade` 根据 `run_id` 取出保存好的运行记录和对应工作目录，交给 [eval.py](eval.py) 的 `evaluate` 做独立检查。

`evaluate` 里的两项核心检查各有明确边界：`ast.dump(ast.parse(...))` 适合核对本题要求的单条 `print` 语法结构，但不能用来证明任意两段复杂代码在运行行为上等价；`output_observed` 检查某次退出码为 `0` 的命令输出了 `"Hello, World!"`，它必须和 `requested_file` 联合判定，才能排除“只跑 `echo` 不写文件”的取巧路径。更通用的程序行为契约会在第 12 课展开。

## 对照 Learn Claude Code

对照上游固定版本的 [s01_agent_loop/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/code.py)，两者的内核完全一致：把消息发给模型，有工具调用就执行并把结果追加回消息列表，没有工具调用就退出循环。

差别只在于本课多做了一步留痕：每次 `run_bash` 返回后，除了更新 `messages`，还把命令与真实返回写进 `run["events"]`，并在退出时明确区分 `finished`、`step_limit` 与 `model_error` 三种状态，让循环外面的评分器有据可查。

## 对应 DeepEval 的三个核心角色

虽然这一课只用二十行 Python 函数打分，但代码里的职责划分直接对应 [DeepEval 评测架构](https://deepeval.com/docs/evaluation-introduction)中的三个核心对象：

- [Golden](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/golden.py)：保存待测任务输入（`input`）与预期标准（`expected_output` 等），对应本课 `cases.jsonl` 里的题目定义，在 Agent 运行前就已经确定。
- [LLMTestCase](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/llm_test_case.py)：汇总一次实际运行的输入、`actual_output` 以及工具调用过程，对应本课 `agent_loop` 产出的 `run` 记录。
- [evaluate](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)：驱动指标读取 `LLMTestCase` 并给出分数与通过结论，对应本课独立的 [eval.py](eval.py)。

先把“题目预期、运行证据、独立判分”这三层拆清楚，下一课接入真实的 `LLMTestCase` 与 `ToolCall` 时，每个字段的来龙去脉就会一目了然。

[样本与评测记录](assessment.md)
