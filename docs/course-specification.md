# Learn Claude Code 编程Agent评测课程：16课详细设计与制作规范

本说明先于第1课实施完成，是逐课制作与验收的共同依据。被测对象为固定版本 Learn Claude Code 编程 Agent；每课只引入当前评测需要的可执行代码。原24课知识合并为16课，后续按小节递进。目前已制作第1、2、3、4、5、6、7课，其余9课保持设计状态。

## 课程目标与制作范围

- 读者会Python，了解RAG与Agent；重点是实际设计、运行、诊断、解释和改进评测。
- 学习结果：能定义成功证据、构建数据集、选择指标、分析失败、比较版本，并沿关键源码解释评分。
- Agent维持编程身份：读项目资料、理解需求、修改文件、运行命令与测试。知识库为项目、API、架构与开发规范资料。
- 简化重复实现与启动配置，功能以原仓库实际契约为基准；17项机制按课程归属逐步接入，不能把计划说成等价验证已完成。
- 清理旧Faithfulness教学样章及专属回放、样本、入口与生成稿；该知识点将在第5课以编程场景重新制作。原框架源码、16课设计与通用工程设施保留。

## 教学方式与每课固定结构

参考Learn Claude Code：从一个具体问题出发，保留最小Agent循环，每次增加一个机制，再运行观察。合并课内部继续分小节；某些课只增加评分代码，不扩展Agent。第1课只介绍循环与Bash。

| 部分 | 必须交付的内容 |
|---|---|
| 问题与目标 | 明确评测对象、任务成功证据、前置知识和学完能做什么。 |
| 代码增量 | 正文展示必要片段，列清相对前课的变化；完整代码单独提供，不能隐藏导入未来整套Agent。 |
| 评分与数据 | 字段、reference依赖、评分方向、分母、阈值、空值、适用域；正常/错误/边界任务与来源。 |
| 实验解释 | 完整命令、实际轨迹、文件变化、退出码、逐样本评分；预期与实测分开。 |
| 源码导读 | 固定仓库/commit/文件/符号，按适用部分追踪校验、prompt/schema、调用、verdict、聚合、异步和结果。 |
| 练习与验收 | 先独立作答，再看参考答案；验收条件可观察、可执行，包含能暴露失败的反例。 |
| 下一课 | 解释本课边界及下一步增加什么。 |

## 制作流程与通过标准

### 先定义评测合同

- 写清输入、预期结果、可接受路径、工具约束、失败与未评分情况。
- 区分模型决策、工具实际执行和评分器；明确应用模型、裁判、数据生成器与模拟用户的角色。

### 准备最小代码与数据

- 依据本课Agent代码清单选择原项目片段，保留来源与改编说明。
- 共享模块只承载已经讲过的能力。每个任务在独立练习目录运行；验收数据不暴露给被测Agent。

### 实际运行并留下证据

- 先验证正常、错误和边界场景，再组织教材。记录模式、版本、参数、工具、退出码、文件结果、成本与错误。
- 真实模式实际调用模型；回放用于评分管线练习。任何预设输出不得冒充模型或Agent实测。

### 使用PocketFlow组织教材

- 将当前课代码、数据、运行结果、文档/源码依据、目标与验收要求组成明确材料包。
- 通过原版节点和必要课程适配生成正文；只生成当前课，不把整个集成Agent提前塞入。保存实际节点、调用与输入输出哈希。

### 审校、复跑与发布

- 核对正文代码和完整程序一致、结果与报告一致、来源可追溯。照着文档命令再运行。
- 更新Docker阅读器与GitHub；报告已通过、失败、跳过和未验证内容，不把旧测试成绩当新课验收。

## 工程结构与运行约定

- lessons/eNN_topic：README.zh.md、code.py、eval.py、cases.jsonl、source_walkthrough.md、exercises.md、solutions.md和真实示例报告。
- eval_course：课程启动、阅读器与已经介绍的基础能力；不提前隐藏全部Agent功能。
- knowledge_base：只读挂载的项目资料；workspaces：每次任务独立的可写练习目录；runs：持久化结果与轨迹。
- evaluation_private：独立验收数据与保留测试，不挂载给被测Agent。references：固定版本、源码引用和许可。generation：材料、约束、原稿和生成凭证。
- 第1课模型接入复用本机Codex登录：模型只返回下一步Bash动作或最终回答，真实命令由容器中的课程Agent执行。登录凭据留在本机。
- 教材生成与Agent运行分别记录。第1课采用确定性文件/输出/退出码验收；后续需要的LLM裁判单独配置。
- 模型使用达到预算或工具超时属于受控停止/失败，不能记为任务成功。知识库检索和专用文件工具不提前进入第1课。

## 逐课详细要求

### e01 最小编程 Agent 与第一份评测协议

前置：会Python，了解RAG/Agent；已准备Docker和可用模型入口。

学完能做什么：识别Agent循环、模型、Bash工具和独立验收器的职责；能解释真实行动与完成声明的区别。

评测对象：真实工具执行、停止与任务完成

- 知识点：任务、样本、判分器、数据集、阈值、运行配置
- 知识点：模型能力与应用质量
- 知识点：离线评测与线上观察。
- 知识点：最小 RAG 链路、组件与端到端评测、运行 ID、模型/提示词/数据版本、scorecard。

Agent代码增量：仅 agent_loop、run_bash、必要运行记录

边界：第1课不引入专用文件工具、检索、记忆、计划或协作；模型传输只是接入基础设施。

数据与案例：列出目录；创建并运行hello.py；运行已有脚本；命令失败/超时；给验收器输入假报成功的负例。

评分方案：文件集合、程序标准输出、命令退出码和真实工具轨迹；第一课不使用语义裁判替代状态事实。

实验步骤：先写预期与成功合同，再运行“在临时练习仓库列目录、创建并运行 hello.py，再注入假报成功”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：修改一个任务的成功条件并新增失败例；解释模型停止与任务完成为何不同。

验收：以文件内容与退出码验收；保存输入输出、版本与轨迹；区分回放和真实调用

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/dataset/dataset.py
- 源码依据：deepeval/deepeval/evaluate/evaluate.py
- 源码依据：ragas/src/ragas/dataset.py
- 源码依据：ragas/src/ragas/experiment.py
- 源码依据：learn-claude-code/s01_agent_loop/code.py

- 文档依据：https://deepeval.com/docs/evaluation-introduction
- 文档依据：https://docs.ragas.io/en/stable/concepts/experimentation/
- 文档依据：https://deepeval.com/tutorials/rag-qa-agent/evaluation
- 文档依据：https://docs.ragas.io/en/stable/tutorials/rag/

原课知识映射：s01, s09。实施状态：本轮先制作并验证。

### e02 工具、权限、轨迹与统一评测样本

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能构造可追溯执行记录并转换框架字段；能区分拒绝、异常与正常执行。

评测对象：工具决策与结果、权限拒绝、字段适配

- 知识点：input/actual_output/expected_output/retrieval_context
- 知识点：user_input/response/reference/retrieved_contexts
- 知识点：工具调用与多轮消息
- 知识点：必需字段
- 知识点：数据版本与开发/校准/留出集。
- 知识点：trace、span、轨迹、工具事件、输入输出、异常
- 知识点：端到端/完整轨迹/组件边界
- 知识点：trace 树和工具归属。

Agent代码增量：read/write/edit/glob dispatch、权限检查和记录 hook

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：缺字段、缺参数、权限拒绝、工具报错和多工具结果错位。

评分方案：字段/结构断言，加适用框架样本对象；以原始工具事件为依据。

实验步骤：先写预期与成功合同，再运行“构造成功、缺参、被拒绝、工具异常轨迹，转为两框架样本”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：为一个工具事件补齐字段映射；找出丢失退出码的记录并修复。

验收：逐字段可追溯；拒绝不当成功；数据分开发/校准/留出

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/test_case/conversational_test_case.py
- 源码依据：deepeval/deepeval/test_case/llm_test_case.py
- 源码依据：deepeval/deepeval/tracing/tracing.py
- 源码依据：ragas/src/ragas/dataset_schema.py
- 源码依据：learn-claude-code/s02_tool_use/code.py
- 源码依据：learn-claude-code/s03_permission/code.py
- 源码依据：learn-claude-code/s04_hooks/code.py

- 文档依据：https://deepeval.com/docs/evaluation-test-cases
- 文档依据：https://docs.ragas.io/en/stable/concepts/components/eval_sample/
- 文档依据：https://docs.ragas.io/en/stable/concepts/components/eval_dataset/
- 文档依据：https://deepeval.com/guides/guides-tracing-ai-agents
- 文档依据：https://deepeval.com/docs/evaluation-trajectory-based-llm-evals

原课知识映射：s02, s13。实施状态：第2课已制作并完成真实Docker实验，详见本课验收记录。

### e03 规则评分与 LLM 裁判

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能把主观质量写成评分标准，知道规则与语义裁判各自的适用域。

评测对象：格式、精确结果与语义标准

- 知识点：精确匹配、集合 precision/recall/F1、结构校验、规则断言
- 知识点：规则覆盖范围
- 知识点：对语义等价的误判。
- 知识点：LLM-as-a-Judge、评分维度、rubric、G-Eval、Aspect Critic、结构化 verdict 与理由
- 知识点：DAG 评分分支。

Agent代码增量：复用前课 Agent，仅加独立判分适配

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：同义答案、格式错误但内容正确、字符串相同却状态错误、rubric字段缺失。

评分方案：精确匹配/JSON/F1、DeepEval GEval/DAG、Ragas适用的Aspect/rubric，实际API按固定版本核对。

实验步骤：先写预期与成功合同，再运行“手算规则/F1，再比较 G-Eval、Aspect 类标准与 DAG 边界”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：手算工具集合F1；写一份可区分正反例的rubric；说明模型判据的不确定性。

验收：rubric 与字段一致；记录 verdict/理由；分清确定控制与模型随机性

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/dag/dag.py
- 源码依据：deepeval/deepeval/metrics/g_eval/g_eval.py
- 源码依据：ragas/src/ragas/metrics/collections/tool_call_f1/metric.py
- 源码依据：ragas/src/ragas/metrics/collections/tool_call_f1/util.py

- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/traditional/
- 文档依据：https://deepeval.com/guides/guides-building-custom-metrics
- 文档依据：https://deepeval.com/docs/metrics-llm-evals
- 文档依据：https://deepeval.com/guides/guides-g-eval-examples
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/aspect_critic/

原课知识映射：s03, s04。实施状态：后续逐课制作，本说明不代表已实现。

### e04 知识库检索：精度、召回与排序

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能区分相关性、排名和证据覆盖，选择需要或不需要reference的口径。

评测对象：相关性排序与 API/规范证据覆盖

- 知识点：Context Precision、相关性判定、排序敏感性
- 知识点：基于标注 ID 与基于 LLM/参考答案的口径
- 知识点：分母与空结果。
- 知识点：Context Recall、参考答案中的 claims、标注证据集合
- 知识点：coverage 与 precision 的区别
- 知识点：参考不完整时的局限。

Agent代码增量：知识库挂载与 search_knowledge，参考 SkillLoader 按需知识加载

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：关键API文档排末尾；两段必要证据漏一段；全相关但不够回答；空结果。

评分方案：ContextualPrecision/Recall/Relevancy与Ragas ContextPrecision/Recall及ID或证据集合规则。

实验步骤：先写预期与成功合同，再运行“查项目 API 文档，重排、加噪声、删必需片段”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：手算排序变化；构造高precision低recall，并指出参考资料不完整的影响。

验收：构造高 precision 低 recall；记录文档 ID/版本；区分 ID/reference/LLM 口径

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/contextual_precision/contextual_precision.py
- 源码依据：deepeval/deepeval/metrics/contextual_recall/contextual_recall.py
- 源码依据：ragas/src/ragas/metrics/collections/context_precision/metric.py
- 源码依据：ragas/src/ragas/metrics/collections/context_recall/metric.py
- 源码依据：learn-claude-code/s07_skill_loading/code.py

- 文档依据：https://deepeval.com/docs/metrics-contextual-precision
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/
- 文档依据：https://deepeval.com/docs/metrics-contextual-recall
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/

原课知识映射：s05, s06。实施状态：后续逐课制作，本说明不代表已实现。

### e05 Faithfulness：解释是否忠于检索证据

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能逐声明判断证据支持、未支持与矛盾，解释固定版本差异。

评测对象：回答声明相对本次证据的支持程度

- 知识点：Faithfulness、claim 拆解、支持/矛盾/信息不足、NLI
- 知识点：证据内一致性与外部事实正确性
- 知识点：不同框架的判定口径。

Agent代码增量：复用检索 Agent，加逐声明 SDK 记录

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：文档支持的API说明、未提及参数、矛盾返回值、混合陈述与无事实声明；证据改版。

评分方案：DeepEval FaithfulnessMetric与Ragas collections Faithfulness；逐声明verdict和空声明单独记录。

实验步骤：先写预期与成功合同，再运行“支持、未支持、矛盾、混合、空声明五类，接入已有回放再评真实输出”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：给一段编程解释拆claims；手算两种聚合；说明空声明高分不代表答对。

验收：手算固定版本分数；解释 borderline/NaN；证据变化拒用旧标注

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/faithfulness/faithfulness.py
- 源码依据：ragas/src/ragas/metrics/collections/faithfulness/metric.py

- 文档依据：https://deepeval.com/docs/metrics-faithfulness
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/

原课知识映射：s07。实施状态：后续逐课制作，本说明不代表已实现。

### e06 答案相关性、正确性、完整性与拒答

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能区别切题、正确、完整、语义相似与适当拒答。

评测对象：切题、正确、覆盖及适当拒答

- 知识点：Answer/Response Relevancy、Answer Correctness、Factual Correctness、语义相似度
- 知识点：reference 依赖
- 知识点：precision/recall 侧重
- 知识点：拒答与不可回答问题。

Agent代码增量：同一 Agent，加入 reference 和不可回答任务

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：忠于旧文档但实际错误；事实正确却答偏；遗漏一个用户要求；不可回答却编造。

评分方案：AnswerRelevancy、FactualCorrectness、AnswerCorrectness等适用指标；结合独立reference与业务判据。

实验步骤：先写预期与成功合同，再运行“相关但错、忠于旧文档、正确但答偏、证据不足编造四类”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：选择互补指标解释四类回答，标注每个指标需要的字段与reference。

验收：组合指标解释失败；核实 reference/版本；不用单一忠实度概括质量

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/answer_relevancy/answer_relevancy.py
- 源码依据：ragas/src/ragas/metrics/collections/answer_correctness/metric.py
- 源码依据：ragas/src/ragas/metrics/collections/factual_correctness/metric.py

- 文档依据：https://deepeval.com/docs/metrics-answer-relevancy
- 文档依据：https://deepeval.com/guides/guides-answer-correctness-metric
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness/

原课知识映射：s08。实施状态：后续逐课制作，本说明不代表已实现。

### e07 通过故障实验定位 RAG 失败

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能通过控制变量定位RAG失败位置，并维护bad case分类。

评测对象：没找到、找错、噪声干扰还是生成出错

- 知识点：故障注入、错误分类、Noise Sensitivity、检索/生成分离诊断、bad case 分析。

Agent代码增量：文档/检索/生成三个位置的可控故障开关

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：只改文档、检索、生成中一个位置；记录预期影响与实际差异。

评分方案：本课复用检索/回答指标，加入NoiseSensitivity及阶段级对照。

实验步骤：先写预期与成功合同，再运行“分别删 API 关键段、加旧规范/噪声、改提示词，控制其他变量”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：对失败报告写出证据、定位和待验证假设，而不是直接归因提示词。

验收：预期与实测分开；bad case 可定位到阶段和证据

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/contextual_relevancy/contextual_relevancy.py
- 源码依据：ragas/src/ragas/metrics/collections/noise_sensitivity/metric.py

- 文档依据：https://deepeval.com/guides/guides-rag-evaluation
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/noise_sensitivity/

原课知识映射：s10。实施状态：后续逐课制作，本说明不代表已实现。

### e08 构建、生成与审查评测数据集

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能从种子与文档建立候选数据，再审核、去重、分层和留出。

评测对象：任务覆盖、标注有效性与泄漏

- 知识点：DeepEval Synthesizer、Ragas TestsetGenerator、knowledge graph、personas、单跳/多跳、evolutions、质量过滤、重复与数据泄漏。

Agent代码增量：独立于被测 Agent 的离线数据生成与审核

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：不可回答问题、重复题、错误reference、单跳/多跳、不同难度、编程任务验收器。

评分方案：DeepEval Synthesizer、Ragas TestsetGenerator/知识图谱/场景/单多跳；候选质量规则与独立审核。

实验步骤：先写预期与成功合同，再运行“从规范文档用 Synthesizer/TestsetGenerator 生成候选题，补编程种子、单/多跳与不可回答样本”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：审核一批候选并给出去留理由；保留来源与审核状态；真实输出由Agent另行产生。

验收：来源/类别/难度、去重、人工待审与数据划分齐全；合成题不是已执行轨迹

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/synthesizer/synthesizer.py
- 源码依据：ragas/src/ragas/testset/synthesizers/generate.py

- 文档依据：https://deepeval.com/guides/guides-using-synthesizer
- 文档依据：https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/
- 文档依据：https://docs.ragas.io/en/stable/howtos/customizations/testgenerator/

原课知识映射：s11。实施状态：后续逐课制作，本说明不代表已实现。

### e09 版本比较、实验控制与统计解释

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能做同样本受控比较，解释分层差异、重复运行与统计不确定性。

评测对象：可靠改进、分层退化与成本权衡

- 知识点：受控实验、配对样本、提示词/检索参数迭代、质量/成本/延迟权衡
- 知识点：开发集选择与留出集验证。
- 知识点：逐样本配对差值、重复评分、分层报告、均值与失败率
- 知识点：bootstrap 区间入门、业务最小改进与统计不确定性。

Agent代码增量：只改一个检索/提示词因素，保留 Agent 功能可比

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：只改top-k或提示词；总体提升但某类退化；重复Judge产生分歧；小样本宽区间。

评分方案：逐样本配对差、分层成功率、bootstrap区间、成本/延迟；统计方法标课程补充。

实验步骤：先写预期与成功合同，再运行“配对比较，重复评分，做分层与 bootstrap 区间”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：写一份与样本规模相称的结论；不把区间跨零当成已证明无差异。

验收：报告逐样本差值/区间；留出不调参；统计为方法补充

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：ragas/src/ragas/experiment.py

- 文档依据：https://deepeval.com/tutorials/rag-qa-agent/improvement
- 文档依据：https://deepeval.com/guides/guides-optimizing-hyperparameters
- 文档依据：https://docs.ragas.io/en/stable/howtos/applications/evaluate-and-improve-rag/
- 文档依据：https://docs.ragas.io/en/stable/concepts/experimentation/
- 文档依据：https://docs.ragas.io/en/stable/concepts/datasets/
- 文档依据：https://deepeval.com/guides/guides-regression-testing-in-cicd
- 文档依据：https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html

原课知识映射：s12, s20。实施状态：后续逐课制作，本说明不代表已实现。

### e10 工具选择、参数、调用顺序与 MCP

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能区分工具名、参数、顺序、集合与序列口径，评价MCP接入。

评测对象：选工具、参数、顺序、漏调误调与重复

- 知识点：ToolCorrectness、ToolCallAccuracy、ToolCallF1、ArgumentCorrectness
- 知识点：集合与序列
- 知识点：额外参数、重复调用、无调用边界。

Agent代码增量：现有工具加 MCP tool pool 最小片段和本地模拟服务

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：读文件→编辑→测试中的错路径、错参数、漏调、乱序、重复与无需工具。

评分方案：DeepEval ToolCorrectness/ArgumentCorrectness与Ragas ToolCallAccuracy/F1；额外的重复/状态规则。

实验步骤：先写预期与成功合同，再运行“读文件→编辑→运行测试，注入错路径/错参/乱序/重复，比较工具池接入前后”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：对多种合法路径设合同；解释集合F1为何不能单独惩罚重复执行。

验收：解释 ToolCorrectness/ArgumentCorrectness、ToolCallAccuracy/F1；集合 F1 不承担重复惩罚；接受多合法路径

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/tool_correctness/tool_correctness.py
- 源码依据：ragas/src/ragas/metrics/collections/tool_call_accuracy/metric.py
- 源码依据：ragas/src/ragas/metrics/collections/tool_call_f1/metric.py
- 源码依据：learn-claude-code/s14_mcp_plugin/code.py

- 文档依据：https://deepeval.com/docs/metrics-tool-correctness
- 文档依据：https://deepeval.com/docs/metrics-argument-correctness
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/

原课知识映射：s14。实施状态：后续逐课制作，本说明不代表已实现。

### e11 代码任务真实完成与自定义指标

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能核实代码任务真实完成，写有适用域的业务指标，并审查停止判断。

评测对象：真实修复与完成声明是否一致

- 知识点：Task Completion、AgentGoalAccuracy、reference outcome、外部状态断言
- 知识点：结果与路径
- 知识点：停止条件与证据。
- 知识点：规则/LLM/复合指标、BaseMetric、结构化输出、measure/a_measure/ascore、解释与错误状态
- 知识点：适用域。

Agent代码增量：目标状态和停止审查片段，独立外部验收器

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：真正修复、只改说明、删除测试、假报成功、部分完成、目标无法完成。

评分方案：TaskCompletion、AgentGoalAccuracy、自定义BaseMetric与独立文件/diff/保留测试断言。

实验步骤：先写预期与成功合同，再运行“真实修复、只改说明、删测试、假报成功、重复改；实现业务指标”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：完成声明与状态分别报告；自定义指标包含正常、错误、边界和未评分情况。

验收：独立核验文件/diff/验收测试；区分模型推断与状态事实；自定义指标有反例/适用域

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/base_metric.py
- 源码依据：deepeval/deepeval/metrics/task_completion/task_completion.py
- 源码依据：ragas/src/ragas/metrics/collections/agent_goal_accuracy/metric.py
- 源码依据：ragas/src/ragas/metrics/collections/base.py
- 源码依据：learn-claude-code/s17_goal_loop/code.py

- 文档依据：https://deepeval.com/docs/metrics-task-completion
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/
- 文档依据：https://deepeval.com/guides/guides-building-custom-metrics
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/general_purpose/

原课知识映射：s15, s21。实施状态：后续逐课制作，本说明不代表已实现。

### e12 多轮、上下文压缩与持久记忆

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能评跨轮条件、上下文压缩、持久记忆与模拟用户。

评测对象：跨轮约束、压缩和旧记忆影响

- 知识点：ConversationalTestCase、Turn、MultiTurnSample、上下文保持、指令变化、知识保留、对话完整性、模拟器终止与场景覆盖。

Agent代码增量：ContextCompactor 与记忆读写，保留工具和权限

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：保持函数签名后追加条件；长输出压缩；过期或污染记忆；模拟用户过早结束。

评分方案：ConversationalTestCase/Turn、MultiTurnSample、KnowledgeRetention/ConversationCompleteness及适用rubric。

实验步骤：先写预期与成功合同，再运行“先要求保留函数签名，再加约束和长输出，比较压缩前后，固定场景模拟用户”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：轮级与会话级结果分开；约束证据对齐；模拟器本身单独复核。

验收：轮级与会话级分开；证据对齐；不得丢约束或错用记忆；模拟器单独复核

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/simulator/conversation_simulator.py
- 源码依据：deepeval/deepeval/test_case/conversational_test_case.py
- 源码依据：learn-claude-code/s08_context_compact/code.py
- 源码依据：learn-claude-code/s09_memory/code.py

- 文档依据：https://deepeval.com/guides/guides-multi-turn-evaluation
- 文档依据：https://deepeval.com/guides/guides-multi-turn-simulation
- 文档依据：https://docs.ragas.io/en/stable/howtos/applications/evaluating_multi_turn_conversations/

原课知识映射：s16。实施状态：后续逐课制作，本说明不代表已实现。

### e13 计划、任务依赖、子 Agent 与协作

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能区分计划质量、遵从度、依赖执行与整体完成，评价子任务交接。

评测对象：计划质量/遵从、依赖与组件/整体结果

- 知识点：Plan Quality、Plan Adherence、可观察计划与执行证据
- 知识点：任务依赖
- 知识点：多 Agent 的组件与整体评价。

Agent代码增量：TodoManager、TaskStore、子任务隔离、最小协作接口依次引入

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：好/坏/缺计划；依赖未满足；交接信息丢失；并行修改冲突与多种合法路径。

评分方案：PlanQuality/PlanAdherence、任务依赖断言和组件/整体评价；Ragas适用rubric为定制而非同名等价。

实验步骤：先写预期与成功合同，再运行“跨文件 bug，好/坏/缺计划，依赖未满足、交接丢信息和并行冲突”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：只使用显式计划和可观察事件；缺计划默认分单列；任务与结果可追溯。

验收：只评显式计划与事件；无计划默认分单独标记；依赖/子任务可追溯；无需唯一轨迹

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/plan_adherence/plan_adherence.py
- 源码依据：deepeval/deepeval/metrics/plan_quality/plan_quality.py
- 源码依据：learn-claude-code/s05_todo_write/code.py
- 源码依据：learn-claude-code/s10_task_system/code.py
- 源码依据：learn-claude-code/s06_subagent/code.py
- 源码依据：learn-claude-code/s13_agent_teams/code.py

- 文档依据：https://deepeval.com/docs/metrics-plan-quality
- 文档依据：https://deepeval.com/docs/metrics-plan-adherence
- 文档依据：https://deepeval.com/guides/guides-ai-agent-evaluation-metrics

原课知识映射：s17。实施状态：后续逐课制作，本说明不代表已实现。

### e14 后台任务、调度、效率、成本与稳定性

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能评价后台/调度正确性，并同时分析成功率、效率、恢复和资源消耗。

评测对象：长命令/超时/重试/通知/定时触发与效率

- 知识点：Step Efficiency、步数/重试/异常、工具调用成本、token/延迟、预算、重复运行成功率
- 知识点：计划效率与实际效率。

Agent代码增量：后台通知、受控调度与既有协作记录

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：后台测试完成通知、超时恢复、重复检索、受控时间触发、失败重试。

评分方案：StepEfficiency、步数/重试/超时/重复运行成功率；应用与裁判费用及延迟分开。

实验步骤：先写预期与成功合同，再运行“模拟测试超时、重复检索、后台完成、定时触发，重复同一任务”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：少步骤不自动更优；通知和状态一致；重复运行与成本完整记录。

验收：成功率与步数/延迟分报；应用和裁判成本分开；少步骤不必然更优；受控时钟/状态验收

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/step_efficiency/step_efficiency.py
- 源码依据：learn-claude-code/s11_background_tasks/code.py
- 源码依据：learn-claude-code/s12_cron_scheduler/code.py

- 文档依据：https://deepeval.com/docs/metrics-step-efficiency
- 文档依据：https://docs.ragas.io/en/stable/howtos/customizations/run_config/
- 文档依据：https://docs.ragas.io/en/stable/howtos/customizations/metrics/_cost/

原课知识映射：s18。实施状态：后续逐课制作，本说明不代表已实现。

### e15 裁判校准、偏差与中文适配

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能用独立标注校准裁判，发现顺序、篇幅、自偏好和语言偏差。

评测对象：裁判对齐及顺序/篇幅/措辞偏差

- 知识点：人工复核集、Judge alignment、位置/篇幅/自偏好、裁判提示词、中文适配、分歧分析
- 知识点：局部改进与留出验证。

Agent代码增量：Agent 不变，只调整裁判，保留独立复核集

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：交换答案顺序、改写长度、中英改写、校准前后对比；未审核标签。

评分方案：G-Eval与适用的Ragas judge alignment/语言适配；校准集和留出复核集。

实验步骤：先写预期与成功合同，再运行“打乱顺序、改写长度、双语改写，校准后在留出检验”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：保留标准、版本、人工标签与分歧；没有人工审核就标记；不能借校准泄漏留出集。

验收：保留独立标签、版本和分歧；未审核明确标记；中文适配标准不漂移

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/metrics/g_eval/g_eval.py
- 源码依据：ragas/src/ragas/experiment.py

- 文档依据：https://docs.ragas.io/en/stable/howtos/applications/align-llm-as-judge/
- 文档依据：https://docs.ragas.io/en/stable/howtos/customizations/metrics/metrics_language_adaptation/
- 文档依据：https://arxiv.org/abs/2306.05685

原课知识映射：s19。实施状态：后续逐课制作，本说明不代表已实现。

### e16 综合回归、完整调用链与结课评测

前置：已完成前面课程；仅复用已经介绍的共享能力。

学完能做什么：能完成可复核评测、CI回归、工作流续跑和完整源码链分析。

评测对象：功能保留、完整任务与回归

- 知识点：pytest/CI、质量门禁、关键失败单独拦截、夜间较重评测、生产 trace 转样本、版本与成本记录。
- 知识点：指标基类、输入校验、prompt/schema、模型调用、聚合、异步
- 知识点：同名指标实现差异
- 知识点：文档、实现与测试三方对照。
- 知识点：评测协议、数据审计、指标选型、双框架复现、受控实验、错误分析、可靠性、成本、回归的完整闭环。

Agent代码增量：到结课才引入集成视图、workflow journal/续跑，并核对全部17机制

边界：当前课不提前导入尚未介绍的后续机制；按小节逐项增加能力。

数据与案例：bad case进入回归；注入退化；中断续跑；基线与改进；完整追踪Faithfulness和工具指标。

评分方案：pytest/CI门禁、关键失败单独拦截、生产trace转样本、端到端/组件/轨迹评价与17机制清单。

实验步骤：先写预期与成功合同，再运行“bad case 入 CI；流程中断续跑；追踪 Faithfulness 与工具指标调用链；基线/改进报告”；保存轨迹与状态，用独立评分器检查，最后解释差异。

练习：交付数据/配置/代码/逐样本结果/限制；17机制逐项标状态；别人按命令可复现。

验收：交付数据/配置/代码/逐样本结果/复现命令；关键失败门禁；能力清单有归属与测试计划；未实现不标完成

本课产物：可运行入口、评分入口、样本、源码导读、练习/解答、模式明确的逐样本示例报告。

源码分析：按所选指标适用部分追踪输入校验、prompt/schema、模型调用、verdict、聚合、异步与结果对象；规则指标说明不适用项。

- 源码依据：deepeval/deepeval/evaluate/evaluate.py
- 源码依据：deepeval/deepeval/metrics/faithfulness/faithfulness.py
- 源码依据：ragas/src/ragas/evaluation.py
- 源码依据：ragas/src/ragas/metrics/collections/faithfulness/metric.py
- 源码依据：ragas/src/ragas/metrics/collections/tool_call_accuracy/metric.py
- 源码依据：learn-claude-code/s15_integrated_harness/code.py
- 源码依据：learn-claude-code/s16_workflow_runtime/code.py

- 文档依据：https://deepeval.com/guides/guides-regression-testing-in-cicd
- 文档依据：https://deepeval.com/guides/guides-llm-observability
- 文档依据：https://docs.ragas.io/en/stable/howtos/applications/add_to_ci/
- 文档依据：https://deepeval.com/docs/metrics-faithfulness
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/
- 文档依据：https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/
- 文档依据：https://deepeval.com/guides/guides-ai-agent-evaluation
- 文档依据：https://deepeval.com/guides/guides-rag-evaluation
- 文档依据：https://docs.ragas.io/en/stable/tutorials/agent/

原课知识映射：s22, s23, s24。实施状态：后续逐课制作，本说明不代表已实现。

## 全课程一致的验收清单

- 运行：从干净Docker环境启动；必要模型配置写清楚；无密钥时不能将预设回放伪装成真实模型。
- 证据：问题、模型动作、工具返回、退出码、文件结果、版本、运行ID和错误可追溯。
- 判分：正常、错误、边界均有预期；失败、跳过、未评分分别记录；不可将NaN直接当0。
- 数据：来源、类别、审核与划分明确；合成数据和真实轨迹分开；留出数据不用于调参。
- 教学：正文片段与完整代码一致；关键函数逐段解释；有与前课差异和下一课边界。
- 来源：指标引用固定源码和官方文档；同名指标分别说明，附录专题保留入口。
- 交付：Markdown教材、可运行代码、Docker、GitHub、示例报告和核验记录；课程说明同步飞书。

## 实施批次与当前顺序

- 本轮先交付这份16课详细设计和制作规范并同步飞书，之后才清理旧样章并制作第1课。
- 第1课通过后，后续逐步制作第2—5课，形成工具、知识库、真实回答与指标的第一条完整链路。
- 第6—9课补齐质量、故障诊断、数据生成和版本比较；第10—14课覆盖Agent扩展；第15—16课校准与综合回归。
- 每课完成代码和实验，再由PocketFlow组织教材并审校发布。课程原始大纲、生成凭证和源码索引在仓库中保留。

## 版本与公开参考

deepeval：https://github.com/confident-ai/deepeval @ 34db63dd005ebc9a905c8ef4741ae0687c93c14c

ragas：https://github.com/vibrantlabsai/ragas @ 8c63f10d500c44efbf24fdb9e2920de2104c321c

learn_claude_code：https://github.com/shareAI-lab/learn-claude-code @ 448c75bb596917ad196cc1fb7558f459c5c50fdd

pocketflow_tutorial：https://github.com/The-Pocket/PocketFlow-Tutorial-Codebase-Knowledge @ 05b24cbbb0fe409c5e23c9791f0342f07524ffdc

课程仓库：https://github.com/lovits/learn-agent-evaluation

## 第2课实际交付

[飞书教材与验收结果](https://my.feishu.cn/docx/KVAkdoPHlofNEOxSPQqcfXuenfn)。5条开发任务全部通过，16次真实模型请求、14次工具请求；四种SDK样本可导出并恢复。本地与Docker断网32项测试通过。校准与留出各2条未执行，不计入成绩。

## 第3课实际交付

[教材与验收](https://my.feishu.cn/docx/J6iAd17kSonCjCxqlOWcjyGonTg)。规则评分、GEval、DAGMetric、AspectCritic已实测，两轮共15次真实裁判请求；原始分歧和标准修订分别保留。44项本地及Docker断网测试通过。

## 第4课实际交付

[飞书教材与验收](https://my.feishu.cn/docx/SPD5dOh7vo7LVtxrbykc7tgSn4g)：真实Agent检索与产物独立验收通过；最终23次原生裁判请求，0个指标运行错误。首次失败、修复和完整请求数分别留档，挂载更换验证通过，本地与Docker断网51项测试通过。

## 第5课实际交付

[飞书教材与验收](https://my.feishu.cn/docx/VnU4dKOOHoMJhEx55jpcQ83fn4e)：逐声明证据核对、DeepEval与Ragas原生Faithfulness及源码分析已完成。复用第4课真实Agent记录，主实验34次、来源封装补测5次裁判请求，最终0个运行错误。默认borderline策略、空声明、来源身份丢失及证据改版分别解释；本地与Docker断网59项测试通过。

## 第6课实际交付

[飞书教材与验收](https://my.feishu.cn/docx/IrtXdlfrVoYPZcxNPkLccRzHn0b)：切题、参考正确性、需求完整性、语义相似与拒答政策分别说明，保留双框架固定源码分析。八条构造回答与一条旧Agent真实产物再评；主实验93次、reference澄清补测4次请求，最终0个指标错误。两轮原始结果分开留存，人工向量与计数标为演示；本地与Docker断网65项测试通过。PocketFlow实际生成，14个正文小节已完成humanizer审校。

## 第7课实际交付

[飞书教材与验收](https://my.feishu.cn/docx/Yueedp2OAo3ljdxc5Fich78ZnWc)：按Learn Claude Code的讲解、组织和带读语气完成六部分正文与六步短代码，12节已审校。六组真实Agent干预留下资料、检索前后与实际文件证据；25次Agent模型请求，两轮裁判共108次请求，SDK错误0。初轮评分输入问题、修订与原始结果分开留存。本地与Docker断网75项测试通过。

## 第1课图文改写

[第1课新版教材、配图与验收](https://my.feishu.cn/docx/ZIlFdoY5EoFvaExYY9dcvQnnnce)：按Learn Claude Code的六部分正文和六步短代码重写，补入Agent/Harness循环、独立验收两张关键结构图，保留源码导读、练习、答案和首次实验。PocketFlow实际生成一次，humanizer审校12节。本地与Docker断网78项测试通过，浏览器已检查两图加载与缩放。原Agent代码、样本和历史报告保持一致，本次未重新测量Agent。
