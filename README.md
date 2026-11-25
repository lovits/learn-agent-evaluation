# 从编程 Agent 学评测

从一个最小循环和 Bash 工具出发，先让 Agent 动手处理文件，再沿着每一次执行追问：怎么确认它真的把事做对了？

课程中的编程 Agent 沿 [Learn Claude Code](https://github.com/shareAI-lab/learn-claude-code) 的递进方式逐步长出工具、权限、知识库检索与多轮记忆；知识库接入 [Datawhale TinyRAG](https://github.com/datawhalechina/tiny-universe/tree/main/content/TinyRAG)，评测体系基于 [DeepEval](https://deepeval.com/docs/evaluation-introduction) 展开。适合会写 Python、了解 RAG 与 Agent，想把评测真正落到代码里的读者。

## 课程

全课分四个阶段推进：第 1 至 4 课搭起成功条件、样本、数据集与评分器；第 5 至 10 课接入 TinyRAG，评测检索上下文与生成回答；第 11 至 13 课评测工具调用、任务交付与多轮会话；第 14 至 16 课校准 LLM 裁判、对比版本并建立持续回归。

| 课 | 核心知识点 | 要解决的问题 |
|---|---|---|
| 01 | [定义成功](course/e01_success/README.zh.md) | 模型停下了，任务就完成了吗？ |
| 02 | [保存一次运行](course/e02_samples/README.zh.md) | 怎样把 Agent 的一次工作变成评测样本？ |
| 03 | [准备评测数据](course/e03_datasets/README.zh.md) | 怎样让题目代表你真正关心的能力？ |
| 04 | [给样本评分](course/e04_scoring/README.zh.md) | 什么时候写规则，什么时候请模型当裁判？ |
| 05 | [接通知识库](course/e05_knowledge_context/README.zh.md) | 检索出的资料，最后有哪些真的送进了模型？ |
| 06 | [上下文相关性与排序](course/e06_context_precision/README.zh.md) | 找到了资料，为什么还要看相关性和先后顺序？ |
| 07 | [上下文覆盖与召回](course/e07_context_recall/README.zh.md) | 返回的资料都相关，为什么问题还是答不全？ |
| 08 | [回答对上下文的忠实度](course/e08_faithfulness/README.zh.md) | 回答里的每条事实，上下文都给过依据吗？ |
| 09 | [答案质量](course/e09_answer_quality/README.zh.md) | 句句有出处，为什么仍可能没把问题答好？ |
| 10 | [上下文干扰与故障定位](course/e10_rag_diagnosis/README.zh.md) | 答案错了，该先查资料、检索还是生成？ |
| 11 | [工具调用质量](course/e11_tool_quality/README.zh.md) | 工具名选对了，调用就算合格了吗？ |
| 12 | [任务完成度](course/e12_task_completion/README.zh.md) | 怎样确认 Agent 真正交付了用户要的结果？ |
| 13 | [会话上下文与约束保持](course/e13_conversation/README.zh.md) | 用户中途改过要求，Agent 还在按哪一版执行？ |
| 14 | [校准 LLM 裁判](course/e14_judge_calibration/README.zh.md) | 用来打分的模型裁判，它自己的判断可信吗？ |
| 15 | [比较两个版本](course/e15_version_comparison/README.zh.md) | 平均分涨了，怎么判断改动确实有效？ |
| 16 | [综合项目与持续回归](course/e16_regression/README.zh.md) | 怎样把一次线上修复沉淀成长期回归门禁？ |

[完整大纲](docs/curriculum.md)

## 能学到哪些知识点与原理

- 模型、工具与执行框架（Harness）怎样配合形成 Agent 循环，循环退出状态、目录权限边界与运行轨迹各自记录什么信息。
- 任务目标、成功条件、运行证据、参考答案与评分标准怎样各司其职，为什么要把执行过程和最终产物分开核验。
- 一次真实运行如何映射为 DeepEval 的 `LLMTestCase` 与 `ToolCall`，以及 `Golden`、`EvaluationDataset`、`Synthesizer` 在候选出题、人工复核、语义去重和开发/留出集划分中的用法。
- 确定性规则（继承 `BaseMetric`）与语义裁判（`GEval`、`Rubric`、`evaluation_steps`）各自的适用边界，量表归一化与阈值判定怎样计算，以及有效零分、指标不适用与接口报错为什么要分开记录。
- TinyRAG 文档分块、向量检索与上下文组装的完整数据流，检索候选列表与模型实际收到的 `retrieval_context` 有何差别，以及如何追踪文档来源与内容版本。
- 检索上下文相关性与排序原理：普通精度、平均精度（AP）、倒数排名（MRR）与 NDCG 的计算方式，以及 DeepEval 中 `ContextualPrecisionMetric`（按片段排序加权）和 `ContextualRelevancyMetric`（按陈述相关性占比）的判分差异。
- 检索上下文覆盖与召回原理：参考事实如何拆解并与上下文归因比对，`ContextualRecallMetric` 的分母由什么决定，以及为什么高精度检索仍可能漏掉关键证据。
- 回答忠实度（`FaithfulnessMetric`）的三步判分过程：从上下文提取 `truths`、从回答拆出 `claims`、逐条做自然语言推断（`yes` / `no` / `borderline`），以及 `penalize_ambiguous_claims` 如何影响聚合得分。
- 答案质量的多维拆解：切题程度（`AnswerRelevancyMetric`）、事实精度与召回、F 分数、需求完整性以及缺证据时的合理拒答。
- RAG 链路故障定位方法：通过受控对照隔离文档缺失、版本过期、检索漏召回、上下文截断和生成阶段幻觉。
- 工具调用评测原理：用 `ToolCorrectnessMetric` 和 `ArgumentCorrectnessMetric` 分别检查工具选择、参数内容、调用顺序与重复动作，理解工具匹配高分与实际执行成功之间的差距。
- 任务完成度评测：将文件产物、程序行为契约与 `TaskCompletionMetric` 结合起来，避免只凭一句“已完成”或局部轨迹放行错误交付。
- 多轮会话评测：区分原始对话历史与压缩后送入模型的上下文，追踪用户约束的新增、覆盖与撤销，理解 `KnowledgeRetentionMetric` 与 `ConversationCompletenessMetric` 的输入视角。
- LLM 裁判校准原理：用独立参考标签统计误接收与误拒绝，排查顺序、篇幅和语言风格带来的裁判偏差，并在冻结的开发集与留出集上验证提示词修订。
- 版本对比与持续回归：同题配对比较、重复运行波动、按题族重采样（Bootstrap）与调用成本核算，将复核后的失败案例收进回归集持续守门。

## 仓库结构

```text
learn-agent-evaluation/
├── README.md                    课程总览、知识点与目录导航
├── course/
│   ├── e01_success/             最小 Agent 循环与成功条件
│   ├── e02_samples/             具名工具、权限、轨迹与 DeepEval 样本
│   ├── e03_datasets/            评测数据集构建、审核与划分
│   ├── e04_scoring/             规则评分与 G-Eval 裁判
│   ├── e05_knowledge_context/   接入 TinyRAG 与上下文追踪
│   ├── e06_context_precision/   上下文相关性与排序
│   ├── e07_context_recall/      上下文覆盖与召回
│   ├── e08_faithfulness/        回答忠实度
│   ├── e09_answer_quality/      答案质量
│   ├── e10_rag_diagnosis/       RAG 故障定位
│   ├── e11_tool_quality/        工具调用质量
│   ├── e12_task_completion/     任务完成度
│   ├── e13_conversation/        多轮会话与约束保持
│   ├── e14_judge_calibration/   LLM 裁判校准
│   ├── e15_version_comparison/  双版本配对比较
│   ├── e16_regression/          综合项目与持续回归
│   ├── run.py                   前两课的任务运行入口
│   └── grade.py                 前两课的独立评分入口
├── eval_course/                 模型调用、裁判适配、TinyRAG 与记录等共享模块
├── knowledge_base/              只读挂载的知识库文档
├── docs/                        完整大纲、制作规范与综合项目导读
├── references/                  上游文档、源码依据与固定版本号
├── vendor/                      引用的上游代码快照
├── generation/                  教材生成输入与运行证据留档
├── tools/                       教材生成、模型桥接与绘图脚本
├── tests/                       仓库单元测试
├── Dockerfile                   运行环境镜像
└── compose.yaml                 知识库、工作区与运行记录挂载配置
```

### 每课目录

每一课都是 `course/` 下的独立目录，把被测实现 `code.py` 和评分逻辑 `eval.py` 分开存放，方便对照“Agent 做了什么”与“评测器怎么判断”：

```text
course/eXX_topic/
├── README.zh.md            主教材：从具体问题出发讲解机制与代码
├── code.py                 本课运行或实验入口，按需复用前课 Agent
├── eval.py                 本课评分器、DeepEval 指标调用或产物检查
├── cases.jsonl             任务输入、参考答案与测试样本
├── source_walkthrough.md   本课调用链与 DeepEval 源码导读
├── exercises.md            动手练习
├── solutions.md            练习参考解答
├── assessment.md           样本设计与实际运行记录
├── assessment.json         结构化评分结果留档
└── images/                 两张 SVG 流程图及源文件
```

部分课程带有专用模块：第 2 课用 [tools.py](course/e02_samples/tools.py) 实现工具分发与路径边界，用 [samples.py](course/e02_samples/samples.py) 导出 DeepEval 样本；第 3 课用 [generate.py](course/e03_datasets/generate.py) 生成候选题目；第 13 课用 [scenario.json](course/e13_conversation/scenario.json) 描述多轮对话场景。

### Agent 代码入口

后续指标课直接复用前几课搭好的 Agent 内核，避免每课重复贴同一套循环：

| 模块 | 文件 | 职责 |
|---|---|---|
| 最小循环 | [第 1 课 code.py](course/e01_success/code.py) | 请求模型、执行 Bash、把命令输出喂回模型 |
| 具名工具循环 | [第 2 课 code.py](course/e02_samples/code.py) | 贯穿全课的 Agent 主循环，按步记录工具调用与结果 |
| 工具与权限 | [第 2 课 tools.py](course/e02_samples/tools.py) | 文件读写、Bash 分发与工作区路径校验 |
| 样本转换 | [第 2 课 samples.py](course/e02_samples/samples.py) | 把运行事件转换为 DeepEval `LLMTestCase` |
| 知识库接入 | [第 5 课 code.py](course/e05_knowledge_context/code.py) · [tinyrag.py](eval_course/tinyrag.py) | 注册检索工具，分别保存候选结果与送入模型的上下文 |
| 综合回归 | [第 16 课 code.py](course/e16_regression/code.py) · [eval.py](course/e16_regression/eval.py) | 串联 Agent、TinyRAG 与各项判据，执行回归门禁 |

上游参考片段存放在 [vendor](vendor/) 与 [references/upstream](references/upstream/)，对应提交哈希见 [versions.json](references/versions.json)。

## 学完能做什么

- 把模糊的业务目标拆成可验证的成功条件，将 Agent 运行轨迹整理成标准评测样本。
- 搭建带来源追踪、人工审核与开发/留出划分的数据集，合理搭配代码规则与 `GEval` 裁判。
- 诊断 RAG 检索的相关性、排序与覆盖率，核验回答忠实度与答案质量，定位链路出错位置。
- 独立评测工具调用、文件交付与多轮约束保持，不再被一句“已完成”误导。
- 读懂 DeepEval 指标背后的拆解、裁决与聚合源码，校准模型裁判，完成版本对比与持续回归。

## 如何阅读

按 `e01` 到 `e16` 的顺序往下读。每课先摆出一个具体故障，再引入解决它的最小代码，逐步拆解数据流与判分逻辑；想深挖 SDK 细节时打开同目录下的 `source_walkthrough.md`，想看运行输出时查阅 `assessment.md`，最后在[综合项目导读](docs/integrated-project.md)里把整条评测链串起来。

[来源与许可](THIRD_PARTY.md) · [固定源码版本](references/versions.json)
