# 从项目学会 RAG 与 Agent 评测：学习路线与 24 课大纲

这是24课的路线，其中s07已经提供可运行样章，其余课为后续规划。目标读者会 Python、了解 RAG/Agent；以实践能力和关键源码结合为主。贯穿项目为“知识库问答＋工具调用助理”。建议按先修关系推进，预计 40–60 小时，属于工作量估计。

每课增加一个主要评测问题。先用小例子手算或复现，再运行框架，最后沿源码解释结果。DeepEval 与 Ragas 是相互对照的实现材料；相同名字不保证相同评分口径。课程安排是教学设计建议，不等同于官方文档顺序。

| 单元 | 课程 | 学完能做什么 |
|---|---|---|
| 一、先把评测问题定义清楚 | s01–s04 | 从“看起来不错”走到一份可执行的评测协议。 |
| 二、把 RAG 拆成可诊断的指标 | s05–s08 | 解释检索、证据和回答分别出了什么问题。 |
| 三、用评测驱动 RAG 改进 | s09–s12 | 在同一数据集上建立基线、制造失败、扩充样本并做受控迭代。 |
| 四、评测 Agent 的行动与结果 | s13–s16 | 把最终回答、工具行为、真实状态和多轮表现分别评清楚。 |
| 五、让评测结论值得相信 | s17–s20 | 评估计划和效率，并检查裁判偏差、实验波动与结论边界。 |
| 六、做成可以持续使用的评测工程 | s21–s24 | 实现自定义指标、回归门禁、源码对照，完成可复现的项目报告。 |

## 一、先把评测问题定义清楚

从“看起来不错”走到一份可执行的评测协议。

### s01 把“好用”写成评测协议

**要解决的问题：** 什么结果才算成功，哪些失败绝不能被平均分掩盖？

**知识点：** 任务、样本、判分器、数据集、阈值、运行配置；模型能力与应用质量；离线评测与线上观察。

**实验与本课产物：** 用知识库助理的 6 个示例建立初始 scorecard，记录成功、失败与暂时不可判定。

**验收：** 提交一页评测协议：目标、对象、输入、成功证据、失败类型、分数方向都明确。

**官方阅读：** [资料 1](https://deepeval.com/docs/evaluation-introduction)、[资料 2](https://docs.ragas.io/en/stable/concepts/experimentation/)。

**源码入口：** [deepeval/deepeval/evaluate/evaluate.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)、[ragas/src/ragas/experiment.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)。

### s02 一条样本怎样进入两个框架

**要解决的问题：** 同一条业务记录如何适配 DeepEval 和 Ragas，而不改变评测问题？

**知识点：** input/actual_output/expected_output/retrieval_context；user_input/response/reference/retrieved_contexts；工具调用与多轮消息；必需字段；数据版本与开发/校准/留出集。

**实验与本课产物：** 建立统一 JSONL 样本和两份小适配器；加入缺字段、无参考答案、工具失败样本。

**验收：** 逐字段说明映射；对不兼容样本给出明确处理；区分 Ragas collections 新接口与旧 Sample/evaluate 路线。

**官方阅读：** [资料 1](https://deepeval.com/docs/evaluation-test-cases)、[资料 2](https://docs.ragas.io/en/stable/concepts/components/eval_sample/)、[资料 3](https://docs.ragas.io/en/stable/concepts/components/eval_dataset/)。

**源码入口：** [deepeval/deepeval/test_case/llm_test_case.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/llm_test_case.py)、[deepeval/deepeval/test_case/conversational_test_case.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/conversational_test_case.py)、[ragas/src/ragas/dataset_schema.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset_schema.py)。

### s03 先做能精确判定的评测

**要解决的问题：** 哪些问题用普通程序就能判，何时需要语义判断？

**知识点：** 精确匹配、集合 precision/recall/F1、结构校验、规则断言；规则覆盖范围；对语义等价的误判。

**实验与本课产物：** 手算工具集合 F1；给有效 JSON、必需字段、工单真实状态写本地断言。

**验收：** 手算与程序结果一致；能解释“字符串不同但都正确”和“文字正确但状态未变”的反例。

**官方阅读：** [资料 1](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/traditional/)、[资料 2](https://deepeval.com/guides/guides-building-custom-metrics)。

**源码入口：** [ragas/src/ragas/metrics/collections/tool_call_f1/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/metric.py)、[ragas/src/ragas/metrics/collections/tool_call_f1/util.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/util.py)。

### s04 让 LLM 按 rubric 判分

**要解决的问题：** 怎样把“回答质量”写成裁判可以执行的标准？

**知识点：** LLM-as-a-Judge、评分维度、rubric、G-Eval、Aspect Critic、结构化 verdict 与理由；DAG 评分分支。

**实验与本课产物：** 为“答案是否覆盖用户所有要求”写 rubric，用正例、反例和边界例检查判分。

**验收：** 标准能区分不同错误；保留每条理由；不把 LLM 裁判输出当作客观真值，也不把 DAG 当作完全确定的裁判。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-llm-evals)、[资料 2](https://deepeval.com/guides/guides-g-eval-examples)、[资料 3](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/aspect_critic/)。

**源码入口：** [deepeval/deepeval/metrics/g_eval/g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)、[deepeval/deepeval/metrics/dag/dag.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/dag/dag.py)。

## 二、把 RAG 拆成可诊断的指标

解释检索、证据和回答分别出了什么问题。

### s05 检索结果有用而且排在前面吗

**要解决的问题：** 为什么同样找到了证据，排序不同仍应得到不同分数？

**知识点：** Context Precision、相关性判定、排序敏感性；基于标注 ID 与基于 LLM/参考答案的口径；分母与空结果。

**实验与本课产物：** 固定问题和答案，将相同 chunks 重排、加入噪声，手算后再用框架评分。

**验收：** 解释排名变化如何影响所选实现的分数；列清它需要哪些字段和参考信息。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-contextual-precision)、[资料 2](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)。

**源码入口：** [deepeval/deepeval/metrics/contextual_precision/contextual_precision.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_precision/contextual_precision.py)、[ragas/src/ragas/metrics/collections/context_precision/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_precision/metric.py)。

### s06 检索是否漏掉完成回答的证据

**要解决的问题：** 检索结果都相关，为什么仍然可能无法回答？

**知识点：** Context Recall、参考答案中的 claims、标注证据集合；coverage 与 precision 的区别；参考不完整时的局限。

**实验与本课产物：** 设计需要两段证据的问题，分别保留一段、两段和错误版本的证据。

**验收：** 构造“高 precision、低 recall”样本；说明 claim recall 与基于 ID 的 recall 不能混作同一指标。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-contextual-recall)、[资料 2](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)。

**源码入口：** [deepeval/deepeval/metrics/contextual_recall/contextual_recall.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_recall/contextual_recall.py)、[ragas/src/ragas/metrics/collections/context_recall/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_recall/metric.py)。

### s07 回答真的被证据支持吗

**要解决的问题：** 一个听起来正确的回答，是否可能没有证据支持？

**知识点：** Faithfulness、claim 拆解、支持/矛盾/信息不足、NLI；证据内一致性与外部事实正确性；不同框架的判定口径。

**实验与本课产物：** 保持问题与证据不变，分别加入被支持、矛盾和证据未提及的陈述。

**验收：** 逐 claim 解释 verdict；识别两个框架对于信息不足的不同处理，不直接平均它们的总分。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-faithfulness)、[资料 2](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)。

**源码入口：** [deepeval/deepeval/metrics/faithfulness/faithfulness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py)、[ragas/src/ragas/metrics/collections/faithfulness/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py)。

### s08 相关、正确和完整分别是什么

**要解决的问题：** 为什么回答了问题，不代表答案事实正确或完整？

**知识点：** Answer/Response Relevancy、Answer Correctness、Factual Correctness、语义相似度；reference 依赖；precision/recall 侧重；拒答与不可回答问题。

**实验与本课产物：** 设计“相关但错误”“忠实但证据错误”“正确但答非所问”“应拒答却编造”四组样本。

**验收：** 用指标组合而非一个总分解释四组样本；为不可回答问题另写验收标准。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-answer-relevancy)、[资料 2](https://deepeval.com/guides/guides-answer-correctness-metric)、[资料 3](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness/)。

**源码入口：** [deepeval/deepeval/metrics/answer_relevancy/answer_relevancy.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/answer_relevancy/answer_relevancy.py)、[ragas/src/ragas/metrics/collections/factual_correctness/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/factual_correctness/metric.py)、[ragas/src/ragas/metrics/collections/answer_correctness/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/answer_correctness/metric.py)。

## 三、用评测驱动 RAG 改进

在同一数据集上建立基线、制造失败、扩充样本并做受控迭代。

### s09 给最小 RAG 建立可复现基线

**要解决的问题：** 如何让一次实验完整留下输入、检索、输出和分数？

**知识点：** 最小 RAG 链路、组件与端到端评测、运行 ID、模型/提示词/数据版本、scorecard。

**实验与本课产物：** 接入固定文档的问答管线，先用缓存输出跑通，再选择真实模型运行；两框架评同一批记录。

**验收：** 可以从保存的记录重放评分；能列出全部影响结果的配置；基线报告不包含编造的实测分数。

**官方阅读：** [资料 1](https://deepeval.com/tutorials/rag-qa-agent/evaluation)、[资料 2](https://docs.ragas.io/en/stable/tutorials/rag/)。

**源码入口：** [deepeval/deepeval/dataset/dataset.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/dataset.py)、[ragas/src/ragas/dataset.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset.py)、[ragas/src/ragas/experiment.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)。

### s10 通过失败实验定位 RAG 问题

**要解决的问题：** 分数下降是检索、上下文还是生成出了问题？

**知识点：** 故障注入、错误分类、Noise Sensitivity、检索/生成分离诊断、bad case 分析。

**实验与本课产物：** 分别删证据、加无关段落、改错误文档、改生成提示词，保留其他条件。

**验收：** 为每种注入给出预期受影响指标和实际差异；避免把所有失败都归因于提示词。

**官方阅读：** [资料 1](https://deepeval.com/guides/guides-rag-evaluation)、[资料 2](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/noise_sensitivity/)。

**源码入口：** [deepeval/deepeval/metrics/contextual_relevancy/contextual_relevancy.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py)、[ragas/src/ragas/metrics/collections/noise_sensitivity/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/noise_sensitivity/metric.py)。

### s11 生成测试集，并验证它有没有价值

**要解决的问题：** 合成问题怎样覆盖真实任务，又如何避免自问自答的偏差？

**知识点：** DeepEval Synthesizer、Ragas TestsetGenerator、knowledge graph、personas、单跳/多跳、evolutions、质量过滤、重复与数据泄漏。

**实验与本课产物：** 从小文档集扩充种子问题，按错误类型/任务类型分层，并抽样人工复核。

**验收：** 每条样本可追溯到来源；合成与人工样本分开标记；留出集不参与优化；不把 Agent 测试集占位页当作现成功能。

**官方阅读：** [资料 1](https://deepeval.com/guides/guides-using-synthesizer)、[资料 2](https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/)、[资料 3](https://docs.ragas.io/en/stable/howtos/customizations/testgenerator/)。

**源码入口：** [deepeval/deepeval/synthesizer/synthesizer.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/synthesizer.py)、[ragas/src/ragas/testset/synthesizers/generate.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/generate.py)。

### s12 改变一个因素，比较一个假设

**要解决的问题：** 改 top-k、chunk 或模型后，怎样判断改进来自哪里？

**知识点：** 受控实验、配对样本、提示词/检索参数迭代、质量/成本/延迟权衡；开发集选择与留出集验证。

**实验与本课产物：** 在相同问题和评分配置下比较两个 RAG 版本，先只改一个因素。

**验收：** 报告逐样本变化与分类结果；说明权衡和未改善类别；不根据教程中的示意表得出模型优劣结论。

**官方阅读：** [资料 1](https://deepeval.com/tutorials/rag-qa-agent/improvement)、[资料 2](https://deepeval.com/guides/guides-optimizing-hyperparameters)、[资料 3](https://docs.ragas.io/en/stable/howtos/applications/evaluate-and-improve-rag/)。

**源码入口：** [ragas/src/ragas/experiment.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)、[learn-claude-code/s08_context_compact/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s08_context_compact/code.py)。

## 四、评测 Agent 的行动与结果

把最终回答、工具行为、真实状态和多轮表现分别评清楚。

### s13 把 Agent 执行变成评测样本

**要解决的问题：** 为什么最终回答看不到工具错误和多走的步骤？

**知识点：** trace、span、轨迹、工具事件、输入输出、异常；端到端/完整轨迹/组件边界；trace 树和工具归属。

**实验与本课产物：** 给助理记录一次完整工具调用；参考新版 s01/s02/s04，保存可重放事件。

**验收：** 能指出失败发生在哪个 span；区分最终文本、LLM 工具决策与工具执行结果；正确记录工具参数和返回值。

**官方阅读：** [资料 1](https://deepeval.com/guides/guides-tracing-ai-agents)、[资料 2](https://deepeval.com/docs/evaluation-trajectory-based-llm-evals)。

**源码入口：** [deepeval/deepeval/tracing/tracing.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/tracing/tracing.py)、[learn-claude-code/s01_agent_loop/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/code.py)、[learn-claude-code/s02_tool_use/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s02_tool_use/code.py)、[learn-claude-code/s04_hooks/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s04_hooks/code.py)。

### s14 工具选对了，参数与顺序也对了吗

**要解决的问题：** 调用过正确工具，为什么工具使用分数仍可能不同？

**知识点：** ToolCorrectness、ToolCallAccuracy、ToolCallF1、ArgumentCorrectness；集合与序列；额外参数、重复调用、无调用边界。

**实验与本课产物：** 构造正确、漏调、误调、错参、乱序、重复和无需工具的轨迹，手算并对照实现。

**验收：** 解释 Accuracy 与 F1 的差异；识别文档 F1 勘误；证明集合 F1 无法惩罚完全重复的同一调用。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-tool-correctness)、[资料 2](https://deepeval.com/docs/metrics-argument-correctness)、[资料 3](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)。

**源码入口：** [deepeval/deepeval/metrics/tool_correctness/tool_correctness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/tool_correctness/tool_correctness.py)、[ragas/src/ragas/metrics/collections/tool_call_accuracy/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/metric.py)、[ragas/src/ragas/metrics/collections/tool_call_f1/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/metric.py)。

### s15 任务是否真的完成

**要解决的问题：** Agent 说“已创建工单”，如何核实它确实做到了？

**知识点：** Task Completion、AgentGoalAccuracy、reference outcome、外部状态断言；结果与路径；停止条件与证据。

**实验与本课产物：** 在本地模拟工单系统制造“说成功但未写入”“重复创建”“正确完成”三类结果。

**验收：** 用真实状态断言核实完成；将从对话推断的完成度与状态验证分别报告；不强制只有一条合法执行路径。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-task-completion)、[资料 2](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)。

**源码入口：** [deepeval/deepeval/metrics/task_completion/task_completion.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/task_completion.py)、[ragas/src/ragas/metrics/collections/agent_goal_accuracy/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/agent_goal_accuracy/metric.py)、[learn-claude-code/s17_goal_loop/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s17_goal_loop/code.py)。

### s16 多轮对话、记忆和模拟用户怎样评

**要解决的问题：** 单轮都正确，为什么整个对话还是失败？

**知识点：** ConversationalTestCase、Turn、MultiTurnSample、上下文保持、指令变化、知识保留、对话完整性、模拟器终止与场景覆盖。

**实验与本课产物：** 让用户补充或更改条件，加入记忆污染、漏记条件和过早结束场景。

**验收：** 分别评每轮和整个会话；固定场景并检查模拟器自身；遵守当前 DeepEval 多轮执行接口边界。

**官方阅读：** [资料 1](https://deepeval.com/guides/guides-multi-turn-evaluation)、[资料 2](https://deepeval.com/guides/guides-multi-turn-simulation)、[资料 3](https://docs.ragas.io/en/stable/howtos/applications/evaluating_multi_turn_conversations/)。

**源码入口：** [deepeval/deepeval/test_case/conversational_test_case.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/conversational_test_case.py)、[deepeval/deepeval/simulator/conversation_simulator.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/simulator/conversation_simulator.py)、[learn-claude-code/s09_memory/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s09_memory/code.py)。

## 五、让评测结论值得相信

评估计划和效率，并检查裁判偏差、实验波动与结论边界。

### s17 计划质量与执行一致性怎样区分

**要解决的问题：** 完成任务、计划合理、照计划行动是同一件事吗？

**知识点：** Plan Quality、Plan Adherence、可观察计划与执行证据；任务依赖；多 Agent 的组件与整体评价。

**实验与本课产物：** 给同一任务提供好/坏/缺失计划，比较执行轨迹；参考 s05/s10/s13/s16。

**验收：** 区分计划质量与遵从度；对“无计划默认高分”单独标记；不要求读取或展示模型隐藏思维。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-plan-quality)、[资料 2](https://deepeval.com/docs/metrics-plan-adherence)、[资料 3](https://deepeval.com/guides/guides-ai-agent-evaluation-metrics)。

**源码入口：** [deepeval/deepeval/metrics/plan_quality/plan_quality.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/plan_quality/plan_quality.py)、[deepeval/deepeval/metrics/plan_adherence/plan_adherence.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/plan_adherence/plan_adherence.py)、[learn-claude-code/s10_task_system/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s10_task_system/code.py)、[learn-claude-code/s16_workflow_runtime/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s16_workflow_runtime/code.py)。

### s18 完成得高效且稳定吗

**要解决的问题：** 同样成功，怎样发现重复、循环、超时和额外成本？

**知识点：** Step Efficiency、步数/重试/异常、工具调用成本、token/延迟、预算、重复运行成功率；计划效率与实际效率。

**实验与本课产物：** 注入重复检索、工具超时和失败恢复；对同一任务重复运行并记录成本。

**验收：** 同时报告成功率、失败类型和资源消耗；分离评测成本与应用成本；不以更少步骤自动判更优。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-step-efficiency)、[资料 2](https://docs.ragas.io/en/stable/howtos/customizations/run_config/)、[资料 3](https://docs.ragas.io/en/stable/howtos/customizations/metrics/_cost/)。

**源码入口：** [deepeval/deepeval/metrics/step_efficiency/step_efficiency.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/step_efficiency/step_efficiency.py)、[learn-claude-code/s11_background_tasks/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s11_background_tasks/code.py)。

### s19 你的裁判可靠吗

**要解决的问题：** 框架给出分数之前，怎样检查评分标准是否对齐人类？

**知识点：** 人工复核集、Judge alignment、位置/篇幅/自偏好、裁判提示词、中文适配、分歧分析；局部改进与留出验证。

**实验与本课产物：** 建立小规模人工标注校准集，交换答案顺序、改写篇幅并对比分歧；为中文样本校准 rubric。

**验收：** 保留人类标签与裁判理由；报告分歧和修订前后结果；校准材料与最终留出评估分开。

**官方阅读：** [资料 1](https://docs.ragas.io/en/stable/howtos/applications/align-llm-as-judge/)、[资料 2](https://docs.ragas.io/en/stable/howtos/customizations/metrics/metrics_language_adaptation/)、[资料 3](https://arxiv.org/abs/2306.05685)。

**源码入口：** [deepeval/deepeval/metrics/g_eval/g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)、[ragas/src/ragas/experiment.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)。

### s20 平均分上升，结论能说多大

**要解决的问题：** 怎样避免把抽样波动或某个类别退化写成全面改进？

**知识点：** 逐样本配对差值、重复评分、分层报告、均值与失败率；bootstrap 区间入门、业务最小改进与统计不确定性。

**实验与本课产物：** 复用 s12 的两个版本，输出配对差值和分层结果；用重采样展示区间变化。

**验收：** 结论与样本规模匹配；不将区间跨零解释成已证明无差异；不将一次高分当成可靠生产结论。本课统计内容标为方法补充。

**官方阅读：** [资料 1](https://docs.ragas.io/en/stable/concepts/experimentation/)、[资料 2](https://docs.ragas.io/en/stable/concepts/datasets/)、[资料 3](https://deepeval.com/guides/guides-regression-testing-in-cicd)、[统计实现参考](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)。

**源码入口：** [ragas/src/ragas/experiment.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)。

## 六、做成可以持续使用的评测工程

实现自定义指标、回归门禁、源码对照，完成可复现的项目报告。

### s21 实现一个属于业务的指标

**要解决的问题：** 怎样从业务失败类型推导出一个可审查的评分器？

**知识点：** 规则/LLM/复合指标、BaseMetric、结构化输出、measure/a_measure/ascore、解释与错误状态；适用域。

**实验与本课产物：** 实现“回答与工单真实状态一致”的业务指标，先用规则，再比较需要语义判定的扩展。

**验收：** 给出正例、负例、边界例和适用范围；保持规则断言与语义裁判边界；不把官方有缺陷示例直接粘贴为答案。

**官方阅读：** [资料 1](https://deepeval.com/guides/guides-building-custom-metrics)、[资料 2](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/general_purpose/)。

**源码入口：** [deepeval/deepeval/metrics/base_metric.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/base_metric.py)、[ragas/src/ragas/metrics/collections/base.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/base.py)。

### s22 把评测接入回归和生产反馈

**要解决的问题：** 怎样让一次修复成为下次发布前能自动发现的回归？

**知识点：** pytest/CI、质量门禁、关键失败单独拦截、夜间较重评测、生产 trace 转样本、版本与成本记录。

**实验与本课产物：** 把一个已修复 bad case 加入回归集；模拟门禁失败；从匿名化轨迹补充候选样本。

**验收：** 人为引入回归时能被发现；门禁遵循指标方向与校准结果；避开过时 in_ci=True 示例；云服务集成作为可选路径。

**官方阅读：** [资料 1](https://deepeval.com/guides/guides-regression-testing-in-cicd)、[资料 2](https://deepeval.com/guides/guides-llm-observability)、[资料 3](https://docs.ragas.io/en/stable/howtos/applications/add_to_ci/)。

**源码入口：** [deepeval/deepeval/evaluate/evaluate.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)、[ragas/src/ragas/evaluation.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/evaluation.py)。

### s23 沿一次评分读懂关键源码

**要解决的问题：** 从输入字段到 prompt、verdict、公式和结果，评分究竟在哪里发生？

**知识点：** 指标基类、输入校验、prompt/schema、模型调用、聚合、异步；同名指标实现差异；文档、实现与测试三方对照。

**实验与本课产物：** 完整跟踪 Faithfulness 和一个工具指标的调用链；对两个框架写同一份口径说明。

**验收：** 用路径和符号定位每一步；指出哪些分数不可直接比较；源码片段固定 commit；不把整个仓库目录当教材目录。

**官方阅读：** [资料 1](https://deepeval.com/docs/metrics-faithfulness)、[资料 2](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)、[资料 3](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)。

**源码入口：** [deepeval/deepeval/metrics/faithfulness/faithfulness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py)、[ragas/src/ragas/metrics/collections/faithfulness/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py)、[ragas/src/ragas/metrics/collections/tool_call_accuracy/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/metric.py)。

### s24 完成一次可以被别人复核的评测

**要解决的问题：** 你能否独立提出改进、验证它，并解释没有解决的问题？

**知识点：** 评测协议、数据审计、指标选型、双框架复现、受控实验、错误分析、可靠性、成本、回归的完整闭环。

**实验与本课产物：** 完成知识库问答＋工具调用助理的基线、改进版和最终报告；挑一项新版 Learn Claude Code 机制做迁移实验。

**验收：** 交付数据、配置、代码、逐样本结果、失败分析和复现命令；明确假设与限制；至少包含检索失败、无依据生成、错参和虚假完成反例。

**官方阅读：** [资料 1](https://deepeval.com/guides/guides-ai-agent-evaluation)、[资料 2](https://deepeval.com/guides/guides-rag-evaluation)、[资料 3](https://docs.ragas.io/en/stable/tutorials/agent/)。

**源码入口：** [learn-claude-code/s15_integrated_harness/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s15_integrated_harness/code.py)、[learn-claude-code/s16_workflow_runtime/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s16_workflow_runtime/code.py)、[learn-claude-code/s17_goal_loop/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s17_goal_loop/code.py)。

## 完课后应具备的能力

1. 根据业务失败类型设计评测协议、样本与 rubric，说明每个指标测什么和测不到什么。
2. 区分检索缺失、证据不相关、无依据生成、事实错误、工具参数错误、轨迹低效与任务未完成。
3. 为同一批数据正确适配 DeepEval 和 Ragas；解释新旧接口与同名指标差异。
4. 阅读关键指标的输入校验、提示词、结构化判定与聚合公式；用反例检验实现。
5. 在固定数据和配置下比较版本，报告逐样本变化、裁判分歧、不确定性及成本。
6. 将失败案例变为回归样本，并交付别人可以复核的结果与运行记录。

## 选读与附录

官方目录中其余内容按需进入选读：多模态与语音、SQL 与摘要、基础模型 benchmarks、classifiers/Jev/Eval modes、各模型提供商和框架集成、完整配置/API 参考。资料全部登记并不意味着每个 API 都另开一课。主线不扩展为模型训练、从零开发 Agent 框架或所有第三方平台操作教程。
