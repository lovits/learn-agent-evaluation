# e01 源码导读：成功条件写在哪里

[教材](README.zh.md) · [循环](code.py) · [评分器](eval.py)

## 先找两个入口

`code.py:main` 读公开任务，创建新目录，调用 `agent_loop`，保存运行报告。`eval.py:main` 读这份报告与任务规则，调用 `evaluate`，保存逐项判断。

两者之间传的是实际运行结果。`evaluate` 不调用模型，也不运行 Agent 生成的程序；它读执行事件和文件。Docker 中评分进程的工作目录挂载只读，评分标准不挂给 Agent。

| 位置 | 顺着什么读 |
|---|---|
| [code.py](code.py) | `load_cases → main → agent_loop` |
| [runtime.py](../../eval_course/runtime.py) | `call_model`、`run_bash`、`prepare_workspace` |
| [eval.py](eval.py) | `main → evaluate → check_rule` |
| [run_e01.py](../../tools/run_e01.py) | 先执行任务，再启动独立评分容器 |

`runtime.py` 收拢了传输和进程细节，供各课复用。原有导入入口仍可用；本课核心是 `agent_loop` 的请求、执行、回填和停止。

## 循环里的数据

`messages` 是模型可见历史。`events` 是运行记录，保留模型响应与 Bash 的命令和结果。只有执行框架写入的 Bash 事件，才能提供本课需要的动作证据。

`call_model` 调用宿主模型接口，检查返回的 `answer`、`tool_calls` 和命令结构。本机 Codex 只提供结构化响应，其自身工具关闭；实际命令由课程容器执行。

`run_bash` 保留输出、退出码、超时状态与截断标记。工具报错也回填模型。`prepare_workspace` 创建新目录、写入初始文件，拒绝越出该目录的初始路径。

独立目录防止旧文件混入；进程工作目录和教学阻断词表不是完整的 Bash 权限边界。这里不把教学执行器当成通用安全隔离方案。

## 评分器读哪些证据

`evaluate` 先检查正常停止和实际 Bash 事件，再按 `criteria["checks"]` 调用 `check_rule`。

| 规则 | 证据 | 能说明什么 |
|---|---|---|
| `successful_stdout_contains` | 退出码为0的对应 stdout | 某次成功命令输出了指定文字 |
| `error_contains` | 非零退出的 stderr | 某次命令确实返回了指定错误 |
| `python_ast` | 实际文件的 AST | 文件满足当前指定结构 |
| `file_sha256` | 实际文件内容哈希 | 指定文件内容保持一致 |

`python_ast` 解析文件与参考代码，比较 `ast.dump`。读取前会确认路径位于当前目录内。语法错误或无法解码不会通过。AST 相同不等于通用行为正确；stdout 命中也不保证某个特定命令来源。因此本课规则用于演示任务合同，不声称能抵抗任意投机。

汇总中 `score = 通过项数 / 全部项数`，`passed = all(逐项判断)`。规则权重相同，诊断比例依赖你写了多少条规则，跨任务不能直接当作可比的能力分。

## 对照 Learn Claude Code

固定版本的 [s01 agent_loop](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/code.py) 在没有 `tool_use` 时返回；有调用就执行 Bash，把 `tool_result` 放回消息。

本课沿用这个循环。JSON 动作适配不同模型入口，增加步数上限和必要记录，再把任务评分放到循环之外。运行状态描述执行停在哪里，任务规则描述结果是否满足要求。

## DeepEval：预期、实际运行与指标

先看 [Golden](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/golden.py) 和 [LLMTestCase](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/llm_test_case.py)。前者保存输入与预期，后者携带待评分的实际输出及相关字段。预期结果不能填成“实际运行已经做到”。

再读 [evaluate](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)：

1. `validate_evaluate_inputs` 校验样本与评分配置。
2. 根据配置进入同步或异步执行分支，将样本交给指标。
3. 汇集逐样本结果。选择什么指标，才决定怎样定义“好”。

对照[官方评测入门](https://deepeval.com/docs/evaluation-introduction)，本课任务、报告和规则分别承担预期、实际记录和评分标准的职责。文件规则是本课自己的实现，没有调用 DeepEval 原生指标。

## Ragas：一行任务怎样得到结果

读 [Dataset](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset.py) 与 [experiment.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)。`ExperimentWrapper.arun` 为数据行调用被装饰函数，将返回结果收进 `Experiment`。

这个调度器不会替你定义“hello.py 写对了”。被装饰函数需要调用应用，并明确计算或携带评价结果。业务评分来自你选用的规则或指标。

[官方实验概念](https://docs.ragas.io/en/stable/concepts/experimentation/)解释数据集、实验函数和评价的关系；[指标概览](https://docs.ragas.io/en/stable/concepts/metrics/overview/)解释端到端与组件评价。本课同样先运行、后评价，尚未调用 Ragas 原生指标。

下一课才把运行记录转换成两框架的实际样本类型。本课先把一个前提立住：评分需要独立、可追溯的实际输入。
