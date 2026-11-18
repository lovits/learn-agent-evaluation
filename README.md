# 从编程 Agent 学评测

从一个循环和 Bash 开始，让 Agent 真正处理文件，再问：怎样知道它做得对？

课程沿 [Learn Claude Code](https://github.com/shareAI-lab/learn-claude-code) 的思路逐步增加机制。知识库使用 [Datawhale TinyRAG](https://github.com/datawhalechina/tiny-universe/tree/main/content/TinyRAG)，实际评测框架统一使用 DeepEval；同时从 Ragas 的文档与源码学习指标原理和数据集设计。适合会 Python、了解 RAG 与 Agent，想系统学习评测的读者。

## 课程

| 课 | 核心知识点 | 要解决的问题 |
|---|---|---|
| 01 | [定义成功](course/e01_success/README.zh.md) | 模型停下了，任务就完成了吗？ |
| 02 | [保存一次运行](course/e02_samples/README.zh.md) | 怎样把 Agent 的一次工作变成评测样本？ |
| 03 | [准备评测数据](course/e03_datasets/README.zh.md) | 怎样让题目代表你真正关心的能力？ |
| 04 | [给样本评分](course/e04_scoring/README.zh.md) | 什么时候用规则，什么时候请模型判断？ |
| 05 | [接通知识库](course/e05_knowledge_context/README.zh.md) | 检索出的资料，最后有哪些真的交给了模型？ |
| 06 | [上下文相关性与排序](course/e06_context_precision/README.zh.md) | 找到了资料，为什么还要看相关性和顺序？ |
| 07 | [上下文覆盖与召回](course/e07_context_recall/README.zh.md) | 资料看起来都相关，为什么问题仍答不全？ |
| 08 | [回答对上下文的忠实度](course/e08_faithfulness/README.zh.md) | 回答里的每条事实，资料都支持吗？ |
| 09 | [答案质量](course/e09_answer_quality/README.zh.md) | 忠于资料，为什么仍可能没有回答好问题？ |
| 10 | [上下文干扰与故障定位](course/e10_rag_diagnosis/README.zh.md) | 答案错了，应该先改资料、检索还是生成？ |
| 11 | [工具调用质量](course/e11_tool_quality/README.zh.md) | 名字选对了，工具就用对了吗？ |
| 12 | [任务完成度](course/e12_task_completion/README.zh.md) | 怎样确认 Agent 真的交付了用户要的结果？ |
| 13 | [会话上下文与约束保持](course/e13_conversation/README.zh.md) | 用户改了要求以后，Agent 还记得哪一版？ |
| 14 | [校准 LLM 裁判](course/e14_judge_calibration/README.zh.md) | 评分器自己的判断可信吗？ |
| 15 | [比较两个版本](course/e15_version_comparison/README.zh.md) | 分数变高，怎样判断改动真的有用？ |
| 16 | [综合项目与持续回归](course/e16_regression/README.zh.md) | 怎样让一次修复成为以后不会再犯的经验？ |

[完整大纲](docs/curriculum.md)

## 每课学什么，代码在哪里

每课只展开一个核心问题。按“教材 → 本课代码 → 评分代码 → 源码导读”阅读；源码导读解释本课调用链，并给出 Learn Claude Code、DeepEval、Ragas 的相关依据。Ragas 用来理解评测原理，实际框架接入统一使用 DeepEval。

`code.py` 是本课机制或实验的主入口，`eval.py` 保存评分或证据检查逻辑。只有前两课直接实现 Agent 循环；后续按需要复用，避免重复贴一套 Agent。

| 课 | 知识点与学完能做什么 | 教材 | 本课代码 | 评分代码 | 源码导读 |
|---|---|---|---|---|---|
| 01 · 定义成功 | Agent 的模型—Bash 循环；停止条件；运行证据；独立检查文件与输出。学会把“任务完成”写成可检查的条件。 | [教材](course/e01_success/README.zh.md) | [code.py](course/e01_success/code.py) | [eval.py](course/e01_success/eval.py) | [导读](course/e01_success/source_walkthrough.md) |
| 02 · 保存一次运行 | 具名工具与分发；文件权限边界；消息与动作轨迹；DeepEval 样本字段。学会把一次运行整理成可评测的证据。 | [教材](course/e02_samples/README.zh.md) | [code.py](course/e02_samples/code.py) | [eval.py](course/e02_samples/eval.py) | [导读](course/e02_samples/source_walkthrough.md) |
| 03 · 准备评测数据 | 候选题生成与人工审核；来源与参考答案；去重、能力覆盖；开发集与留出集。学会构建数据集并避免题目泄漏。 | [教材](course/e03_datasets/README.zh.md) | [code.py](course/e03_datasets/code.py) | [eval.py](course/e03_datasets/eval.py) | [导读](course/e03_datasets/source_walkthrough.md) |
| 04 · 给样本评分 | 规则评分与 G-Eval；评价量表、阈值与评分理由；异常和缺失分数。学会为不同问题选择评分方法。 | [教材](course/e04_scoring/README.zh.md) | [code.py](course/e04_scoring/code.py) | [eval.py](course/e04_scoring/eval.py) | [导读](course/e04_scoring/source_walkthrough.md) |
| 05 · 接通知识库 | TinyRAG 的分块、向量检索与工具接入；只读知识库；来源版本；候选片段与实际上下文。学会追踪模型究竟看到了什么。 | [教材](course/e05_knowledge_context/README.zh.md) | [code.py](course/e05_knowledge_context/code.py) | [eval.py](course/e05_knowledge_context/eval.py) | [导读](course/e05_knowledge_context/source_walkthrough.md) |
| 06 · 上下文相关性与排序 | 上下文相关性；Precision、AP、倒数排名与 NDCG；DeepEval 的上下文指标。学会区分“资料相关”和“相关资料排在前面”。 | [教材](course/e06_context_precision/README.zh.md) | [code.py](course/e06_context_precision/code.py) | [eval.py](course/e06_context_precision/eval.py) | [导读](course/e06_context_precision/source_walkthrough.md) |
| 07 · 上下文覆盖与召回 | 必要事实与参考答案；证据覆盖；上下文召回与归因；缺失资料。学会发现相关资料中仍然漏掉的必要信息。 | [教材](course/e07_context_recall/README.zh.md) | [code.py](course/e07_context_recall/code.py) | [eval.py](course/e07_context_recall/eval.py) | [导读](course/e07_context_recall/source_walkthrough.md) |
| 08 · 回答对上下文的忠实度 | 回答声明拆分；逐条证据支持；不支持与模糊判断；忠实度聚合。学会判断回答中的事实有没有资料依据。 | [教材](course/e08_faithfulness/README.zh.md) | [code.py](course/e08_faithfulness/code.py) | [eval.py](course/e08_faithfulness/eval.py) | [导读](course/e08_faithfulness/source_walkthrough.md) |
| 09 · 答案质量 | 回答相关性；事实精度、召回与 F 分数；任务量表；正确性与完整性。学会区分有依据的回答和真正答好问题的回答。 | [教材](course/e09_answer_quality/README.zh.md) | [code.py](course/e09_answer_quality/code.py) | [eval.py](course/e09_answer_quality/eval.py) | [导读](course/e09_answer_quality/source_walkthrough.md) |
| 10 · 上下文干扰与故障定位 | 资料、检索、上下文组装与生成的边界；干扰片段；单变量对照。学会沿证据链定位 RAG 失败的环节。 | [教材](course/e10_rag_diagnosis/README.zh.md) | [code.py](course/e10_rag_diagnosis/code.py) | [eval.py](course/e10_rag_diagnosis/eval.py) | [导读](course/e10_rag_diagnosis/source_walkthrough.md) |
| 11 · 工具调用质量 | 工具名、参数、顺序与调用结果；参考轨迹；ToolCorrectness 与 ArgumentCorrectness。学会解释工具调用究竟错在哪里。 | [教材](course/e11_tool_quality/README.zh.md) | [code.py](course/e11_tool_quality/code.py) | [eval.py](course/e11_tool_quality/eval.py) | [导读](course/e11_tool_quality/source_walkthrough.md) |
| 12 · 任务完成度 | 业务交付条件；文件产物与行为检查；过程证据；TaskCompletion。学会独立核对 Agent 是否真正完成任务。 | [教材](course/e12_task_completion/README.zh.md) | [code.py](course/e12_task_completion/code.py) | [eval.py](course/e12_task_completion/eval.py) | [导读](course/e12_task_completion/source_walkthrough.md) |
| 13 · 会话上下文与约束保持 | 原始历史与实际模型输入；新增、覆盖和撤销约束；知识保持与会话完整性。学会判断 Agent 是否遵守用户当前的要求。 | [教材](course/e13_conversation/README.zh.md) | [code.py](course/e13_conversation/code.py) | [eval.py](course/e13_conversation/eval.py) | [导读](course/e13_conversation/source_walkthrough.md) |
| 14 · 校准 LLM 裁判 | 人工参考标签；误判与分歧；阈值校准；等价表达、位置变化与裁判指令干扰。学会检查评分器本身是否可信。 | [教材](course/e14_judge_calibration/README.zh.md) | [code.py](course/e14_judge_calibration/code.py) | [eval.py](course/e14_judge_calibration/eval.py) | [导读](course/e14_judge_calibration/source_walkthrough.md) |
| 15 · 比较两个版本 | 同题配对；单变量改动；重复运行与题族重采样；质量、用量与成本。学会判断分数差异是否足以支持改进结论。 | [教材](course/e15_version_comparison/README.zh.md) | [code.py](course/e15_version_comparison/code.py) | [eval.py](course/e15_version_comparison/eval.py) | [导读](course/e15_version_comparison/source_walkthrough.md) |
| 16 · 综合项目与持续回归 | 组合 Agent、TinyRAG 与评分器；失败复核与回归集；关键条件与缺失证据；持续回归。学会把一次修复变成可持续检查的评测链。 | [教材](course/e16_regression/README.zh.md) | [code.py](course/e16_regression/code.py) | [eval.py](course/e16_regression/eval.py) | [导读](course/e16_regression/source_walkthrough.md) |

## 仓库结构

```text
learn-agent-evaluation/
├── README.md                    课程总览、知识点与文件导航
├── course/
│   ├── e01_success/             最小 Agent 循环与成功条件
│   ├── e02_samples/             工具、权限、轨迹与统一样本
│   ├── e03_datasets/            评测数据集
│   ├── e04_scoring/             规则评分与 LLM 裁判
│   ├── e05_knowledge_context/   Agent 接入 TinyRAG
│   ├── e06_context_precision/  上下文相关性与排序
│   ├── e07_context_recall/      上下文覆盖与召回
│   ├── e08_faithfulness/        回答忠实度
│   ├── e09_answer_quality/      答案质量
│   ├── e10_rag_diagnosis/       RAG 故障定位
│   ├── e11_tool_quality/        工具调用质量
│   ├── e12_task_completion/     任务完成度
│   ├── e13_conversation/        多轮约束保持
│   ├── e14_judge_calibration/   裁判校准
│   ├── e15_version_comparison/  版本比较
│   ├── e16_regression/          综合 Agent 与持续回归
│   ├── run.py                  前两课的任务运行入口
│   └── grade.py                前两课的记录评分入口
├── eval_course/                 模型调用、裁判适配、TinyRAG 与记录等共享代码
├── knowledge_base/              可挂载的知识库资料
├── docs/                        完整大纲、课程规范与综合项目讲解
├── references/                  上游文档、指标源码依据与固定版本
├── vendor/                      课程引用的上游代码片段
├── generation/                  PocketFlow 教材组织输入与生成依据
├── tools/                       教材生成、模型桥接和绘图工具
├── tests/                       代码检查，独立于课程质量评测
├── Dockerfile                   课程运行镜像
└── compose.yaml                 知识库、工作区与运行记录的挂载配置
```

### 每课的文件结构

下面是各课共有的结构。`code.py` 与 `eval.py` 分开，方便对照“被观察的过程”和“判断它的依据”；主教材不混入运行报告。

```text
course/eXX_topic/
├── README.zh.md            教材：问题、解决方案、工作原理与关键代码
├── code.py                 本课机制或实验入口，按需复用已有 Agent
├── eval.py                 本课评分、指标调用或证据检查
├── cases.jsonl             任务、参考与评测样本
├── source_walkthrough.md   关键调用链及上游文档、源码依据
├── exercises.md            动手问题
├── solutions.md            参考解释
├── assessment.md           独立的评测样本说明与运行结果
├── assessment.json         对应的结构化记录
└── images/                 两张关键流程图及源文件
```

少数课程有额外文件：第 2 课的 [tools.py](course/e02_samples/tools.py) 实现工具与权限边界，[samples.py](course/e02_samples/samples.py) 转换评测样本；第 3 课的 [generate.py](course/e03_datasets/generate.py) 准备候选题；第 13 课的 [scenario.json](course/e13_conversation/scenario.json) 保存会话场景。其余配套文件在各课源码导读中解释。

### Agent 的代码从哪里读

| 部分 | 文件 | 负责什么 |
|---|---|---|
| 最小循环 | [第 1 课 code.py](course/e01_success/code.py) | 请求模型、执行 Bash、把结果交回模型 |
| 具名工具循环 | [第 2 课 code.py](course/e02_samples/code.py) | 复用的 Agent 主循环，记录工具动作与返回 |
| 工具与权限 | [第 2 课 tools.py](course/e02_samples/tools.py) | 文件读写、Bash 分发与文件路径边界 |
| 评测样本转换 | [第 2 课 samples.py](course/e02_samples/samples.py) | 将运行记录转换为 DeepEval 样本 |
| 知识库接入 | [第 5 课 code.py](course/e05_knowledge_context/code.py) · [tinyrag.py](eval_course/tinyrag.py) | 增加检索工具，保存检索结果与实际送入模型的上下文 |
| 综合项目 | [第 16 课 code.py](course/e16_regression/code.py) · [eval.py](course/e16_regression/eval.py) | 组合既有 Agent 与评测逻辑，形成回归流程 |

上游原代码与课程代码的对应关系见每课源码导读；本地参考片段位于 [vendor](vendor/) 与 [references/upstream](references/upstream/)，固定版本见 [versions.json](references/versions.json)。

## 学完能做什么

- 把用户目标写成可检查的成功条件，从运行记录构造评测样本。
- 建立有来源、有参考、有划分的数据集，选用规则和 LLM 裁判。
- 评价上下文是否相关、排得合理、覆盖充分，以及回答是否有依据、正确、完整。
- 分开判断工具调用、任务完成和多轮约束，用证据定位失败。
- 读懂 DeepEval、Ragas 的关键判分过程，校准裁判、比较版本并接入持续回归。

## 怎样读

每课从一个具体困难开始，接着给出最小机制，再沿关键代码解释它怎样工作。教材只展开当前知识点，完整函数和框架依据放在源码导读，动手问题及参考解另放。

一条任务贯穿 Agent 与评分器：Agent 负责工作，评分器根据实际记录和结果判断。后续课程复用已有能力，最后组合成[完整项目](docs/integrated-project.md)。代码可在 Docker 中执行，知识库通过只读目录挂载。

[来源与许可](THIRD_PARTY.md) · [固定源码版本](references/versions.json)
