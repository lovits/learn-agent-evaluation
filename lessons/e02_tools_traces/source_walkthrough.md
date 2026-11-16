# 第2课源码导读

这课沿着一次工具调用读代码：模型提出动作，运行时检查参数和权限，工具返回结果，最后把记录转换成框架样本。建议先跑一条任务，再按这个顺序读。

## 原版 Learn Claude Code 到本课

固定版本为 `448c75bb596917ad196cc1fb7558f459c5c50fdd`。

- [s02 工具分发](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s02_tool_use/code.py)：`TOOL_HANDLERS` 把名字映射到函数；`agent_loop` 根据 `block.name` 选函数，把结果关联到 `tool_use_id`。本课保留 Bash、read_file、write_file、edit_file、glob 五种工具。edit 只替换第一处；glob 按名字排序，最多展示200项。
- [s03 权限](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s03_permission/code.py)：`check_permission` 先查 deny list，再查规则，需要确认时走 `ask_user`。本课的 `permission` 保留“直接允许、硬拒绝、请求批准”的分支；批量实验中的批准回调固定拒绝，单元实验另测显式批准。目录外文件访问直接拒绝，比上游交互策略严格。
- [s04 hooks](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s04_hooks/code.py)：上游在 UserPromptSubmit、PreToolUse、PostToolUse、Stop 触发回调。本课直接在这几个位置记录事件，暂不搭建通用插件注册系统。为方便统计，每次请求，包括拒绝和参数错误，都会留下 Pre/Post 配对；上游拒绝后直接 continue，不会走执行后的 Post hook。两者语义有这处区别。

本课新增代码在 [code.py](code.py)。只从第1课复用 Bash 执行器和练习目录准备函数；没有检索、记忆、计划、子Agent。文件工具先讲必需参数，未加入上游 read_file 的可选 limit。此处验证的是本课列出的操作合同，不能据此宣称完整上游等价。

## 从参数到执行结果

`validate_call` 解析 `arguments_json`，核对工具名、参数集合和字符串类型。把参数写成 JSON 字符串，是本机模型入口的传输方式；分发前会还原成字典。

`permission` 在执行前解析文件路径。符号链接也要 resolve，再判断是否越出工作目录。Bash 的阻断词和危险命令判断只覆盖教学例子，不能把它当成完整的 shell 安全分析器。Bash 仍能使用容器内的其他路径；Docker 不挂载宿主机代码目录或登录凭据，验收标准也不放进 Agent 镜像。

`dispatch` 分开返回权限结论与工具结果。缺参数是 invalid_arguments，文件不存在是 error，权限不通过是 denied。Bash 保留 stdout、stderr、exit_code 和 timeout，不把它们压成一句“调用失败”。

## 轨迹怎样找到所属模型调用

每次模型响应有 `model-N`；该响应中的第 i 个工具有 `model-N:tool-i`，其 parent_id 指向这个模型。run_id 区分不同实验，因此 span_id 在一次实验内唯一即可。结果消息也携带 call_id。

[samples.py](samples.py) 的 `trace_errors` 逐个核对调用顺序、父节点、动作内容以及 hook 配对，再允许转换。交换两个工具事件，或者漏记一个 PostToolUse，都会使轨迹合同失败。它检查记录的内部一致性，无法证明被恶意篡改的记录可信；文件和输出还要由独立验收器检查。

## DeepEval：构造样本之前先读校验器

固定版本 `34db63dd005ebc9a905c8ef4741ae0687c93c14c`（4.3.4）。

- [官方单轮样本说明](https://deepeval.com/docs/evaluation-test-cases) 解释 input、actual_output、expected_output、retrieval_context 与 tools_called 的含义。文档中有关于 actual_output 必需性的不同表述；当前源码字段默认可空。本课要求完成记录有字符串 final_answer，再填 actual_output。具体指标需要哪些字段，要在第3课按指标另查，构造对象成功并不代表所有指标都能运行。
- [LLMTestCase 与 ToolCall](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/llm_test_case.py)：ToolCall 保存 name、input_parameters、output；LLMTestCase 的 before `validate_input` 要求 tools_called 已经是 ToolCall 实例。直接把 model_dump 后的工具字典重新传进去，会触发 TypeError。因此 `restore_samples` 先恢复嵌套 ToolCall，再创建样本。这个分支有真实 SDK 往返测试。
- [Turn 与 ConversationalTestCase](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/conversational_test_case.py)：Turn 的角色是 user/assistant；本课把工具返回保存在对应 assistant Turn 的 ToolCall.output，不虚构一个 tool 角色。单轮视图合并所有请求，多轮视图保留各次模型响应。
- [Tracing 实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/tracing/tracing.py)：`TraceManager.add_span_to_trace` 用 parent_uuid 找父节点并挂到 children；父节点尚未到达时，还会通过 `_reparent_orphan_roots` 修复树。这说明只保存工具名不够。本课先用本地 parent_id 解释归属，没有调用 observe 或上传云端原生 trace。
- [Tracing guide](https://deepeval.com/guides/guides-tracing-ai-agents) 区分 agent、llm、tool、retriever span。本课只有前三种职责，没有 retriever。

## Ragas：消息序列要满足什么条件

固定版本 `8c63f10d500c44efbf24fdb9e2920de2104c321c`（0.4.4）。

- [官方样本说明](https://docs.ragas.io/en/stable/concepts/components/eval_sample/) 区分 SingleTurnSample 和 MultiTurnSample。前者承载一次任务的输入与最终回答；后者保留 Human、AI、Tool 消息序列。
- [dataset_schema.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset_schema.py)：SingleTurnSample 的 user_input、response、reference、retrieved_contexts 都可空。MultiTurnSample 的 user_input 是消息列表，`validate_user_input` 会检查 ToolMessage 前是否已有 AIMessage、相邻消息顺序以及工具调用信息。框架做结构检查，本课再加 call_id 和顺序合同。
- [messages.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/messages.py)：ToolCall 使用 name/args；它没有本课所需的独立 call_id 字段。我们把关联 ID 写入 AIMessage 和 ToolMessage 的 metadata，原始记录也继续保留。不能假定后续每个指标都会读取这些 metadata。

## 统一样本保留什么，省略什么

[eval.py](eval.py) 在无网络的独立容器中构造四种原生 SDK 对象，导出 JSON，再恢复对象。验收标准只挂载给这个容器。原始轨迹、转换结果和评分放在同一份报告中，方便逐字段核对。

| 本课事实 | DeepEval | Ragas |
|---|---|---|
| 任务输入 | input | 单轮 user_input / 多轮 HumanMessage |
| 最终回答 | actual_output | response / 最后一条 AIMessage |
| 预期答案 | expected_output | reference |
| 工具动作 | ToolCall(name, input_parameters) | ToolCall(name, args) |
| 工具结果 | ToolCall.output | ToolMessage.content |
| 检索证据 | retrieval_context | retrieved_contexts |

本课没有检索证据，也没有给最终中文答案制定语义 reference，相应字段保持 None。文件读取结果属于工具输出，不能为了凑字段塞进 retrieval_context。工具请求中包含被拒绝和无效请求，其状态保存在 output、消息内容及外层 metadata。计算后续工具指标时，必须先说明是在评请求、执行还是成功执行；不能把这些数量混在一起。

五条实测都是 development 集，用于调试。另有2条 calibration 和2条 holdout，完整任务与验收标准放在 evaluation_private，未执行，也不进入 Agent 镜像。dataset_manifest.json 记录划分、数量和文件哈希。这个小数据集用于说明隔离方法；正式比较版本还应扩展任务族，防止同一个模板的变体跨集泄漏。
