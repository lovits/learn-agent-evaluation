# DeepEval、Ragas 的评测与数据能力地图

这份地图来自已审读的 Docs / Guides / Tutorials、固定源码与2026-11-16复核的官方页面。
它区分框架提供的能力、编程任务的外部验收，以及补充的实验方法。
固定版本与完整指标导出目录分别在 references/versions.json、references/evaluation-capabilities.json。
没有将所有官方示例都视为已执行。

| 范围 | DeepEval 依据 | Ragas 依据 | 本课程的使用方式 |
|---|---|---|---|
| 评测范围 | 单轮、多轮、端到端、组件、完整轨迹；tracing/span | 端到端、组件、业务指标，experiment/dataset | 分清 Agent 整体、检索组件、工具决策与真实文件状态 |
| 样本和数据集 | Golden、LLMTestCase、ConversationalTestCase、EvaluationDataset | SingleTurnSample、MultiTurnSample、EvaluationDataset，以及较新 dataset/experiment 路线 | 统一业务记录，再分别适配；区分旧接口与 collections |
| 非模型评分 | ExactMatch、PatternMatch、JsonCorrectness 等 | ExactMatch、StringPresence、距离、BLEU/ROUGE/CHRF、语义相似度 | 精确/结构/集合规则适用于可确定的结果；不把文本相似当代码功能正确 |
| 通用模型裁判 | GEval、DAG、ConversationalGEval、自定义 BaseMetric 等 | Aspect 类判据、领域/实例 rubric、自定义指标 | 定义 rubric、结构化 verdict、解释、阈值与适用域 |
| RAG 检索 | ContextualPrecision、Recall、Relevancy | ContextPrecision/Recall、EntityRecall、ContextRelevance/Utilization | 排序、相关性、覆盖、ID/reference 依赖和空结果 |
| RAG 回答 | Faithfulness、AnswerRelevancy、Hallucination 等 | Faithfulness、AnswerRelevancy、FactualCorrectness、AnswerCorrectness/Accuracy、ResponseGroundedness、NoiseSensitivity | 忠于证据、符合事实、切题、完整和抗噪声分开测 |
| 工具与行动 | ToolCorrectness、ArgumentCorrectness、ToolPermission、MCP 指标 | ToolCallAccuracy、ToolCallF1、AgentGoalAccuracy | 工具、参数、顺序、权限、重复与结果使用不同证据；不强行一一对应 |
| 完整 Agent 轨迹 | TaskCompletion、PlanQuality/Adherence、StepEfficiency、AgentLoopDetection | GoalAccuracy、工具轨迹及可定制 rubric | 对可观察计划/事件评价；pytest、文件/diff等独立验收给出实际完成证据 |
| 多轮与记忆 | Turn 系列、KnowledgeRetention、ConversationCompleteness、Role/Topic、ConversationSimulator | MultiTurnSample、TopicAdherence、AgentGoalAccuracy 与适用的 rubric | 测约束保持、用户改口、压缩、记忆和停止；模拟器也需检查 |
| 合成测试数据 | Synthesizer 从文档、上下文、种子或需求生成 goldens；对话模拟生成实际 turns | TestsetGenerator、知识图谱、transforms、单/多跳、场景与persona能力以源码为准 | 生成候选、过滤、去重、审核、留出；不可把合成预期当成 Agent 实际运行 |
| 实验运行 | tracing、异步执行、pytest/CI、配置、缓存、模型适配、逐样本报告 | experiment、dataset、RunConfig、模型/embedding适配、费用与结果记录 | 固定基线、错误/超时、重试、预算和回归 |
| 校准与扩展 | 自定义 rubric/metric/模型、阈值与理由 | Judge alignment、提示适配、语言适配、自定义指标 | 独立标注校准；偏差与分歧分析；开发/校准/留出分开 |

## 数据怎样构建

先给编程 Agent 建小规模种子任务：查 API、解释源码、按规范改代码、修 bug、运行测试、
保持跨轮约束。每条记录包含任务ID、输入、知识库版本/证据、预期结果或验收测试、
可接受工具/路径约束、难度/类别、来源和审核状态。

执行 Agent 后再追加实际回答、检索片段、工具调用/返回、退出码、文件 diff、运行ID、
模型/配置和成本。预期数据与实际执行数据分开保存，验收测试与答案不暴露给被测 Agent。
模型、裁判、数据生成器和模拟用户是不同角色，分别记录配置。

DeepEval 的 goldens 提供输入与预期，实际输出由应用运行产生；对话实际 turns 由运行或
模拟产生。Ragas 从文档知识图谱生成 RAG 候选题的流程不能直接充当完整编程 Agent
测试集生成器。编程任务必须补充文件状态与可执行验收。数据扩充后做质量检查、去重、
任务分层与独立审核；没有完成人工审核的样本明确标记。

## 全面能力目录与主线边界

主线16课覆盖上述评测过程。安全/隐私/偏见、提示注入、图像/语音、多模态、摘要、SQL、
传统文本指标、基础模型 benchmarks，以及供应商和第三方框架集成保留为专题索引与附录。
权限、记忆污染、MCP等与编程 Agent 直接相关的部分进入主线实验。
原24课知识全部映射到16课的小节与练习；原先按需附录仍保留为附录。

配对比较、bootstrap区间、分层分析、独立文件断言与保留验收测试是课程补充方法，
不宣称两框架内置完整统计推断或代码正确性证明。分数、失败率、跳过、成本分别报告。
不要求把每一个可用指标同时跑在每条样本上，而是按评测对象选择必要的指标组合。

## 官方入口

- [DeepEval 指标与范围](https://deepeval.com/docs/metrics-introduction)
- [DeepEval Agent tracing](https://deepeval.com/docs/getting-started-agents)
- [DeepEval Golden Synthesizer](https://deepeval.com/docs/golden-synthesizer)
- [Ragas 指标地图](https://docs.ragas.io/en/stable/concepts/metrics/overview/)
- [Ragas 工具与Agent指标](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)
- [Ragas 测试集生成](https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/)

文档可能与固定源码存在 API、字段、默认值及示例差异，教材以明确指定版本核验。
典型边界包括 DeepEval 固定 llm 模式的 borderline/空裁决，以及 Ragas 的空声明 NaN；
实际含义应逐指标解释，不将同名指标当作同一尺度。
