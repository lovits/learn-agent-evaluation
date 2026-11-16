# 《从 Learn Claude Code 编程 Agent 学 RAG 与 Agent 评测》课程设计

> 状态：第1至9课已制作并通过各课适用的真实Docker实验；第1至7课已重写，第8、9课按同一标准制作。其余7课与17机制完整迁移继续推进。

## 原项目学习方式与课程改编

Learn Claude Code 采用“遇到一个具体困难，只增加一个最小机制”的递进方式：从 `agent_loop + bash` 起步，逐步加入工具分发、权限、hooks、计划、子任务、skills、上下文压缩、记忆、任务图、后台任务、调度、团队、MCP、集成运行、流程续跑和目标闭环。

本课程沿用这种教学节奏，但每课改为：

评测问题 → 被测对象 → 最小 Agent 代码增量 → 数据与评分标准 → 故障或对照实验 → 结果解释 → 指标源码 → 外部验收。

第1课不会导入完整集成 Agent；正文只给当前评测问题必需的代码片段，完整可执行版本放入当课 `code.py`。集成视图、workflow journal 和17项机制总核对到第16课才出现。

知识库固定为项目、API、架构和开发规范文档。Docker 中知识库只读挂载；练习仓库和结果目录可写；留出验收数据独立保管，不暴露给被测 Agent。文件、diff、退出码和保留测试用于核实客观状态；模型裁判用于判断语义、计划或解释质量，两类结果分别报告。

原项目依据：[s01 教材](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/README.zh.md)、[s02 教材](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s02_tool_use/README.zh.md)。

## DeepEval 与 Ragas 能力分工

| 能力 | DeepEval | Ragas | 课程用法 |
|---|---|---|---|
| 样本与运行 | LLMTestCase、ConversationalTestCase、EvaluationDataset、trace/span | SingleTurnSample、MultiTurnSample、EvaluationDataset、experiment | 先形成统一业务记录，再做框架适配 |
| RAG | Contextual Precision/Recall/Relevancy、Faithfulness、Answer Relevancy | Context Precision/Recall、Faithfulness、Factual Correctness、Noise Sensitivity | 分开评检索排序、覆盖、证据忠实和答案质量 |
| Agent | Tool、Argument、Task Completion、Plan、Step Efficiency | ToolCallAccuracy/F1、AgentGoalAccuracy | 轨迹语义评分不替代文件与测试验收 |
| 数据生成 | Synthesizer、对话模拟 | TestsetGenerator、知识图谱、persona、单/多跳 | 只生成待审核候选，不冒充真实执行轨迹 |
| 扩展与回归 | BaseMetric、异步、pytest/CI、tracing | collections、自定义指标、RunConfig、成本记录 | 固定版本，保存逐样本结果、错误和费用 |
| 裁判校准 | rubric、G-Eval、DAG、阈值与理由 | Judge alignment、语言适配 | 校准集与留出集分开，分析偏差和分歧 |

统一数据记录至少包含：任务ID、输入、知识库及证据版本、reference或外部验收器、允许的工具约束、类别、难度、来源、审核状态和数据划分。运行后追加回答、检索结果、工具事件、退出码、diff、运行ID、模型配置、裁判配置、延迟和成本。

真实 SDK 配合预设输出只能验证评分管线，不能称为模型准确率实验。真实 Agent 与真实裁判分别配置接口；回放结果和真实调用结果不得混报。

官方入口：[DeepEval 指标](https://deepeval.com/docs/metrics-introduction)、[DeepEval Agent tracing](https://deepeval.com/docs/getting-started-agents)、[DeepEval Synthesizer](https://deepeval.com/docs/golden-synthesizer)、[Ragas 指标](https://docs.ragas.io/en/stable/concepts/metrics/overview/)、[Ragas Agent 指标](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)、[Ragas 测试集生成](https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/)。

## e01 最小编程 Agent 与第一份评测协议

- **评测对象：** `agent_loop`、`run_bash`、停止行为和任务是否真实完成。
- **知识点：** 任务、样本、判分器、数据集、阈值、运行配置；模型能力与应用质量；离线评测、线上观察；RAG链路概览（检索代码在e04引入）、运行ID和scorecard。
- **Agent代码增量：** 仅引入循环、bash执行和必要运行记录。
- **实验：** 在临时练习仓库列目录、创建并运行 `hello.py`，再注入“未创建文件却宣称成功”的输出。
- **验收：** 由文件内容和退出码确认完成；保存输入、输出、版本与轨迹；回放和真实调用分别标记。
- **来源：** [Agent循环源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/code.py)、[DeepEval evaluation](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)、[Ragas experimentation](https://docs.ragas.io/en/stable/concepts/experimentation/)。

## e02 工具、权限、轨迹与统一评测样本

- **评测对象：** 工具选择与结果、权限拒绝、异常和两框架字段适配。
- **知识点：** DeepEval与Ragas样本字段；多轮消息；trace、span、工具事件、异常；端到端、组件和完整轨迹；开发、校准、留出划分。
- **Agent代码增量：** 加入 read/write/edit/glob 分发、权限检查和记录hook。
- **实验：** 构造成功、缺参、权限拒绝和工具异常轨迹，转换成两框架样本。
- **验收：** 字段逐项可追溯；拒绝不能记为成功；验收数据与开发数据隔离。
- **来源：** [工具源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s02_tool_use/code.py)、[权限源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s03_permission/code.py)、[DeepEval test cases](https://deepeval.com/docs/evaluation-test-cases)、[Ragas EvalSample](https://docs.ragas.io/en/stable/concepts/components/eval_sample/)。

## e03 规则评分与 LLM 裁判

- **评测对象：** 格式、精确结果、集合匹配和语义标准。
- **知识点：** 精确匹配、precision/recall/F1、结构断言；G-Eval、Aspect Critic、DAG、rubric、结构化verdict与理由。
- **Agent代码增量：** Agent不变，增加独立规则与模型裁判适配器。
- **实验：** 手算集合F1；比较规则、G-Eval、Aspect类标准和DAG分支的边界案例。
- **验收：** rubric与输入字段一致；保存verdict和理由；确定性评分与模型随机性分开报告。
- **来源：** [DeepEval G-Eval源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)、[Ragas ToolCallF1源码](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/metric.py)、[Aspect Critic](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/aspect_critic/)。

## e04 知识库检索：精度、召回与排序

- **评测对象：** API、架构和规范证据的相关性、排序及覆盖。
- **知识点：** Context Precision、Context Recall、排序敏感性、claims覆盖；文档ID、reference和LLM判定口径；空结果与参考不完整。
- **Agent代码增量：** 只读知识库挂载和 `search_knowledge`，参考SkillLoader的按需加载方式。
- **实验：** 查询项目API文档，依次重排、加噪声和删除必需片段。
- **验收：** 构造高precision低recall案例；保存文档ID与版本；三种评测口径分列。
- **来源：** [Skill loading源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s07_skill_loading/code.py)、[DeepEval Contextual Precision](https://deepeval.com/docs/metrics-contextual-precision)、[Ragas Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)。

## e05 Faithfulness：解释是否忠于检索证据

- **评测对象：** 回答中的声明是否得到本次检索证据支持。
- **知识点：** claim拆解、支持、矛盾、信息不足、NLI；证据内一致性与外部事实正确性的区别；两框架口径。
- **Agent代码增量：** 复用检索Agent，增加逐声明SDK输入和评分记录。
- **实验：** 重新制作编程知识的忠实度案例，覆盖支持、未支持、矛盾、混合、空声明；随后规划接入真实Agent输出。
- **验收：** 对固定案例手算预期分数；解释borderline和NaN；证据版本改变后旧标注失效。预设输出阶段只验评分管线。
- **来源：** [DeepEval Faithfulness源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py)、[Ragas Faithfulness源码](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py)。

## e06 答案相关性、正确性、完整性与拒答

- **评测对象：** 回答是否切题、正确、覆盖充分，并在证据不足时适当拒答。
- **知识点：** Answer/Response Relevancy、Answer Correctness、Factual Correctness、语义相似度、reference依赖及precision/recall侧重。
- **Agent代码增量：** 同一Agent增加reference和不可回答任务。
- **实验：** 比较“相关但错、忠于旧文档、正确但答偏、证据不足却编造”。
- **验收：** 核对reference和知识版本；用组合指标解释失败，不以Faithfulness概括全部质量。
- **来源：** [DeepEval Answer Relevancy源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/answer_relevancy/answer_relevancy.py)、[Ragas Factual Correctness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness/)。

## e07 通过故障实验定位 RAG 失败

- **评测对象：** 没找到、找错、受噪声干扰或生成阶段出错。
- **知识点：** 故障注入、错误分类、Noise Sensitivity、检索/生成分离诊断和bad case分析。
- **Agent代码增量：** 在文档、检索和生成三个位置加入可控故障开关。
- **实验：** 分别删除API关键段、加入旧规范或噪声、修改生成提示词，每次只改变一项。
- **验收：** 预期影响与实际结果分栏；每个bad case可定位到阶段和证据。
- **来源：** [DeepEval Contextual Relevancy源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py)、[Ragas Noise Sensitivity](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/noise_sensitivity/)。

## e08 构建、生成与审查评测数据集

- **评测对象：** 任务覆盖、标注有效性、重复、泄漏和审核状态。
- **知识点：** Synthesizer、TestsetGenerator、知识图谱、persona、单跳/多跳、evolution、质量过滤和数据划分。
- **Agent代码增量：** 不修改被测Agent；建立独立离线生成与审核流程。
- **实验：** 从规范文档生成候选题，补充编程种子、单/多跳和不可回答任务。
- **验收：** 来源、类别、难度、去重、审核状态和划分齐全；候选题不得标为已执行轨迹。
- **来源：** [DeepEval Synthesizer源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/synthesizer.py)、[Ragas生成器源码](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/generate.py)。

## e09 版本比较、实验控制与统计解释

- **评测对象：** 改动是否带来可靠提升、分层退化及质量/成本/延迟权衡。
- **知识点：** 受控实验、配对差值、重复评分、分层报告、bootstrap区间、最小业务改进和留出验证。
- **Agent代码增量：** 每轮只改变一个提示词或检索因素，保持Agent能力可比。
- **实验：** 在同一批配对任务上比较版本，重复裁判评分并计算分层bootstrap区间。
- **验收：** 报告逐样本差值和区间；留出集不参与调参；统计方法标为课程补充。
- **来源：** [Ragas experiment源码](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)。

## e10 工具选择、参数、调用顺序与 MCP

- **评测对象：** 工具选择、参数、顺序、漏调、误调和重复调用。
- **知识点：** ToolCorrectness、ArgumentCorrectness、ToolCallAccuracy、ToolCallF1；集合与序列；额外参数、重复和空调用。
- **Agent代码增量：** 在现有工具池中加入最小MCP片段和本地模拟服务。
- **实验：** 执行“读文件→编辑→测试”，注入错路径、错参、乱序和重复，并比较接入前后。
- **验收：** 接受多种合法路径；分别解释四类指标；不让集合F1承担重复惩罚。
- **来源：** [MCP源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s14_mcp_plugin/code.py)、[DeepEval Tool Correctness](https://deepeval.com/docs/metrics-tool-correctness)、[Ragas Agent指标](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)。

## e11 代码任务真实完成与自定义指标

- **评测对象：** 代码是否真实修复，以及完成声明是否符合仓库状态。
- **知识点：** Task Completion、AgentGoalAccuracy、reference outcome、外部状态断言；BaseMetric、`measure/a_measure/ascore`、结构化输出和适用域。
- **Agent代码增量：** 加入目标状态、停止审查片段和独立外部验收器。
- **实验：** 真实修复、只改说明、删除测试、假报成功和重复修改；实现一个业务复合指标。
- **验收：** 文件、diff、退出码和保留测试报告事实；模型裁判单独报告语义判断；自定义指标含反例和适用域。
- **来源：** [Goal loop源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s17_goal_loop/code.py)、[DeepEval BaseMetric源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/base_metric.py)、[Ragas AgentGoalAccuracy源码](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/agent_goal_accuracy/metric.py)。

## e12 多轮、上下文压缩与持久记忆

- **评测对象：** 跨轮约束、压缩损失和旧记忆污染。
- **知识点：** ConversationalTestCase、Turn、MultiTurnSample、知识保持、指令变化、会话完整性、场景覆盖与模拟终止。
- **Agent代码增量：** 加入ContextCompactor和记忆读写，保留工具与权限。
- **实验：** 先要求保持函数签名，再追加约束和长输出，对比压缩前后及有无旧记忆。
- **验收：** 轮级和会话级分别评分；检查约束证据；模拟用户输出单独复核。
- **来源：** [Context compact源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s08_context_compact/code.py)、[Memory源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s09_memory/code.py)、[DeepEval多轮评测](https://deepeval.com/guides/guides-multi-turn-evaluation)。

## e13 计划、任务依赖、子 Agent 与协作

- **评测对象：** 计划质量、遵从、依赖处理、交接和组件/整体结果。
- **知识点：** Plan Quality、Plan Adherence、显式计划与执行证据、任务依赖及多Agent评价。
- **Agent代码增量：** 依次加入TodoManager、TaskStore、子任务隔离和最小协作接口。
- **实验：** 跨文件bug；设置好计划、坏计划、无计划、未满足依赖、交接丢失和并行冲突。
- **验收：** 只评可观察计划和事件；无计划单独标记；依赖与子任务可追溯，不要求唯一轨迹。
- **来源：** [Todo源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s05_todo_write/code.py)、[Subagent源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s06_subagent/code.py)、[DeepEval Plan Quality](https://deepeval.com/docs/metrics-plan-quality)。

## e14 后台任务、调度、效率、成本与稳定性

- **评测对象：** 长命令、超时、重试、通知、定时触发、效率和重复运行稳定性。
- **知识点：** Step Efficiency、步数、异常、工具成本、token、延迟、预算和成功率；计划效率与实际效率。
- **Agent代码增量：** 加入后台通知、受控调度和既有协作记录。
- **实验：** 模拟测试超时、重复检索、后台完成和定时触发，多次运行同一任务。
- **验收：** 成功率、步数和延迟分报；应用模型与裁判成本分报；以受控时钟和状态验收。
- **来源：** [后台任务源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s11_background_tasks/code.py)、[调度源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s12_cron_scheduler/code.py)、[DeepEval Step Efficiency](https://deepeval.com/docs/metrics-step-efficiency)。

## e15 裁判校准、偏差与中文适配

- **评测对象：** 裁判与人工标准的对齐，以及顺序、篇幅、措辞和语言偏差。
- **知识点：** 人工复核集、Judge alignment、位置/篇幅/自偏好、提示词、中文适配和分歧分析。
- **Agent代码增量：** 被测Agent不变，只调整裁判；校准集和留出复核集隔离。
- **实验：** 打乱答案顺序、改变长度、进行中英双语改写；校准后在留出集检验。
- **验收：** 保留人工标签、裁判版本和分歧；未审核样本明确标记；中文适配不得改变原评分标准。
- **来源：** [DeepEval G-Eval源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)、[Ragas Judge alignment](https://docs.ragas.io/en/stable/howtos/applications/align-llm-as-judge/)。

## e16 综合回归、完整调用链与结课评测

- **评测对象：** 完整任务、功能保留、中断续跑、关键失败和版本回归。
- **知识点：** pytest/CI、质量门禁、生产trace转样本、版本与成本；输入校验→prompt/schema→模型调用→verdict→聚合→异步→结果对象；同名指标差异。
- **Agent代码增量：** 首次引入集成视图、workflow journal和续跑，核对全部17项机制。
- **实验：** 将bad case加入CI；模拟流程中断续跑；追踪Faithfulness与工具指标调用链；规划基线/改进报告。
- **验收：** 交付数据、配置、代码、逐样本结果和复现命令；关键失败单独门禁；能力清单记录归属、测试计划和真实状态。
- **来源：** [集成源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s15_integrated_harness/code.py)、[Workflow源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s16_workflow_runtime/code.py)、[DeepEval回归指南](https://deepeval.com/guides/guides-regression-testing-in-cicd)、[Ragas evaluation源码](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/evaluation.py)。

## 分阶段制作计划

| 阶段 | 输入 | 产物 | 通过条件 |
|---|---|---|---|
| 0. 固定环境与协议 | 三个仓库固定commit、知识库、角色配置 | 版本锁、Docker挂载、统一样本schema、回放/真实模式说明 | 知识库只读；`workspaces/`与`runs/`可写；验收集独立；Agent、裁判、生成器分别配置 |
| 1. 先行样章 | e01、e02、编程版第5课材料 | e01/e02及编程版e05 | 不导入集成Agent；回放管线与真实Agent接口分开；编程案例可由外部断言复核 |
| 2. RAG评测批次 | e03–e08 | 规则/裁判、检索、回答、故障和数据集课程 | 每课可独立运行；证据有版本；生成数据有审核和划分 |
| 3. Agent评测批次 | e09–e14 | 比较统计、工具、完成、多轮、协作、效率课程 | 逐样本与聚合报告齐全；事实验收和模型语义分报；成本和错误不遗漏 |
| 4. 校准与结课 | e15–e16 | 校准报告、CI门禁、能力核对和结课评测 | 留出集未用于调参；17机制逐项标记计划/已实现/已验证，不能以归属代替验证 |
| 5. GitHub回归 | 固定基线、bad cases、版本锁 | 轻量PR门禁、夜间重评测、可复现报告 | 固定依赖与commit；关键失败独立拦截；跳过、错误、成本和不确定性均可见 |

## 每课文件结构

```text
lessons/eNN_topic/
├── README.zh.md       # 问题、目标、关键片段、实验解释、来源
├── code.py            # 本课可执行Agent增量
├── eval.py            # 评分、外部验收与结果保存
├── cases.jsonl        # 来源、证据、划分、审核状态
├── exercises.md
├── solutions.md
└── reports/
    ├── replay.example.json
    └── real.example.schema.json
```

公共运行目录：

```text
knowledge_base/ # Docker只读挂载
workspaces/     # 每次实验的可写临时练习仓库
runs/           # 轨迹、逐样本结果、diff、成本和错误
evaluation_private/holdout/ # 独立保管，不挂载给被测Agent
config/      # Agent、裁判、生成器、模拟用户的独立配置
```

## 原24课到16课映射

| 新课 | 保留的原课知识 |
|---|---|
| e01 | s01、s09 |
| e02 | s02、s13 |
| e03 | s03、s04 |
| e04 | s05、s06 |
| e05 | s07 |
| e06 | s08 |
| e07 | s10 |
| e08 | s11 |
| e09 | s12、s20 |
| e10 | s14 |
| e11 | s15、s21 |
| e12 | s16 |
| e13 | s17 |
| e14 | s18 |
| e15 | s19 |
| e16 | s22、s23、s24 |

安全、隐私、偏见、提示注入、SQL、摘要、图像、语音、多模态、传统文本指标、基础模型benchmark及供应商集成保留为能力索引与附录；其中权限、记忆污染和MCP等与编程Agent直接相关的内容进入主线实验。

## 功能保留与未实现状态

Learn Claude Code 的17项机制均已有课程归属：循环e01；工具、权限、hook e02；skill加载e04；上下文压缩e12；记忆e12；计划、子Agent、任务系统、团队协作e13；后台任务与调度e14；MCP e10；目标闭环e11；集成、workflow续跑和目标复核e16。

第1、2课已验证最小循环、Bash及本课具名工具、权限和轨迹合同，与上游的改编差异见源码导读。这不代表17项机制完整迁移或全部功能等价。旧Faithfulness样章已移除，第5课已按编程知识与真实Agent输出重新制作，第6课已完成答案质量、reference和拒答评测；第7课已完成三层故障干预与真实Agent排查；第8至16课与完整机制核对仍为计划状态。历史验证记录单独保留。

## 相关材料与生成记录

[教学方式详解](teaching-method.md)、[评测与数据能力地图](evaluation-landscape.md)、[具体制作计划](course-production-plan.md)、[PocketFlow规划凭证](../generation/curriculum-README.md)、[原24课知识对照](archive/curriculum-24.md)。

第2课入口：[教材](../lessons/e02_tools_traces/README.zh.md)、[实验结果](../lessons/e02_tools_traces/run_summary.md)、[验收记录](e02-validation.md)。
