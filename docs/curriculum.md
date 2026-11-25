# 从编程 Agent 学评测：课程大纲

Agent 接到任务后，先读取文件、检索资料、调用工具，最后组织回答。评测要沿着这条链路把四个问题落到代码里：目标是什么、证据在哪里、判据怎样计算、下一步该修哪一层。

课程沿 [Learn Claude Code](https://github.com/shareAI-lab/learn-claude-code) 的递进路线搭建编程 Agent，知识库部分接入 [Datawhale TinyRAG](https://github.com/datawhalechina/tiny-universe/tree/main/content/TinyRAG)，评测体系统一基于 [DeepEval](https://deepeval.com/docs/evaluation-introduction) 展开。每课围绕一个核心问题推进，指标课直接复用前面搭好的 Agent 内核。

| 阶段 | 课程 | 要建立的理解 |
|---|---|---|
| 建立评测 | 01 至 04 | 定义成功条件，保存运行样本，准备与审核数据，选择规则或语义评分 |
| 评价上下文与回答 | 05 至 10 | 接通 TinyRAG，评价检索相关性、排序、覆盖、忠实度与答案质量，定位链路故障 |
| 评价 Agent 行为 | 11 至 13 | 分别核对工具调用过程、最终交付产物和多轮会话约束 |
| 形成改进闭环 | 14 至 16 | 校准模型裁判，开展同题版本对比，将复核后的失败接入持续回归 |

上下文追踪贯穿第 5 至 10 课，第 13 课进一步延伸到多轮对话压缩后模型实际可见的输入。检索候选、送入模型的片段和原始知识文档分开存档，避免拿错评测对象。

## 01 定义成功

模型停下了，任务就完成了吗？

用一个最小循环和 Bash 执行文件任务，再从实际文件与命令输出判断是否成功。

知识点：

- 模型、执行框架与工具的职责分工
- 消息回填与循环退出状态
- 停止状态、命令退出码与任务成功条件
- 独立评分及逐项证据核验

本课代码：仅保留模型请求、Bash 执行与消息回填，记录够独立评分使用的事件。

源码依据：

- Learn Claude Code：`s01_agent_loop` 最小循环
- DeepEval：`Golden`、`LLMTestCase` 与 `evaluate` 的三层职责

动手理解：创建并运行 `hello.py`，再把一条只回复“已完成”的记录交给评分器。

学会的标志：能沿着任务要求、执行事件、磁盘文件和评分规则，解释为什么模型正常停止依然可能判为失败。

[教材](../course/e01_success/README.zh.md) · [源码导读](../course/e01_success/source_walkthrough.md)

## 02 保存一次运行

怎样把 Agent 的一次工作变成评测样本？

把任务、可见输入、最终输出、工具调用和产物对应起来，再转换成 DeepEval 样本结构。

知识点：

- 任务编号、运行编号与事件位置编号
- 原始运行轨迹与标准化样本映射
- 具名工具、输入参数、执行结果与权限拒绝状态
- DeepEval 的 `input`、`actual_output` 与 `ToolCall` 字段映射

本课代码：在 Bash 之外加入 `read_file` 和 `write_file`，补上工作区路径校验和结构化事件记录。

源码依据：

- Learn Claude Code：`s02_tool_use` 与 `s03_permission` 工具分发及路径边界
- DeepEval：`LLMTestCase`、`ToolCall` 与 `tracing` 入口

动手理解：让同一任务触发一次合法写入和一次越界拒绝，核对导出的 `LLMTestCase` 是否完整保留真实动作、参数与状态。

学会的标志：能从评测样本追回每一步真实动作，区分工具未调用、权限拒绝与执行报错。

[教材](../course/e02_samples/README.zh.md) · [源码导读](../course/e02_samples/source_walkthrough.md)

## 03 准备评测数据

怎样让题目代表你真正关心的能力？

先编写少量覆盖核心行为的种子题，再结合文档生成候选，经过人工审核与去重后划分数据集。

知识点：

- 任务、参考答案、参考上下文与实际输出的区别
- 正常、错误前提、边界与缺证据四类题型
- 来源哈希、原文引文、候选生成与人工审核状态
- 按题意去重以及按题族隔离开发集和留出集

本课代码：复用前两课 Agent，新增数据审核过滤、候选生成和集合检查。

源码依据：

- DeepEval：`Golden`、`EvaluationDataset` 与 `Synthesizer`

动手理解：围绕上传规范编写种子题，生成候选并剔除无原文支撑或同义重复的条目，保证同一题族落在同一划分中。

学会的标志：能说明每道题测什么、参考依据出自哪个版本，以及为何不能用调试题充当独立验收集。

[教材](../course/e03_datasets/README.zh.md) · [源码导读](../course/e03_datasets/source_walkthrough.md)

## 04 给样本评分

什么时候用规则，什么时候请模型判断？

从结构与固定值检查走到自然语言语义量表，明确评分单位、阈值和异常处理方式。

知识点：

- 精确匹配、结构契约与业务规则检查
- `GEval` 的 `evaluation_steps`、`rubric` 与阈值归一化
- 集合 Precision、Recall 与 F1 的评分单位和分母
- 有效零分、分母未定义与接口报错三类状态分离

本课代码：复用统一样本，新增继承 `BaseMetric` 的规则检查器和一个 `GEval` 语义裁判。

源码依据：

- DeepEval：`BaseMetric`、`GEval`（`criteria`、`steps`、量表归一化）与 `DAGMetric` 分支思路

动手理解：分别对同义改写、缺漏要点的回答和裁判接口报错打分，观察规则与语义标准各自负责的边界。

学会的标志：能追到每次打分的输入字段、量表分母与状态标签，把接口异常从业务零分中摘出来。

[教材](../course/e04_scoring/README.zh.md) · [源码导读](../course/e04_scoring/source_walkthrough.md)

## 05 接通知识库

检索出的资料，最后有哪些真的交给了模型？

接入 Datawhale TinyRAG 与只读知识库，记录从文档分块、检索命中到实际送入模型输入的完整路径。

知识点：

- 文档切分、向量相似度与 `top-k` 预算截断
- 全部检索候选（`hits`）与实际回填上下文（`retrieval_context`）的区别
- 文档路径、字符偏移、内容哈希与知识快照版本
- 本地 TF-IDF 词面基线的能力边界

本课代码：新增只读 `search_knowledge` 工具与上下文组装，每次成功请求前深拷贝 `model_inputs`。

源码依据：

- TinyRAG：`VectorStore` 建库与余弦检索
- DeepEval：`LLMTestCase` 中的 `context` 与 `retrieval_context`

动手理解：调整 `k` 和 `context_limit`，或更换知识库文档，核对命中候选、工具返回值与模型最后一次实际输入。

学会的标志：能取出一次回答真正看过的知识片段，并说明它对应的文档版本是否过期。

[教材](../course/e05_knowledge_context/README.zh.md) · [源码导读](../course/e05_knowledge_context/source_walkthrough.md)

## 06 上下文相关性与排序

找到了资料，为什么还要看相关性和顺序？

固定问题与候选片段，分别考察无关片段占比和有用证据排在列表前后的差异。

知识点：

- 相关性二元标签与参考答案的作用
- 普通精度与按位置加权的列表 AP
- AP、MRR 与 NDCG 的排序视角对照
- `ContextualPrecisionMetric` 与 `ContextualRelevancyMetric` 的评分单位

本课代码：复用 TinyRAG 候选，新增相关性标注与排序聚合检查。

源码依据：

- DeepEval：`ContextualPrecisionMetric`、`ContextualRelevancyMetric` 与 `score_qag_verdicts`

动手理解：保持片段内容和标签不变，仅调整有用片段的先后次序并追加干扰片段，比较命中率与排序分数的变化。

学会的标志：能解释精度指标的参考依赖、分母构成以及排序位置变动对得分的影响。

[教材](../course/e06_context_precision/README.zh.md) · [源码导读](../course/e06_context_precision/source_walkthrough.md)

## 07 上下文覆盖与召回

资料看起来都相关，为什么问题仍答不全？

先明确回答问题所需的参考事实，再检查实际送入模型的上下文覆盖了多少必要证据。

知识点：

- 文档级召回与事实级召回的口径差异
- 参考事实拆解与证据来源映射
- `ContextualRecallMetric` 的逐句归因判断
- 参考条目变化与空参考下的分母边界

本课代码：复用检索记录，新增参考事实覆盖统计和原生归因检查。

源码依据：

- DeepEval：`ContextualRecallMetric` 及其模板和逐句裁决

动手理解：在保持其余返回片段高度相关的前提下删去一条关键文档，再补回该文档，观察精确率与召回率如何各自变化。

学会的标志：能指出漏掉的具体事实，并说明高上下文精度为什么无法自动保证高召回。

[教材](../course/e07_context_recall/README.zh.md) · [源码导读](../course/e07_context_recall/source_walkthrough.md)

## 08 回答对上下文的忠实度

回答里的每条事实，资料都支持吗？

把生成回答拆成独立声明，逐条对照送入模型的上下文判断是否获得支持。

知识点：

- 事实抽取（`truths`）与声明拆解（`claims`）
- 支持（`yes`）、矛盾（`no`）与未提及（`borderline`）三类裁决
- `penalize_ambiguous_claims` 与明确支持比例的聚合口径
- 空声明约定与裁决数量对齐校验

本课代码：复用实际回答与上下文，新增声明级忠实度判定与严格支持比例统计。

源码依据：

- DeepEval：`FaithfulnessMetric`、`schema` 与三步提示词模板

动手理解：在忠实回答里插入一条资料未提及的细节或一处数字矛盾，沿着抽取出的 `truths` 和 `claims` 追踪分数变化。

学会的标志：能逐条指出失去依据的声明位置，区分“忠于给定资料”和“现实世界事实正确”。

[教材](../course/e08_faithfulness/README.zh.md) · [源码导读](../course/e08_faithfulness/source_walkthrough.md)

## 09 答案质量

忠于资料，为什么仍可能没有回答好问题？

把回答是否切题、事实是否正确完整以及缺证据时是否合理拒答拆开度量。

知识点：

- 切题程度（`AnswerRelevancyMetric`）的逐陈述判定边界
- 基于明确事实集合的 Precision、Recall 与 F-beta
- `GEval` 任务标准在“证据充分”与“缺证据拒答”两分支上的判断
- 语义切题分不能代替事实正确性与完整性的原因

本课代码：复用现有 Agent，引入参考事实标注、`AnswerRelevancyMetric` 与 `GEval` 任务量表。

源码依据：

- DeepEval：`AnswerRelevancyMetric` 与 `GEval` 任务正确性量表

动手理解：对比“忠实但离题”“切题但算错”“正确但漏项”和“缺依据仍强行作答”四类样本在各指标下的表现。

学会的标志：能按故障维度挑选对应指标，不再拿忠实度或切题分替代整份答案质量。

[教材](../course/e09_answer_quality/README.zh.md) · [源码导读](../course/e09_answer_quality/source_walkthrough.md)

## 10 上下文干扰与故障定位

答案错了，应该先改资料、检索还是生成？

固定任务与生成输入模板，一次只改变链路上的一个环节，沿各阶段快照追查最早出现的证据缺口。

知识点：

- 知识库缺失、检索过滤遗漏与上下文组装截断
- 文档过期、无关噪声与冲突规范的来源优先级
- 高忠实度但低任务分（忠实于旧资料）的故障形态
- `first_gap` 阶段排查与 `replay` 受控生成回放

本课代码：在既有 RAG 链路加入内存快照控制开关与受控生成回放，隔离变量。

源码依据：

- DeepEval：联合 `ContextualRelevancyMetric`、`FaithfulnessMetric` 与 `GEval` 任务标准做分层诊断

动手理解：依次制造源文档缺失、检索漏召回、组装丢弃、旧版替换与冲突干扰，每次只改动一处并检查阶段快照。

学会的标志：能依据阶段证据指出下一步优先排查哪一层，不从单个总分倒推根因。

[教材](../course/e10_rag_diagnosis/README.zh.md) · [源码导读](../course/e10_rag_diagnosis/source_walkthrough.md)

## 11 工具调用质量

名字选对了，工具就用对了吗？

沿工具名、输入参数、调用顺序与实际返回状态分别评估工具轨迹。

知识点：

- 工具名称、参数字典与执行输出的分层评估
- 无序覆盖、有序加权子序列（Weighted LCS）与精确序列匹配
- `ToolCorrectnessMetric` 五种配置与 `ArgumentCorrectnessMetric` 参数语义判定
- 预期权限拒绝、合法替代路线与多余调用的处理

本课代码：复用第 2 课具名工具与权限校验，构建十组工具边界样本及两组实测任务。

源码依据：

- DeepEval：`ToolCorrectnessMetric` 与 `ArgumentCorrectnessMetric`

动手理解：构造路径错误、顺序颠倒、目录冲突写入失败和多余读取等样本，比较五种规则配置和参数语义裁判各自看到什么。

学会的标志：能解释为什么工具调用拿到高匹配分，最终交付仍然可能失败。

[教材](../course/e11_tool_quality/README.zh.md) · [源码导读](../course/e11_tool_quality/source_walkthrough.md)

## 12 任务完成度

怎样确认 Agent 真正交付了用户要的结果？

以独立子进程执行结果、文件状态和保护约束定义业务契约，再结合任务完成度语义裁判核对交付。

知识点：

- 用户目标、口头完成声明与可观察外部状态的区别
- 函数行为探针、副作用（输入不变性）与受保护文件哈希检查
- 自定义 `BaseMetric` 硬合约与 `TaskCompletionMetric` 的分工
- `TaskCompletionMetric` 无 trace 兼容路径与摘要视野边界

本课代码：引入订单计费修复任务、独立探针 `inspect_delivery` 和 `DeliveryContract`。

源码依据：

- DeepEval：`BaseMetric` 与 `TaskCompletionMetric`（含 `schema` 与抽取/裁决模板）

动手理解：让最终回复同样是“已完成。”的两组运行分别写入正确代码、错误代码和改动受保护文件，观察硬合约与语义裁判的反应。

学会的标志：能为具体业务编写可独立核验的完成条件，并清楚代码探针与语义裁判各自管不到的盲区。

[教材](../course/e12_task_completion/README.zh.md) · [源码导读](../course/e12_task_completion/source_walkthrough.md)

## 13 会话上下文与约束保持

用户改了要求以后，Agent 还记得哪一版？

沿着多轮对话计算当前仍然有效的约束集合，同时记录每轮送进模型的真实前缀与归档恢复过程。

知识点：

- 原始会话历史、模型可见输入与上下文摘要的区别
- 用户约束的新增（`set`）、覆盖与取消（`drop`）状态演进
- 归档文件恢复路径与多轮证据核验
- `KnowledgeRetentionMetric`（反向 `yes` 极性）与 `ConversationCompletenessMetric`

本课代码：增加多轮场景输入前缀选择、归档恢复样本以及会话指标检查。

源码依据：

- Learn Claude Code：`s08_context_compact` 与 `s09_memory`
- DeepEval：`ConversationalTestCase`、`KnowledgeRetentionMetric` 与 `ConversationCompletenessMetric`

动手理解：让用户先设定字数上限与旧路径，再改换路径并取消长度限制，对比完整历史、过期摘要和归档恢复下的执行轨迹。

学会的标志：能按最新有效约束验收产物，分清“模型根本没看到更新”和“模型看到了却没遵守”。

[教材](../course/e13_conversation/README.zh.md) · [源码导读](../course/e13_conversation/source_walkthrough.md)

## 14 校准 LLM 裁判

评分器自己的判断可信吗？

冻结候选回答，用独立参考标签计算误接收与误拒绝，再排查篇幅、语言和展示位置对裁判的影响。

知识点：

- 双人标注一致性与分歧仲裁（未仲裁保持 `None`）
- 混淆矩阵、误接收率、误拒绝率与各维度覆盖率
- 篇幅变体、跨语言变体与受控 A/B 位置对调检验
- 按题族严格隔离开发集调参与留出集验证

本课代码：复用第 4 课裁判适配层，新增标签仲裁、按行统计汇总与位置对照检查。

源码依据：

- DeepEval：`GEval` 步骤、二元 `Rubric`、开发集示例选择与 `arena_g_eval` 匿名打乱机制

动手理解：固定一组候选回答，运行原配置与修订配置两套 `GEval` 裁判，核对留出集上的误判变化和 A/B 位置翻转情况。

学会的标志：能同时给出裁判的误接收/误拒绝分布与覆盖率边界，不再只报一个平均一致率。

[教材](../course/e14_judge_calibration/README.zh.md) · [源码导读](../course/e14_judge_calibration/source_walkthrough.md)

## 15 比较两个版本

分数变高，怎样判断改动真的有用？

固定题目、知识快照和评分标准，按 `(case_id, repeat, version)` 配对比较两个版本，结合分层失败与成本下结论。

知识点：

- 单因素控制、同题配对差值与交错运行顺序
- 按题型分层排查平均分掩盖的局部退化
- 按题族均值做 Bootstrap 重采样的直觉与小样本局限
- 质量提升前提下的延迟、模型调用次数、缓存 token 与费用核算

本课代码：复用第 5 课检索任务，新增 `context_limit` 版本对比、同题配对统计和用量汇总。

源码依据：

- DeepEval：`EvaluationDataset`、`TestResult`、`EvaluationResult` 记录边界与 `GEval` 配对评分

动手理解：固定 `k=3` 仅改变 `context_limit`（1 对 3），按题族与题型拆解同题差值，检查缺失配对如何影响覆盖率。

学会的标志：能说明改进发生在哪类任务、波动是否稳定，以及效果改善与调用成本之间的权衡。

[教材](../course/e15_version_comparison/README.zh.md) · [源码导读](../course/e15_version_comparison/source_walkthrough.md)

## 16 综合项目与持续回归

怎样让一次修复成为以后不会再犯的经验？

把前面 15 课的组件组合进一个可运行、可回归的编程 Agent，把真实交付缺口沉淀成长期门禁。

知识点：

- 从失败案例出发走完“运行 → 采样 → 评分 → 定位 → 修复 → 回归”闭环
- `failure_candidates` 待复核队列与知识快照哈希校验
- `DeliveryContract`、显式 `GEval` 量表与 `ContextualRecallMetric` 组合
- 分项硬门禁下的 `blocked`、`reject`、`accept_in_scope` 与 `no_regression_observed`

本课代码：串联第 2 课循环、第 5 课 TinyRAG、第 12 课独立检查和显式 `GEval` 完成度评估，建立门禁函数 `gate`。

源码依据：

- Learn Claude Code：`s15_integrated_harness` 循环整合思路
- DeepEval：`evaluate`、`assert_test`、`BaseMetric`、`GEval` 与 `ContextualRecallMetric`

动手理解：运行离线回归门禁并触发 `--live --judge` 对照，观察修改保护文件、算错边界条件和评分接口异常时门禁如何分别裁决。

学会的标志：能讲清整条评测链路各层负责什么，并独立为自己的 Agent 搭建持续回归门禁。

[教材](../course/e16_regression/README.zh.md) · [源码导读](../course/e16_regression/source_walkthrough.md) · [完整项目导读](integrated-project.md)

## 范围与依据

主线课程聚焦于直接服务评测工程的核心机制。多 Agent 团队调度、复杂长期记忆平台、MCP 协议、多模态与 SQL 专项不作为独立课次展开。

各课源码导读均沿着“输入字段 → 判据或模型裁决 → 聚合公式 → 适用边界”追查实现细节。概念讲解对照官方文档，具体算法和默认行为以[固定版本](../references/versions.json)记录的上游提交为准。

[DeepEval 评测概念](https://deepeval.com/docs/evaluation-introduction) · [写作与制作规范](course-specification.md)
