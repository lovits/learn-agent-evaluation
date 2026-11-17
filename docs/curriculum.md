# 从编程 Agent 学评测：课程大纲

你让 Agent 修复一段代码。它会读资料、选工具、修改文件，也会解释自己做了什么。评测要把这些行为变成可检查的问题：资料是否找全，回答是否有证据，动作是否合适，最终代码是否满足要求。

编程 Agent 沿 Learn Claude Code 递进；知识库使用 Datawhale TinyRAG，嵌入接口先接本地 TF-IDF 基线，生成仍由课程模型入口完成。

课程从最小执行循环开始。第1至3课建立评测的对象、样本与评分标准；第4至7课沿知识库学习 RAG 评测；第8至9课组织数据和版本比较；第10至14课进入 Agent 行为与状态；最后校准裁判，把评测接成持续回归。

每课围绕一个核心问题，教材解释机制，源码导读继续追到 DeepEval、Ragas 的实现。

## 01 Agent 循环

模型停下了，任务就完成了吗？

用最小循环连接模型与 Bash，分清运行结果和任务评分。

- 任务、样本、评分标准
- 消息与工具结果回填
- 停止状态与完成状态
- 文件、输出和退出码的证据

[教材](../lessons/e01_agent_baseline/README.zh.md) · [源码导读](../lessons/e01_agent_baseline/source_walkthrough.md)

## 02 评测样本

怎样把一次工具调用变成可评测的记录？

给动作命名，保存权限、参数和结果，再转换成两套框架的样本。

- 工具声明与分发
- 参数错误、拒绝与执行失败
- trace、span 与调用归属
- 单轮、多轮和统一字段

[教材](../lessons/e02_tools_traces/README.zh.md) · [源码导读](../lessons/e02_tools_traces/source_walkthrough.md)

## 03 评分标准

什么交给规则，什么交给 LLM 裁判？

从同义回答出发，明确评分单位与 rubric，读懂 G-Eval、DAG 和 AspectCritic。

- 精确匹配与 JSON 合同
- 集合 precision、recall、F1
- 评分步骤、结构化裁决与阈值
- 有效零分与评分失败

[教材](../lessons/e03_judges/README.zh.md) · [源码导读](../lessons/e03_judges/source_walkthrough.md)

## 04 检索质量

找到相关资料，就算找全了吗？

接入 TinyRAG 的分块与向量检索，沿相关性、覆盖和排序解释检索指标。

- TinyRAG 文档、分块、向量与 top-k
- 片段与文档的来源版本
- 文档精度、召回
- AP、MRR、NDCG
- Context Precision、Recall、Relevancy

[教材](../lessons/e04_retrieval/README.zh.md) · [源码导读](../lessons/e04_retrieval/source_walkthrough.md)

## 05 证据忠实度

回答的每条声明都有依据吗？

把回答拆成声明，比较 DeepEval 与 Ragas 的支持判定和聚合。

- claim 拆解与 NLI
- 支持、矛盾与信息不足
- borderline 与二元支持
- 空声明和证据变化

[教材](../lessons/e05_faithfulness/README.zh.md) · [源码导读](../lessons/e05_faithfulness/source_walkthrough.md)

## 06 答案质量

忠于证据的回答，为什么仍可能不合格？

区分切题、事实正确、需求覆盖与合理拒答。

- 问题、证据与 reference 的职责
- 双向 NLI、TP/FP/FN 与 F-beta
- 事实分与嵌入相似度
- 完整性与拒答政策

[教材](../lessons/e06_answer_quality/README.zh.md) · [源码导读](../lessons/e06_answer_quality/source_walkthrough.md)

## 07 失败定位

错误从资料、检索还是生成开始？

只改一个位置，沿阶段证据定位 RAG 失败。

- 受控干预
- 检索前后快照
- 产物与阶段诊断
- Noise Sensitivity 的方向与分母

[教材](../lessons/e07_failure_diagnosis/README.zh.md) · [源码导读](../lessons/e07_failure_diagnosis/source_walkthrough.md)

## 08 评测数据集

怎样把一次坏案例变成能反复使用的题目？

从文档生成候选，经参考审核、去重和题族划分形成数据集。

- Golden 与实际输出
- Synthesizer 与演化
- 图谱、persona、单跳与多跳
- 审核、来源和数据泄漏

[教材](../lessons/e08_datasets/README.zh.md) · [源码导读](../lessons/e08_datasets/source_walkthrough.md)

## 09 版本比较

分数上涨，怎样判断是不是改动带来的？

冻结条件，先按任务配对，再看分层变化和不确定性。

- 单因素比较与重复执行
- 开发选择与留出验证
- 配对差值与题族 bootstrap
- 质量、延迟和成本

[教材](../lessons/e09_comparison/README.zh.md) · [源码导读](../lessons/e09_comparison/source_walkthrough.md)

## 10 工具调用质量

工具名字对了，调用就对了吗？

借动态工具池理解名字、参数、序列和集合各在评价什么。

- MCP 发现、绑定与授权
- ToolCorrectness 与 ArgumentCorrectness
- ToolCallAccuracy 与 ToolCallF1
- 决策时上下文与合法路径

[教材](../lessons/e10_tool_evaluation/README.zh.md) · [源码导读](../lessons/e10_tool_evaluation/source_walkthrough.md)

## 11 任务完成度

谁来确认代码真的修好了？

用外部状态检查完成目标，再把业务规则写成自定义指标。

- 停止审查与继续执行
- 行为、边界与文件保护
- TaskCompletion 与 AgentGoalAccuracy
- BaseMetric 与关键条件组合

[教材](../lessons/e11_task_completion/README.zh.md) · [源码导读](../lessons/e11_task_completion/source_walkthrough.md)

## 12 跨轮约束

会话变长以后，哪些要求还应有效？

通过压缩与记忆理解多轮评测，检查新旧规则和场景覆盖。

- 可见上下文与原始轨迹
- 配对保护、转存与分页恢复
- 持久记忆与版本过滤
- 知识保留、会话完整性与模拟用户

[教材](../lessons/e12_conversation/README.zh.md) · [源码导读](../lessons/e12_conversation/source_walkthrough.md)

## 13 计划与协作

子任务都完成，整体就完成了吗？

沿依赖和交接分别评价计划质量、遵从及整体结果。

- 显式计划与执行证据
- 依赖、认领与完成声明
- 子会话、邮箱与文件归属
- 原生 trace、PlanQuality 与 PlanAdherence

[教材](../lessons/e13_planning/README.zh.md) · [源码导读](../lessons/e13_planning/source_walkthrough.md)

## 14 执行效率

怎样评价等待、重试和后台工作？

追踪后台结果与调度交付，在任务完成的前提下讨论效率。

- 占位结果与完成通知
- 到期、送达与实际执行
- StepEfficiency、超时与重试
- 墙钟、token、缓存与费用

[教材](../lessons/e14_runtime/README.zh.md) · [源码导读](../lessons/e14_runtime/source_walkthrough.md)

## 15 裁判校准

评分器自己的判断可靠吗？

用独立标签检查误判，再调整标准、少样本和语言提示。

- 混淆矩阵、agreement 与 κ
- 训练、开发和留出隔离
- G-Eval 标准与 Ragas align
- 中文适配、位置和篇幅偏差

[教材](../lessons/e15_calibration/README.zh.md) · [源码导读](../lessons/e15_calibration/source_walkthrough.md)

## 16 持续回归

怎样把这些评测接回完整 Agent？

串起运行、证据采样、双框架评分和关键条件门禁。

- 集成运行时与目标循环
- 工作流日志与恢复
- 响应、trace 与样本来源
- 业务规则、语义指标和回归门禁

[教材](../lessons/e16_regression/README.zh.md) · [源码导读](../lessons/e16_regression/source_walkthrough.md)

## 结课项目

[综合编程 Agent](../integrated_agent/README.md)连接工具、权限、按需知识、上下文、记忆、计划、任务与后台执行。评测链从实际运行提取样本，再分别检查业务状态、工具行为与回答证据，最后决定能否接受这次改动。

学习目标是能给自己的项目定义任务与数据，选出合适的指标，读懂指标的计算过程，并根据失败证据决定下一步改哪里。
