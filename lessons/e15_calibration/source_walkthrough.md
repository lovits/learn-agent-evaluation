# 第15课源码导读：评分器也需要验收

本课复用第14课已经完成的Agent机制，没有增加或改动Agent工具。新代码只负责固定报告、裁判配置、隔离数据和比较判分。样本中的业务数值与检查记录为讲师构造，不是新的Agent执行，也没有人工投票。范围与文件哈希见[选读清单](../../references/e15-reading.json)，实验顺序见[冻结协议](../../references/e15-experiment-protocol.json)。

## 先认清三个接口层次

| 做法 | 实际改变了什么 | 本课执行情况 |
|---|---|---|
| DeepEval `GEval(evaluation_steps=...)` | 明确评分步骤；阈值把连续分数变成通过/失败 | 比较两版开发集结果，选择后评留出集 |
| Ragas `DiscreteMetric.align(...)` | 把训练标签加入动态少样本提示 | 使用原生无向量回退：最近四个示例 |
| Ragas `BasePrompt.adapt(...)` | 翻译示例，按需翻译指令 | 原始与中文提示使用相同schema，在相同四个样本上比较 |

它们都没有更新模型权重。`align`、prompt优化器和模型微调不能互相替代。本课没有运行Ragas全套优化器，也没有宣称用向量检索挑选相似示例。

## 1. 样本与隔离：先分家族，再改写

[code.py](code.py)的 `make_cases` 生成16条记录，训练4条、开发4条、留出8条；同一个家族的正确、错误、长篇和英文版本保留在同一个split。`validate_cases` 拒绝重复ID、跨split家族和违反规则合同的标签。

这里的合同很窄：报告写出的数值与“独立检查是否通过”必须同时匹配给定记录。检查未通过时，诚实说明失败的报告仍是准确报告；它不代表修复任务完成。标签来自构造器的明确字段，不是让同一个裁判先出答案再给自己打标签。

`judge_input` 只发送任务、预期值和检查状态；不发送 `label`、`reported_fields`、split和人工审核字段。裁判必须看见评分所需的证据，这与把参考标签直接塞给它是两回事。由于教材作者知道构造方法，本实验不宣称对作者盲测；隔离保证留出结果不参与选择步骤。

## 2. DeepEval：从输入检查到连续分数

固定版本：[g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)。

调用链：`score` → `GEval.measure` → `_validate` → `_generate_evaluation_steps` → `_evaluate` → `generate_rubric_score` → `DeepJudge.generate` → 宿主裁判桥 → `ReasonScore` → 范围归一化 → 本课0.7阈值。

- `_validate` 根据 `evaluation_params` 检查 `LLMTestCase`。本课传 `INPUT` 与 `ACTUAL_OUTPUT`；没有混入与标准无关的字段，也没有让指标推断trace模式。
- `evaluation_steps` 已明确指定，因此不额外请求模型生成步骤。v1要求“有用、可信的完成报告”，v2把两项事实、失败报告、等义语言和无关篇幅写清。v1是刻意欠明确的教学基线。
- schema中的 `score` 是浮点数，`reason` 是字符串。本课仍核对结果有限且位于0至1，协议错误保留为未评分。
- 原生通用评分函数优先尝试raw response与logprobs；不支持时进入schema生成分支。本课沿用第3课的自定义适配器，没有实现raw/logprob接口，因此不能宣称进行了token概率加权。参数叫 `top_logprobs` 也不等于供应商真的返回了它。
- `measure` 在本课设置 `async_mode=False`；不同样本的四路并发由外层线程池负责。原生 `a_measure` 对应异步步骤生成与异步评分，接口行为与本课同步入口要分开理解。
- 自定义后端的原生 `evaluation_cost` 不代表账单。原始成功响应另存usage；精确模型版本和价格未知就保留为空。

官方[G-Eval文档](https://deepeval.com/docs/metrics-llm-evals)用于核对显式步骤和自定义模型路径。固定步骤能减少变化来源，不能保证裁判确定性或与人类完全一致。

## 3. Ragas：离散结果与少样本对齐

固定版本：[discrete.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/discrete.py)、[base.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/base.py)。

调用链：`metric` → `DiscreteMetric.__post_init__`构造 `Literal["pass","fail"]` schema → `SimpleLLMMetric.score` 格式化提示 → `StructuredJudge.generate` → 原生schema校验 → `MetricResult(value, reason, traces)`。本课的适配器只承担传输和schema输出，不代替Ragas构造评分提示。

`ascore` 使用 `llm.agenerate`，结果同样进入 `MetricResult`；不是把 `score` 返回的字符串自行包装成“原生异步评测”。本课正式对齐调用同步API，异步适配器用于原生提示翻译。

`align` 从训练Dataset读取prompt变量、`report_accuracy`与`report_accuracy_reason`，加入 `DynamicFewShotPrompt`。它不请求裁判，本课传 `embedding_model=None` 触发源码已有的最近示例回退；`max_similar_examples=4` 控制示例数。不能把“最近”写成“最相似”。

这版源码对有 `embed_query` 的旧适配器创建只暴露 `embed_text` 的wrapper，而示例库又调用 `embed_query`。本课用0模型测试复现接口不一致，正式实验使用可工作的原生回退路径，不暗改上游代码。

`validate_alignment` 会逐行评分，再计算agreement与Cohen's κ，返回DataFrame。κ依赖额外的scikit-learn，本项目已加入并锁定。源码分别过滤参考值和预测值中的None，缺失位置不一致时可能错配；教材自己的 `alignment` 始终按同一ID成对保留，错误计入覆盖率，不能静默当失败或从分母里消失。κ在单一类别完全一致时可能无定义，本课的规则汇总返回null，不写NaN。

官方[对齐指南](https://docs.ragas.io/en/stable/howtos/applications/align-llm-as-judge/)用现成回答与人工标签比较。本课保留这个流程，但参考标签明确为构造合同标签；没有人工复核就不能称“人工对齐已通过”。训练、开发、留出集各有用途，也不能把同一家族改写后分散出去。

## 4. 中文适配：翻译的是文字，不是判分含义

固定版本：[BasePrompt](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/prompt/metrics/base_prompt.py)。[官方语言指南](https://docs.ragas.io/en/stable/howtos/customizations/metrics/metrics_language_adaptation/)描述collections指标prompt属性的 `adapt`。它不是旧版 `adapt_prompts`，也不能直接套用在所有指标类上。

调用链：`ReportPrompt.adapt` → `get_all_strings(examples)` → `_translate_strings` → `StructuredJudge.agenerate` → 翻译条数检查 → `update_strings` → 深拷贝prompt → 可选指令翻译。

本课示例使用数字0/1作为输出枚举，避免把可翻译的自然语言标签与固定schema枚举混在一起。指令和reason可翻译，数值、布尔值、字段结构、数字标签仍保持原合同。原生代码检查返回条数；数值与schema不变也不足以证明语义无漂移，最终仍需复核否定词、范围和例外。

源码在示例为空时提前返回，只更新language，即使 `adapt_instruction=True` 也不翻译指令。测试确实覆盖该路径和翻译条数错误。正式实验有两个示例，预期一次示例翻译、一次指令翻译；所有实际响应保留。

## 5. 偏差诊断和选择后的验证

`select_version` 只读取开发结果。候选必须完整评分，再优先避免误放行、比较agreement，同分选预先写好的v2。选择记录先落盘，随后才调用留出评分；没有根据留出结果继续改prompt。

成对比较用原生 `DiscreteMetric` 返回A、B或tie，再映射回固定内容ID。交换后都选A不算一致；应比较是否仍选同一份内容。顺序一致也不代表选择正确，因此同时检查是否选择准确报告。

长篇错误报告与“声称来自同一模型”的报告也做交换。后者只是作者身份线索测试：真实模型身份未公开，内容是讲师构造，无法证明真正的模型自偏好。偏差分类参考[MT-Bench论文](https://arxiv.org/abs/2306.05685)，没有把论文中的一致率搬成本课结果。

两家框架的对象、prompt、连续/离散输出和结果聚合不同；本课可以比较它们在同一合同标签上的行为，不能把相同的分数名称当成相同测量。全部逐样本分数、理由和调用输入见[运行记录](run_summary.md)。
